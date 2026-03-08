"""
Test multiple topics streaming.
"""

import pytest
from starhtml import Div
from starstream import StarStreamPlugin


class TestMultiTopicStreaming:
    """Test streaming to multiple topics."""

    def test_get_stream_element_single(self, mock_app):
        """Test getting stream element for single topic."""
        plugin = StarStreamPlugin(mock_app)
        element = plugin.get_stream_element("chat:123")

        # Check that element contains the correct SSE URL
        element_str = str(element)
        assert 'data-star-sse="connect:/starstream?topic=chat:123"' in element_str
        assert "<div" in element_str

    def test_get_stream_element_multiple(self, mock_app):
        """Test getting stream elements for multiple topics."""
        plugin = StarStreamPlugin(mock_app)
        elements = plugin.get_stream_element(["chat:123", "notifications", "presence"])

        assert isinstance(elements, list)
        assert len(elements) == 3
        # Check each element contains correct SSE URL
        assert 'data-star-sse="connect:/starstream?topic=chat:123"' in str(elements[0])
        assert 'data-star-sse="connect:/starstream?topic=notifications"' in str(elements[1])
        assert 'data-star-sse="connect:/starstream?topic=presence"' in str(elements[2])

    def test_get_stream_element_empty_list(self, mock_app):
        """Test getting stream elements with empty list."""
        plugin = StarStreamPlugin(mock_app)
        elements = plugin.get_stream_element([])

        assert isinstance(elements, list)
        assert len(elements) == 0

    def test_get_stream_element_default(self, mock_app):
        """Test getting stream element with default topic."""
        plugin = StarStreamPlugin(mock_app)
        element = plugin.get_stream_element()

        # Default topic is "global"
        assert 'data-star-sse="connect:/starstream?topic=global"' in str(element)

    @pytest.mark.asyncio
    async def test_broadcast_to_multiple_topics(self, mock_app):
        """Test broadcasting to multiple topics."""
        plugin = StarStreamPlugin(mock_app)
        messages = []

        async def subscriber_chat():
            async for msg in plugin.core.subscribe("chat"):
                messages.append(("chat", msg))
                break

        async def subscriber_notifs():
            async for msg in plugin.core.subscribe("notifications"):
                messages.append(("notifications", msg))
                break

        import asyncio

        task1 = asyncio.create_task(subscriber_chat())
        task2 = asyncio.create_task(subscriber_notifs())
        await asyncio.sleep(0.1)

        # Broadcast to each topic
        plugin.broadcast("Hello chat!", "chat")
        plugin.broadcast("New notification!", "notifications")

        try:
            await asyncio.wait_for(asyncio.gather(task1, task2), timeout=1.0)
        except asyncio.TimeoutError:
            task1.cancel()
            task2.cancel()

        assert len(messages) == 2
        # Messages come formatted with SSE prefix
        assert any(msg[0] == "chat" and "Hello chat!" in msg[1] for msg in messages)
        assert any(msg[0] == "notifications" and "New notification!" in msg[1] for msg in messages)
