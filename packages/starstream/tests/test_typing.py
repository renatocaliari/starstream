"""
Unit tests for Typing Indicators.
"""

import pytest
import asyncio
from starstream.typing import TypingIndicator


class TestTypingIndicator:
    """Test suite for TypingIndicator class."""

    @pytest.fixture
    async def typing(self):
        """Fresh typing indicator instance."""
        t = TypingIndicator(auto_stop_after=0.5)
        yield t

    @pytest.mark.asyncio
    async def test_start_adds_user(self, typing):
        """Verify start adds user to typing."""
        result = await typing.start("room:123", "user_1")

        assert result is True
        assert await typing.is_typing("room:123", "user_1") is True

    @pytest.mark.asyncio
    async def test_start_returns_false_if_already_typing(self, typing):
        """Verify start returns False if user already typing."""
        await typing.start("room:123", "user_1")
        result = await typing.start("room:123", "user_1")

        assert result is False

    @pytest.mark.asyncio
    async def test_stop_removes_user(self, typing):
        """Verify stop removes user from typing."""
        await typing.start("room:123", "user_1")
        result = await typing.stop("room:123", "user_1")

        assert result is True
        assert await typing.is_typing("room:123", "user_1") is False

    @pytest.mark.asyncio
    async def test_stop_returns_false_if_not_found(self, typing):
        """Verify stop returns False if user not typing."""
        result = await typing.stop("room:123", "user_1")

        assert result is False

    @pytest.mark.asyncio
    async def test_get_typing_returns_users(self, typing):
        """Verify get_typing returns all typing users."""
        await typing.start("room:123", "user_1")
        await typing.start("room:123", "user_2")

        typing_users = await typing.get_typing("room:123")

        assert len(typing_users) == 2
        assert "user_1" in typing_users
        assert "user_2" in typing_users

    @pytest.mark.asyncio
    async def test_get_typing_returns_empty_if_no_users(self, typing):
        """Verify get_typing returns empty set if no users."""
        typing_users = await typing.get_typing("room:123")

        assert typing_users == set()

    @pytest.mark.asyncio
    async def test_auto_stop_removes_inactive_users(self, typing):
        """Verify auto-stop removes users after timeout."""
        await typing.start("room:123", "user_1")
        assert await typing.is_typing("room:123", "user_1") is True

        # Wait for auto-stop
        await asyncio.sleep(0.7)

        # User should be removed
        assert await typing.is_typing("room:123", "user_1") is False

    @pytest.mark.asyncio
    async def test_get_typing_count(self, typing):
        """Verify get_typing_count returns correct count."""
        await typing.start("room:123", "user_1")
        await typing.start("room:123", "user_2")

        count = await typing.get_typing_count("room:123")
        assert count == 2

    @pytest.mark.asyncio
    async def test_stop_all_removes_all_users(self, typing):
        """Verify stop_all removes all typing users in topic."""
        await typing.start("room:123", "user_1")
        await typing.start("room:123", "user_2")

        await typing.stop_all("room:123")

        assert await typing.is_typing("room:123", "user_1") is False
        assert await typing.is_typing("room:123", "user_2") is False

    @pytest.mark.asyncio
    async def test_on_start_callback(self, typing):
        """Verify on_start callback is called."""
        callback_called = False
        callback_data = {}

        async def on_start(topic, user_id):
            nonlocal callback_called, callback_data
            callback_called = True
            callback_data = {"topic": topic, "user_id": user_id}

        t = TypingIndicator(auto_stop_after=0.5, on_start=on_start)

        await t.start("room:123", "user_1")

        # Wait for callback
        await asyncio.sleep(0.1)

        assert callback_called is True
        assert callback_data["topic"] == "room:123"
        assert callback_data["user_id"] == "user_1"

    @pytest.mark.asyncio
    async def test_on_stop_callback(self, typing):
        """Verify on_stop callback is called."""
        callback_called = False
        callback_data = {}

        async def on_stop(topic, user_id):
            nonlocal callback_called, callback_data
            callback_called = True
            callback_data = {"topic": topic, "user_id": user_id}

        t = TypingIndicator(auto_stop_after=0.5, on_stop=on_stop)

        await t.start("room:123", "user_1")
        await t.stop("room:123", "user_1")

        # Wait for callback
        await asyncio.sleep(0.1)

        assert callback_called is True
        assert callback_data["topic"] == "room:123"
        assert callback_data["user_id"] == "user_1"

    @pytest.mark.asyncio
    async def test_typing_in_different_topics(self, typing):
        """Verify typing is isolated per topic."""
        await typing.start("room:123", "user_1")
        await typing.start("room:456", "user_1")

        assert await typing.is_typing("room:123", "user_1") is True
        assert await typing.is_typing("room:456", "user_1") is True

        # Stop in one topic shouldn't affect other
        await typing.stop("room:123", "user_1")

        assert await typing.is_typing("room:123", "user_1") is False
        assert await typing.is_typing("room:456", "user_1") is True
