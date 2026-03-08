"""
Test unified broadcast API.
"""

import pytest
import asyncio
from starstream import StarStreamPlugin


class TestUnifiedBroadcast:
    """Test the unified broadcast method."""

    @pytest.mark.asyncio
    async def test_broadcast_with_string_target(self, mock_app):
        """Test broadcast with string target (auto-detect)."""
        plugin = StarStreamPlugin(mock_app)
        messages = []

        async def subscriber():
            async for msg in plugin.core.subscribe("global"):
                messages.append(msg)
                break

        task = asyncio.create_task(subscriber())
        await asyncio.sleep(0.1)

        # String target
        plugin.broadcast("Hello!", target="global")

        try:
            await asyncio.wait_for(task, timeout=1.0)
        except asyncio.TimeoutError:
            task.cancel()

        assert len(messages) == 1
        assert "Hello!" in messages[0]

    @pytest.mark.asyncio
    async def test_broadcast_with_room_prefix(self, mock_app):
        """Test broadcast with room: prefix."""
        plugin = StarStreamPlugin(mock_app)
        messages = []

        async def subscriber():
            async for msg in plugin.core.subscribe("room:123"):
                messages.append(msg)
                break

        task = asyncio.create_task(subscriber())
        await asyncio.sleep(0.1)

        plugin.broadcast("Room message!", target="room:123")

        try:
            await asyncio.wait_for(task, timeout=1.0)
        except asyncio.TimeoutError:
            task.cancel()

        assert len(messages) == 1
        assert "Room message!" in messages[0]

    @pytest.mark.asyncio
    async def test_broadcast_with_user_prefix(self, mock_app):
        """Test broadcast with user: prefix."""
        plugin = StarStreamPlugin(mock_app)
        messages = []

        async def subscriber():
            async for msg in plugin.core.subscribe("user:456"):
                messages.append(msg)
                break

        task = asyncio.create_task(subscriber())
        await asyncio.sleep(0.1)

        plugin.broadcast("User message!", target="user:456")

        try:
            await asyncio.wait_for(task, timeout=1.0)
        except asyncio.TimeoutError:
            task.cancel()

        assert len(messages) == 1
        assert "User message!" in messages[0]

    @pytest.mark.asyncio
    async def test_broadcast_with_dict_target(self, mock_app):
        """Test broadcast with dict target."""
        plugin = StarStreamPlugin(mock_app)
        messages = []

        async def subscriber():
            async for msg in plugin.core.subscribe("room:789"):
                messages.append(msg)
                break

        task = asyncio.create_task(subscriber())
        await asyncio.sleep(0.1)

        plugin.broadcast("Dict target!", target={"type": "room", "id": "789"})

        try:
            await asyncio.wait_for(task, timeout=1.0)
        except asyncio.TimeoutError:
            task.cancel()

        assert len(messages) == 1
        assert "Dict target!" in messages[0]

    @pytest.mark.asyncio
    async def test_broadcast_auto_detect_no_target(self, mock_app):
        """Test broadcast with no target (uses default)."""
        plugin = StarStreamPlugin(mock_app, default_topic="custom_default")
        messages = []

        async def subscriber():
            async for msg in plugin.core.subscribe("custom_default"):
                messages.append(msg)
                break

        task = asyncio.create_task(subscriber())
        await asyncio.sleep(0.1)

        plugin.broadcast("Default topic!")  # No target

        try:
            await asyncio.wait_for(task, timeout=1.0)
        except asyncio.TimeoutError:
            task.cancel()

        assert len(messages) == 1
        assert "Default topic!" in messages[0]

    @pytest.mark.asyncio
    async def test_legacy_broadcast_methods(self, mock_app):
        """Test that legacy methods still work."""
        plugin = StarStreamPlugin(mock_app)
        messages = []

        async def subscriber():
            async for msg in plugin.core.subscribe("legacy_topic"):
                messages.append(msg)
                break

        task = asyncio.create_task(subscriber())
        await asyncio.sleep(0.1)

        # Unified broadcast method
        plugin.broadcast("Legacy message!", "legacy_topic")

        try:
            await asyncio.wait_for(task, timeout=1.0)
        except asyncio.TimeoutError:
            task.cancel()

        assert len(messages) == 1
        assert "Legacy message!" in messages[0]

    @pytest.mark.asyncio
    async def test_broadcast_multiple_targets(self, mock_app):
        """Test broadcasting to multiple targets."""
        plugin = StarStreamPlugin(mock_app)
        messages = []

        async def subscriber_chat():
            async for msg in plugin.core.subscribe("chat"):
                messages.append(("chat", msg))
                break

        async def subscriber_notifs():
            async for msg in plugin.core.subscribe("notifications"):
                messages.append(("notifs", msg))
                break

        task1 = asyncio.create_task(subscriber_chat())
        task2 = asyncio.create_task(subscriber_notifs())
        await asyncio.sleep(0.1)

        # Broadcast to each
        plugin.broadcast("Chat msg", target="chat")
        plugin.broadcast("Notif msg", target="notifications")

        try:
            await asyncio.wait_for(asyncio.gather(task1, task2), timeout=1.0)
        except asyncio.TimeoutError:
            task1.cancel()
            task2.cancel()

        assert len(messages) == 2
