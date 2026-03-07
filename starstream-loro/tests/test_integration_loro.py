"""
Integration tests for StarStream with Loro CRDT.

Tests the full flow: StarStreamPlugin -> LoroPlugin -> CRDT Sync + Broadcast
"""

import pytest
import asyncio


class TestLoroIntegration:
    """Test StarStream integration with Loro CRDT."""

    @pytest.fixture
    def loro_plugin(self, mock_app):
        """Create Loro plugin with mock storage."""
        from starstream import StarStreamPlugin
        from starstream_loro import LoroPlugin

        stream = StarStreamPlugin(mock_app)
        loro = LoroPlugin(stream)

        return loro, stream

    @pytest.mark.asyncio
    async def test_connect_and_sync(self, loro_plugin):
        """Test connecting to a document and syncing."""
        loro, stream = loro_plugin

        # Connect peer to document
        result = await loro.connect("doc1", "peer1")
        assert result is True

        # Check document state
        state = await loro.get_state("doc1")
        assert state is not None
        assert state["doc_id"] == "doc1"
        assert "peer1" in state["peers"]

    @pytest.mark.asyncio
    async def test_delta_synchronization(self, loro_plugin):
        """Test delta synchronization between peers."""
        loro, stream = loro_plugin

        # Connect two peers
        await loro.connect("doc1", "peer1")
        await loro.connect("doc1", "peer2")

        # Peer1 sends delta
        delta = b"test delta data"
        result = await loro.receive_delta("doc1", "peer1", delta)
        assert result is True

        # Get peers to broadcast to (should be peer2)
        peers = await loro.get_peers("doc1", exclude="peer1")
        assert "peer2" in peers
        assert "peer1" not in peers

    @pytest.mark.asyncio
    async def test_broadcast_to_other_peers(self, loro_plugin):
        """Test broadcasting changes to other peers via StarStream."""
        loro, stream = loro_plugin

        # Setup
        await loro.connect("doc1", "peer1")
        await loro.connect("doc1", "peer2")
        await loro.connect("doc1", "peer3")

        messages = []

        async def subscriber():
            async for msg in stream.core.subscribe("doc1"):
                messages.append(msg)
                if len(messages) >= 2:
                    break

        task = asyncio.create_task(subscriber())
        await asyncio.sleep(0.1)

        # Peer1 sends delta
        delta = b"update from peer1"
        await loro.receive_delta("doc1", "peer1", delta)

        # Get peers to notify
        peers = await loro.get_peers("doc1", exclude="peer1")

        # Broadcast to each peer
        for peer in peers:
            await stream.send_to_user(peer, ("signals", {"delta": delta.hex()}))

        try:
            await asyncio.wait_for(task, timeout=1.0)
        except asyncio.TimeoutError:
            task.cancel()

        assert len(peers) == 2  # peer2 and peer3
        assert len(messages) == 2  # Both received

    @pytest.mark.asyncio
    async def test_document_versioning(self, loro_plugin):
        """Test document version tracking."""
        loro, stream = loro_plugin

        await loro.connect("doc1", "peer1")

        # Send multiple deltas
        for i in range(3):
            delta = f"delta_{i}".encode()
            await loro.receive_delta("doc1", "peer1", delta)

        # Get state
        state = await loro.get_state("doc1")
        assert state["version"] == 3

    @pytest.mark.asyncio
    async def test_get_delta_since_version(self, loro_plugin):
        """Test retrieving deltas since a specific version."""
        loro, stream = loro_plugin

        await loro.connect("doc1", "peer1")

        # Send deltas
        await loro.receive_delta("doc1", "peer1", b"delta1")
        await loro.receive_delta("doc1", "peer1", b"delta2")
        await loro.receive_delta("doc1", "peer1", b"delta3")

        # Get delta since version 1
        delta = await loro.get_delta("doc1", since_version=1)

        # Should have changes from versions 2 and 3
        assert delta is not None

    @pytest.mark.asyncio
    async def test_peer_disconnect(self, loro_plugin):
        """Test peer disconnection."""
        loro, stream = loro_plugin

        await loro.connect("doc1", "peer1")
        await loro.connect("doc1", "peer2")

        # Disconnect peer1
        result = await loro.disconnect("doc1", "peer1")
        assert result is True

        # Verify peer1 is gone
        state = await loro.get_state("doc1")
        assert "peer1" not in state["peers"]
        assert "peer2" in state["peers"]

    @pytest.mark.asyncio
    async def test_concurrent_peers(self, loro_plugin):
        """Test multiple peers editing concurrently."""
        loro, stream = loro_plugin

        # Connect multiple peers
        peers = [f"peer{i}" for i in range(5)]
        for peer in peers:
            await loro.connect("doc1", peer)

        # Each peer sends a delta
        for i, peer in enumerate(peers):
            delta = f"update from {peer}".encode()
            await loro.receive_delta("doc1", peer, delta)

        # Verify all changes applied
        state = await loro.get_state("doc1")
        assert state["version"] == 5
        assert len(state["peers"]) == 5

    @pytest.mark.asyncio
    async def test_update_callback(self, loro_plugin):
        """Test update callback registration."""
        loro, stream = loro_plugin

        callbacks = []

        async def on_update(event, data):
            callbacks.append((event, data))

        # Register callback
        loro.on_update("doc1", on_update)

        # Connect and send delta
        await loro.connect("doc1", "peer1")
        await loro.receive_delta("doc1", "peer1", b"delta")

        # Give callback time to fire
        await asyncio.sleep(0.1)

        assert len(callbacks) > 0

    @pytest.mark.asyncio
    async def test_sync_stats(self, loro_plugin):
        """Test sync statistics."""
        loro, stream = loro_plugin

        # Empty stats
        stats = loro.get_stats()
        assert stats["documents"] == 0

        # Add some documents
        await loro.connect("doc1", "peer1")
        await loro.connect("doc1", "peer2")
        await loro.connect("doc2", "peer3")

        stats = loro.get_stats()
        assert stats["documents"] == 2
        assert stats["total_peers"] == 3


