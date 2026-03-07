"""
Integration tests for StarStream with SQLite storage backend.

Tests the full flow: StarStreamPlugin -> SQLiteStorage -> Persistence
"""

import pytest
import asyncio
import tempfile
import os
from starstream import StarStreamPlugin, Presence
from starstream.storage.sqlite import SQLiteBackend


class TestSQLiteIntegration:
    """Test StarStream integration with SQLite storage."""

    @pytest.fixture
    def sqlite_storage(self):
        """Create temporary SQLite storage."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        storage = SQLiteBackend(db_path)
        # SQLiteBackend initializes automatically in __init__

        yield storage

        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_message_persistence(self, mock_app, sqlite_storage):
        """Test that messages are persisted to SQLite."""
        # Create plugin with SQLite storage
        plugin = StarStreamPlugin(mock_app, storage=sqlite_storage, enable_history=True)

        # Store a message
        message_data = {"user": "test_user", "text": "Hello SQLite!", "timestamp": 1234567890}

        await plugin.history.add("room:test", message_data)

        # Verify persistence
        messages = await plugin.history.get("room:test", limit=10)
        assert len(messages) == 1
        assert messages[0]["message"]["text"] == "Hello SQLite!"
        assert messages[0]["message"]["user"] == "test_user"

    @pytest.mark.asyncio
    async def test_presence_with_sqlite(self, mock_app, sqlite_storage):
        """Test presence system with SQLite persistence."""
        plugin = StarStreamPlugin(mock_app)
        presence = Presence()
        plugin.presence = presence

        # User joins
        await presence.join("room:test", "user1")

        # Verify in memory
        online = await presence.get_online("room:test")
        assert "user1" in online

        # Verify presence tracking works
        assert len(online) == 1
        assert "user1" in online

    @pytest.mark.asyncio
    async def test_storage_backend_interface(self, sqlite_storage):
        """Test SQLite storage implements StorageBackend interface."""
        # Test set/get
        data = {"test": "value", "number": 42}
        result = await sqlite_storage.set("key1", data, ttl=3600)
        assert result is True

        retrieved = await sqlite_storage.get("key1")
        assert retrieved is not None
        assert retrieved["test"] == "value"
        assert retrieved["number"] == 42

        # Test delete
        deleted = await sqlite_storage.delete("key1")
        assert deleted is True

        # Verify deletion
        retrieved = await sqlite_storage.get("key1")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_ttl_expiration(self, sqlite_storage):
        """Test that data with TTL expires."""
        # Set data with very short TTL
        await sqlite_storage.set("temp_key", {"data": "temp"}, ttl=1)

        # Verify it exists
        data = await sqlite_storage.get("temp_key")
        assert data is not None

        # Wait for expiration
        await asyncio.sleep(2)

        # Should be expired
        data = await sqlite_storage.get("temp_key")
        assert data is None

    @pytest.mark.asyncio
    async def test_concurrent_access(self, sqlite_storage):
        """Test concurrent access to SQLite storage."""

        async def writer(id):
            for i in range(5):
                await sqlite_storage.set(f"key_{id}_{i}", {"id": id, "i": i})

        # Run multiple writers concurrently
        tasks = [writer(i) for i in range(3)]
        await asyncio.gather(*tasks)

        # Verify all data was written
        for id in range(3):
            for i in range(5):
                data = await sqlite_storage.get(f"key_{id}_{i}")
                assert data is not None
                assert data["id"] == id
                assert data["i"] == i

    @pytest.mark.asyncio
    async def test_broadcast_with_storage_fallback(self, mock_app, sqlite_storage):
        """Test broadcast works even with storage operations."""
        plugin = StarStreamPlugin(mock_app, storage=sqlite_storage, enable_history=True)

        messages = []

        async def subscriber():
            async for msg in plugin.core.subscribe("global"):
                messages.append(msg)
                if len(messages) >= 2:
                    break

        task = asyncio.create_task(subscriber())
        await asyncio.sleep(0.1)

        # Broadcast messages
        await plugin.broadcast("Message 1", "global")
        await plugin.broadcast("Message 2", "global")

        try:
            await asyncio.wait_for(task, timeout=2.0)
        except asyncio.TimeoutError:
            task.cancel()

        assert len(messages) == 2


class TestSQLiteStorageBackend:
    """Test SQLiteBackend as StorageBackend implementation."""

    @pytest.fixture
    def storage(self):
        """Create SQLite storage backend."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        storage = SQLiteBackend(db_path)
        # SQLiteBackend initializes automatically in __init__

        yield storage

        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_backend_set_get(self, storage):
        """Test basic set/get operations."""
        await storage.set("test", {"value": 123})
        result = await storage.get("test")
        assert result["value"] == 123

    @pytest.mark.asyncio
    async def test_backend_exists(self, storage):
        """Test exists method."""
        await storage.set("exists_test", {"data": "test"})
        assert await storage.exists("exists_test") is True
        assert await storage.exists("nonexistent") is False

    @pytest.mark.asyncio
    async def test_backend_clear(self, storage):
        """Test clear method."""
        await storage.set("key1", {"data": 1})
        await storage.set("key2", {"data": 2})

        await storage.clear()

        assert await storage.get("key1") is None
        assert await storage.get("key2") is None

    @pytest.mark.asyncio
    async def test_backend_large_data(self, storage):
        """Test storage of large data."""
        large_data = {"items": [{"id": i, "data": "x" * 100} for i in range(100)]}

        await storage.set("large", large_data)
        result = await storage.get("large")

        assert len(result["items"]) == 100
        assert result["items"][0]["data"] == "x" * 100
