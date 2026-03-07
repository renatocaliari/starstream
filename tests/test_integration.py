"""
Integration tests for StarStreamPlugin.
"""

import pytest
import asyncio
from starstream.plugin import StarStreamPlugin


class TestPluginIntegration:
    """Test plugin integration with mock app."""

    def test_plugin_initialization(self, mock_app):
        """Verify plugin initializes correctly."""
        plugin = StarStreamPlugin(mock_app)

        assert plugin.app == mock_app
        assert plugin.default_topic == "global"
        assert plugin.core is not None

    def test_sse_endpoint_registered(self, mock_app):
        """Verify /starstream endpoint is registered."""
        plugin = StarStreamPlugin(mock_app)

        # Check route was registered
        route_paths = [route[0] for route in mock_app.routes]
        assert "/starstream" in route_paths

    def test_auto_topic_detection_from_kwargs(self, plugin):
        """Verify auto-topic detection from kwargs."""
        # Room ID
        topic = plugin._auto_detect_topic("/any", {"room_id": "123"})
        assert topic == "room:123"

        # User ID
        topic = plugin._auto_detect_topic("/any", {"user_id": "456"})
        assert topic == "user:456"

        # Route path
        topic = plugin._auto_detect_topic("/chat/notifications", {})
        assert topic == "chat:notifications"

    @pytest.mark.asyncio
    async def test_manual_broadcast_api(self, plugin):
        """Verify manual broadcast API works."""
        messages = []

        # Subscribe
        async def subscriber():
            async for msg in plugin.core.subscribe("manual-test"):
                messages.append(msg)
                break

        task = asyncio.create_task(subscriber())
        await asyncio.sleep(0.1)

        # Broadcast manually
        await plugin.broadcast("Manual message", "manual-test")

        try:
            await asyncio.wait_for(task, timeout=1.0)
        except asyncio.TimeoutError:
            task.cancel()

        assert len(messages) == 1
        assert "Manual message" in messages[0]

    @pytest.mark.asyncio
    async def test_broadcast_to_room(self, plugin):
        """Verify room-specific broadcast."""
        messages = []

        async def subscriber():
            async for msg in plugin.core.subscribe("room:general"):
                messages.append(msg)
                break

        task = asyncio.create_task(subscriber())
        await asyncio.sleep(0.1)

        await plugin.broadcast("Room message", "room:general")

        try:
            await asyncio.wait_for(task, timeout=1.0)
        except asyncio.TimeoutError:
            task.cancel()

        assert len(messages) == 1

    @pytest.mark.asyncio
    async def test_send_to_user(self, plugin):
        """Verify user-specific broadcast."""
        messages = []

        async def subscriber():
            async for msg in plugin.core.subscribe("user:john"):
                messages.append(msg)
                break

        task = asyncio.create_task(subscriber())
        await asyncio.sleep(0.1)

        await plugin.broadcast("Private message", "user:john")

        try:
            await asyncio.wait_for(task, timeout=1.0)
        except asyncio.TimeoutError:
            task.cancel()

        assert len(messages) == 1

    def test_get_stream_url(self, plugin):
        """Verify stream URL generation."""
        url = plugin.get_stream_url()
        assert url == "/starstream?topic=global"

        url = plugin.get_stream_url("room:123")
        assert url == "/starstream?topic=room:123"

    def test_configure_decorator(self, plugin):
        """Verify configuration decorator."""

        @plugin.configure(topic="custom-topic")
        async def my_endpoint():
            pass

        assert hasattr(my_endpoint, "_starstream_config")
        assert my_endpoint._starstream_config["topic"] == "custom-topic"

    def test_configure_with_filter(self, plugin):
        """Verify configuration with filter."""
        filter_fn = lambda ctx: ctx.get("is_admin", False)

        @plugin.configure(filter_fn=filter_fn)
        async def admin_endpoint():
            pass

        assert admin_endpoint._starstream_config["filter_fn"] == filter_fn

    def test_custom_default_topic(self, mock_app):
        """Verify custom default topic."""
        plugin = StarStreamPlugin(mock_app, default_topic="custom")
        assert plugin.default_topic == "custom"
