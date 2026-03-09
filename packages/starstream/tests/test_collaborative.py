"""
Tests for collaborative flag (Convention over Configuration for CRDT).

RED phase: These tests should FAIL initially.
"""

import pytest


class TestCollaborativeFlag:
    """Test collaborative flag provides transparent CRDT support."""

    def test_collaborative_flag_disabled_by_default(self, mock_app):
        """collaborative should be False by default."""
        from starstream import StarStreamPlugin

        stream = StarStreamPlugin(mock_app)

        assert not hasattr(stream, "_collaborative_enabled") or not stream._collaborative_enabled

    def test_collaborative_flag_creates_engine(self, mock_app):
        """collaborative=True should create collaborative engine on access."""
        from starstream import StarStreamPlugin

        stream = StarStreamPlugin(mock_app, collaborative=True)

        assert stream._collaborative_enabled is True
        # Engine is lazy loaded, access property to trigger
        assert stream.collaborative is not None
        assert stream._collaborative is not None

    def test_collaborative_property_access(self, mock_app):
        """stream.collaborative should expose sync methods."""
        from starstream import StarStreamPlugin

        stream = StarStreamPlugin(mock_app, collaborative=True)

        assert hasattr(stream.collaborative, "sync")
        assert hasattr(stream.collaborative, "connect")
        assert hasattr(stream.collaborative, "disconnect")

    def test_collaborative_without_flag_raises(self, mock_app):
        """Accessing collaborative without flag should raise clear error."""
        from starstream import StarStreamPlugin

        stream = StarStreamPlugin(mock_app, collaborative=False)

        with pytest.raises(RuntimeError) as exc_info:
            _ = stream.collaborative

        assert "Collaborative editing not enabled" in str(exc_info.value)
        assert "collaborative=True" in str(exc_info.value)

    def test_collaborative_with_persist_uses_shared_storage(self, mock_app):
        """collaborative=True with persist=True should share storage."""
        from starstream import StarStreamPlugin

        stream = StarStreamPlugin(mock_app, collaborative=True, persist=True)

        assert stream.storage is not None
        # Collaborative engine should use the same storage
        assert stream.collaborative._storage is stream.storage

    def test_collaborative_without_persist_uses_memory(self, mock_app):
        """collaborative=True with persist=False should use memory."""
        from starstream import StarStreamPlugin

        stream = StarStreamPlugin(mock_app, collaborative=True, persist=False)

        # Storage should be None or memory-based
        # Collaborative engine should handle in-memory state
        assert stream.collaborative is not None

    @pytest.mark.asyncio
    async def test_collaborative_sync_flow(self, mock_app):
        """Test basic collaborative sync workflow."""
        from starstream import StarStreamPlugin

        stream = StarStreamPlugin(mock_app, collaborative=True)

        # Connect peer to document
        await stream.collaborative.connect("doc-1", "user-123")

        # Sync a delta
        delta = b"test delta"
        result = await stream.collaborative.sync("doc-1", delta, "user-123")

        assert result is True

        # Get document state
        state = await stream.collaborative.get_state("doc-1")
        assert state is not None
        assert state["doc_id"] == "doc-1"
        assert "user-123" in state["peers"]


class TestCollaborativeAPI:
    """Test collaborative API is intuitive and works correctly."""

    @pytest.mark.asyncio
    async def test_sync_auto_connects_peer(self, mock_app):
        """sync() should auto-connect peer if not already connected."""
        from starstream import StarStreamPlugin

        stream = StarStreamPlugin(mock_app, collaborative=True)

        # Sync without explicit connect
        delta = b"test content"
        result = await stream.collaborative.sync("doc-auto", delta, "user-456")

        assert result is True

        # Verify peer was auto-connected
        state = await stream.collaborative.get_state("doc-auto")
        assert "user-456" in state["peers"]

    @pytest.mark.asyncio
    async def test_disconnect_cleans_up(self, mock_app):
        """disconnect() should clean up when last peer leaves."""
        from starstream import StarStreamPlugin

        stream = StarStreamPlugin(mock_app, collaborative=True)

        # Connect and sync
        await stream.collaborative.connect("doc-temp", "user-1")
        await stream.collaborative.sync("doc-temp", b"data", "user-1")

        # Disconnect
        await stream.collaborative.disconnect("doc-temp", "user-1")

        # Document should be cleaned up
        stats = stream.collaborative.get_stats()
        assert stats["documents"] == 0
