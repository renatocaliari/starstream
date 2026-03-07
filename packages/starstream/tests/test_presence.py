"""
Unit tests for Presence System.
"""

import pytest
import asyncio
from starstream.presence import Presence
from starstream.tracker import TopicEntry


class TestPresence:
    """Test suite for Presence class."""

    @pytest.fixture
    async def presence(self):
        """Fresh presence instance."""
        p = Presence(expire_after=30)
        yield p

    @pytest.mark.asyncio
    async def test_join_adds_user(self, presence):
        """Verify join adds user to topic."""
        result = await presence.join("room:123", "user_1", {"name": "João"})

        assert result is True
        assert await presence.is_online("room:123", "user_1") is True

    @pytest.mark.asyncio
    async def test_join_returns_false_if_already_present(self, presence):
        """Verify join returns False if user already online."""
        await presence.join("room:123", "user_1")
        result = await presence.join("room:123", "user_1")

        assert result is False

    @pytest.mark.asyncio
    async def test_leave_removes_user(self, presence):
        """Verify leave removes user from topic."""
        await presence.join("room:123", "user_1")
        result = await presence.leave("room:123", "user_1")

        assert result is True
        assert await presence.is_online("room:123", "user_1") is False

    @pytest.mark.asyncio
    async def test_leave_returns_false_if_not_found(self, presence):
        """Verify leave returns False if user not found."""
        result = await presence.leave("room:123", "user_1")

        assert result is False

    @pytest.mark.asyncio
    async def test_get_online_returns_users(self, presence):
        """Verify get_online returns all online users."""
        await presence.join("room:123", "user_1", {"name": "João"})
        await presence.join("room:123", "user_2", {"name": "Maria"})

        online = await presence.get_online("room:123")

        assert len(online) == 2
        assert "user_1" in online
        assert "user_2" in online
        assert online["user_1"]["name"] == "João"
        assert online["user_2"]["name"] == "Maria"

    @pytest.mark.asyncio
    async def test_get_online_returns_empty_if_no_users(self, presence):
        """Verify get_online returns empty dict if no users."""
        online = await presence.get_online("room:123")

        assert online == {}

    @pytest.mark.asyncio
    async def test_heartbeat_updates_last_seen(self, presence):
        """Verify heartbeat updates last_seen timestamp."""
        await presence.join("room:123", "user_1")

        # Wait a bit
        await asyncio.sleep(0.1)

        result = await presence.heartbeat("room:123", "user_1")
        assert result is True

        online = await presence.get_online("room:123")
        assert "last_seen" in online["user_1"]

    @pytest.mark.asyncio
    async def test_heartbeat_returns_false_if_user_not_found(self, presence):
        """Verify heartbeat returns False if user not online."""
        result = await presence.heartbeat("room:123", "user_1")
        assert result is False

    @pytest.mark.asyncio
    async def test_auto_expire_removes_inactive_users(self, presence):
        """Verify expired users are automatically removed."""
        # Create presence with short expiration and check interval
        p = Presence(expire_after=1)
        p.check_interval = 0.5  # Check every 0.5s for faster test
        await p.start()

        try:
            await p.join("room:123", "user_1")
            assert await p.is_online("room:123", "user_1") is True

            # Wait for expiration (> expire_after + check_interval)
            await asyncio.sleep(2.0)

            # User should be removed
            assert await p.is_online("room:123", "user_1") is False
        finally:
            await p.stop()

    @pytest.mark.asyncio
    async def test_get_user_count(self, presence):
        """Verify get_user_count returns correct count."""
        await presence.join("room:123", "user_1")
        await presence.join("room:123", "user_2")

        count = await presence.get_user_count("room:123")
        assert count == 2

    @pytest.mark.asyncio
    async def test_get_all_topics(self, presence):
        """Verify get_all_topics returns all topics with users."""
        await presence.join("room:123", "user_1")
        await presence.join("room:456", "user_2")

        topics = await presence.get_all_topics()

        assert len(topics) == 2
        assert "room:123" in topics
        assert "room:456" in topics

    @pytest.mark.asyncio
    async def test_on_join_callback(self, presence):
        """Verify on_join callback is called."""
        callback_called = False
        callback_data = {}

        async def on_join(topic, user_id, metadata):
            nonlocal callback_called, callback_data
            callback_called = True
            callback_data = {"topic": topic, "user_id": user_id, "metadata": metadata}

        p = Presence(expire_after=30, on_join=on_join)
        await p.start()

        try:
            await p.join("room:123", "user_1", {"name": "João"})

            # Wait for callback
            await asyncio.sleep(0.1)

            assert callback_called is True
            assert callback_data["topic"] == "room:123"
            assert callback_data["user_id"] == "user_1"
            assert callback_data["metadata"]["name"] == "João"
        finally:
            await p.stop()

    @pytest.mark.asyncio
    async def test_on_leave_callback(self, presence):
        """Verify on_leave callback is called."""
        callback_called = False
        callback_data = {}

        async def on_leave(topic, user_id):
            nonlocal callback_called, callback_data
            callback_called = True
            callback_data = {"topic": topic, "user_id": user_id}

        p = Presence(expire_after=30, on_leave=on_leave)
        await p.start()

        try:
            await p.join("room:123", "user_1")
            await p.leave("room:123", "user_1")

            # Wait for callback
            await asyncio.sleep(0.1)

            assert callback_called is True
            assert callback_data["topic"] == "room:123"
            assert callback_data["user_id"] == "user_1"
        finally:
            await p.stop()

    @pytest.mark.asyncio
    async def test_joined_at_preserved_on_rejoin(self, presence):
        """Verify joined_at is preserved when user rejoins."""
        await presence.join("room:123", "user_1")
        online1 = await presence.get_online("room:123")
        joined_at1 = online1["user_1"]["joined_at"]

        # Wait and rejoin
        await asyncio.sleep(0.1)
        await presence.join("room:123", "user_1")

        online2 = await presence.get_online("room:123")
        joined_at2 = online2["user_1"]["joined_at"]

        assert joined_at1 == joined_at2