class TestLoroDocumentLifecycle:
    """Test full document lifecycle with Loro."""

    @pytest.mark.asyncio
    async def test_full_document_flow(self, mock_app):
        """Test complete document editing flow."""
        from starstream import StarStreamPlugin
        from starstream_loro import LoroPlugin

        stream = StarStreamPlugin(mock_app)
        loro = LoroPlugin(stream)

        # 1. User A creates document
        await loro.connect("meeting-notes", "user-a")

        # 2. User A makes initial edit
        await loro.receive_delta("meeting-notes", "user-a", b"initial content")

        # 3. User B joins
        await loro.connect("meeting-notes", "user-b")

        # 4. User B gets current state
        state = await loro.get_state("meeting-notes")
        assert state["version"] == 1

        # 5. Both users edit concurrently
        await loro.receive_delta("meeting-notes", "user-a", b"edit from A")
        await loro.receive_delta("meeting-notes", "user-b", b"edit from B")

        # 6. Verify both changes applied
        state = await loro.get_state("meeting-notes")
        assert state["version"] == 3

        # 7. User A disconnects
        await loro.disconnect("meeting-notes", "user-a")

        # 8. Document still active with user B
        state = await loro.get_state("meeting-notes")
        assert "user-a" not in state["peers"]
        assert "user-b" in state["peers"]

    @pytest.mark.asyncio
    async def test_document_cleanup(self, mock_app):
        """Test document cleanup when all peers leave."""
        from starstream import StarStreamPlugin
        from starstream_loro import LoroPlugin

        stream = StarStreamPlugin(mock_app)
        loro = LoroPlugin(stream)

        # Create document with one peer
        await loro.connect("temp-doc", "user1")
        await loro.receive_delta("temp-doc", "user1", b"data")

        # Verify document exists
        state = await loro.get_state("temp-doc")
        assert state is not None

        # Disconnect last peer
        await loro.disconnect("temp-doc", "user1")

        # Document should be cleaned up
        stats = loro.get_stats()
        assert stats["documents"] == 0


class TestLoroStorageIntegration:
    """Test Loro with storage backend."""

    @pytest.mark.asyncio
    async def test_persist_to_storage(self, mock_app, tmp_path):
        """Test persisting document to storage."""
        from starstream import StarStreamPlugin
        from starstream.storage.sqlite import SQLiteBackend
        from starstream_loro import LoroPlugin, LoroStorage

        # Create storage
        db_path = tmp_path / "loro_test.db"
        base_storage = SQLiteBackend(str(db_path))
        await base_storage.initialize()

        loro_storage = LoroStorage(base_storage)

        stream = StarStreamPlugin(mock_app)
        loro = LoroPlugin(stream, storage=loro_storage)

        # Connect and edit
        await loro.connect("doc1", "peer1")
        await loro.receive_delta("doc1", "peer1", b"content")

        # Trigger save (normally happens on disconnect)
        state = await loro.get_state("doc1")
        await loro_storage.save("doc1", state["content"], state["version"])

        # Load back
        loaded = await loro_storage.load("doc1")
        assert loaded is not None
        assert loaded["version"] == 1

        await base_storage.close()
