"""
Integration tests for StarStream with PocketBase.

Tests the full flow: StarStreamPlugin -> PocketBasePlugin -> Database + Broadcast
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch


class TestPocketBaseIntegration:
    """Test StarStream integration with PocketBase (mocked)."""

    @pytest.fixture
    def mock_pb_client(self):
        """Create mock PocketBase client."""
        client = Mock()
        client.admins = Mock()
        client.admins.auth_with_password = Mock()
        client.collection = Mock()
        return client

    @pytest.fixture
    def mock_pb_plugin(self, mock_app, mock_pb_client):
        """Create mock PocketBase plugin."""
        from starstream import StarStreamPlugin
        from starstream_pocketbase import PocketBasePlugin

        stream = StarStreamPlugin(mock_app)
        pb_plugin = PocketBasePlugin(
            stream,
            base_url="http://localhost:9090",
            admin_email="admin@test.com",
            admin_password="test123",
        )

        # Mock the storage client
        pb_plugin._storage._client = mock_pb_client
        pb_plugin._authenticated = True

        return pb_plugin, stream

    @pytest.mark.asyncio
    async def test_create_and_broadcast(self, mock_pb_plugin, mock_pb_client):
        """Test creating record in PocketBase broadcasts via StarStream."""
        pb_plugin, stream = mock_pb_plugin

        # Mock the collection create
        mock_record = Mock()
        mock_record.__dict__ = {"id": "123", "title": "Test Todo", "completed": False}
        mock_collection = Mock()
        mock_collection.create = Mock(return_value=mock_record)
        mock_pb_client.collection = Mock(return_value=mock_collection)

        messages = []

        async def subscriber():
            async for msg in stream.core.subscribe("todos"):
                messages.append(msg)
                break

        task = asyncio.create_task(subscriber())
        await asyncio.sleep(0.1)

        # Initialize sync layer
        from starstream_pocketbase import PocketBaseSync

        pb_plugin._sync = PocketBaseSync(mock_pb_client, stream)

        # Create record (should broadcast)
        result = await pb_plugin._sync.create(
            "todos", {"title": "Test Todo"}, broadcast=True
        )

        try:
            await asyncio.wait_for(task, timeout=1.0)
        except asyncio.TimeoutError:
            task.cancel()

        assert result is not None
        assert result["title"] == "Test Todo"
        assert len(messages) == 1  # Broadcast happened

    @pytest.mark.asyncio
    async def test_update_and_broadcast(self, mock_pb_plugin, mock_pb_client):
        """Test updating record broadcasts change."""
        pb_plugin, stream = mock_pb_plugin

        # Mock the collection update
        mock_record = Mock()
        mock_record.__dict__ = {"id": "123", "title": "Test", "completed": True}
        mock_collection = Mock()
        mock_collection.update = Mock(return_value=mock_record)
        mock_pb_client.collection = Mock(return_value=mock_collection)

        messages = []

        async def subscriber():
            async for msg in stream.core.subscribe("todos"):
                messages.append(msg)
                break

        task = asyncio.create_task(subscriber())
        await asyncio.sleep(0.1)

        # Initialize sync layer
        from starstream_pocketbase import PocketBaseSync

        pb_plugin._sync = PocketBaseSync(mock_pb_client, stream)

        # Update record
        result = await pb_plugin._sync.update(
            "todos", "123", {"completed": True}, broadcast=True
        )

        try:
            await asyncio.wait_for(task, timeout=1.0)
        except asyncio.TimeoutError:
            task.cancel()

        assert result is not None
        assert result["completed"] is True
        assert len(messages) == 1

    @pytest.mark.asyncio
    async def test_delete_and_broadcast(self, mock_pb_plugin, mock_pb_client):
        """Test deleting record broadcasts change."""
        pb_plugin, stream = mock_pb_plugin

        # Mock the collection delete
        mock_collection = Mock()
        mock_collection.delete = Mock(return_value=None)
        mock_pb_client.collection = Mock(return_value=mock_collection)

        messages = []

        async def subscriber():
            async for msg in stream.core.subscribe("todos"):
                messages.append(msg)
                break

        task = asyncio.create_task(subscriber())
        await asyncio.sleep(0.1)

        # Initialize sync layer
        from starstream_pocketbase import PocketBaseSync

        pb_plugin._sync = PocketBaseSync(mock_pb_client, stream)

        # Delete record
        result = await pb_plugin._sync.delete("todos", "123", broadcast=True)

        try:
            await asyncio.wait_for(task, timeout=1.0)
        except asyncio.TimeoutError:
            task.cancel()

        assert result is True
        assert len(messages) == 1

    @pytest.mark.asyncio
    async def test_authentication_flow(self, mock_pb_client):
        """Test PocketBase authentication."""
        from starstream_pocketbase import PocketBaseStorage

        storage = PocketBaseStorage("http://localhost:9090")
        storage._client = mock_pb_client

        # Mock successful auth
        mock_pb_client.admins.auth_with_password = Mock(return_value=None)

        result = await storage.authenticate("admin@test.com", "password123")

        assert result is True
        mock_pb_client.admins.auth_with_password.assert_called_once_with(
            "admin@test.com", "password123"
        )

    @pytest.mark.asyncio
    async def test_query_operations(self, mock_pb_client):
        """Test querying PocketBase."""
        from starstream_pocketbase import PocketBaseStorage

        storage = PocketBaseStorage("http://localhost:9090")
        storage._client = mock_pb_client

        # Mock records
        mock_records = [
            Mock(__dict__={"id": "1", "title": "Todo 1", "completed": False}),
            Mock(__dict__={"id": "2", "title": "Todo 2", "completed": True}),
        ]
        mock_collection = Mock()
        mock_collection.get_full_list = Mock(return_value=mock_records)
        mock_pb_client.collection = Mock(return_value=mock_collection)

        # Test get_all
        results = await storage.get_all("todos")

        assert len(results) == 2
        assert results[0]["title"] == "Todo 1"
        assert results[1]["completed"] is True

    @pytest.mark.asyncio
    async def test_no_broadcast_when_disabled(self, mock_pb_plugin, mock_pb_client):
        """Test that broadcast can be disabled."""
        pb_plugin, stream = mock_pb_plugin

        # Mock the collection create
        mock_record = Mock()
        mock_record.__dict__ = {"id": "123", "title": "Test"}
        mock_collection = Mock()
        mock_collection.create = Mock(return_value=mock_record)
        mock_pb_client.collection = Mock(return_value=mock_collection)

        messages = []

        async def subscriber():
            async for msg in stream.core.subscribe("todos"):
                messages.append(msg)
                break

        task = asyncio.create_task(subscriber())
        await asyncio.sleep(0.1)

        # Initialize sync layer
        from starstream_pocketbase import PocketBaseSync

        pb_plugin._sync = PocketBaseSync(mock_pb_client, stream)

        # Create without broadcast
        result = await pb_plugin._sync.create(
            "todos", {"title": "Test"}, broadcast=False
        )

        try:
            await asyncio.wait_for(task, timeout=0.5)
        except asyncio.TimeoutError:
            task.cancel()

        assert result is not None
        assert len(messages) == 0  # No broadcast

    @pytest.mark.asyncio
    async def test_storage_operations_without_auth(self, mock_pb_client):
        """Test storage operations fail when not authenticated."""
        from starstream_pocketbase import PocketBaseStorage

        storage = PocketBaseStorage("http://localhost:9090")
        storage._client = mock_pb_client
        storage._authenticated = False

        # Try operations without auth
        result = await storage.set("todos", {"title": "Test"})
        assert result is False

        result = await storage.get("todos", "123")
        assert result is None


class TestPocketBasePluginAPI:
    """Test high-level PocketBasePlugin API."""

    @pytest.mark.asyncio
    async def test_plugin_create_method(self, mock_app):
        """Test plugin.create() method."""
        from starstream import StarStreamPlugin
        from starstream_pocketbase import PocketBasePlugin

        stream = StarStreamPlugin(mock_app)
        pb = PocketBasePlugin(stream)

        # Should fail without auth
        result = await pb.create("todos", {"title": "Test"})
        assert result is None

    @pytest.mark.asyncio
    async def test_plugin_get_all_method(self, mock_app, mock_pb_client):
        """Test plugin.get_all() method."""
        from starstream import StarStreamPlugin
        from starstream_pocketbase import PocketBasePlugin

        stream = StarStreamPlugin(mock_app)
        pb = PocketBasePlugin(stream)
        pb._storage._client = mock_pb_client
        pb._authenticated = True

        # Mock records
        mock_records = [
            Mock(__dict__={"id": "1", "title": "Todo 1"}),
        ]
        mock_collection = Mock()
        mock_collection.get_full_list = Mock(return_value=mock_records)
        mock_pb_client.collection = Mock(return_value=mock_collection)

        results = await pb.get_all("todos")

        assert len(results) == 1
        assert results[0]["title"] == "Todo 1"

    @pytest.mark.asyncio
    async def test_plugin_query_method(self, mock_app, mock_pb_client):
        """Test plugin.query() method."""
        from starstream import StarStreamPlugin
        from starstream_pocketbase import PocketBasePlugin

        stream = StarStreamPlugin(mock_app)
        pb = PocketBasePlugin(stream)
        pb._storage._client = mock_pb_client
        pb._authenticated = True

        # Mock records
        mock_records = [
            Mock(__dict__={"id": "1", "title": "Active Todo", "completed": False}),
        ]
        mock_collection = Mock()
        mock_collection.get_full_list = Mock(return_value=mock_records)
        mock_pb_client.collection = Mock(return_value=mock_collection)

        results = await pb.query("todos", "completed = false", "-created")

        assert len(results) == 1
