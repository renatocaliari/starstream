"""
Unit tests for StarStreamCore functionality.
"""

import pytest
import asyncio
from starstream.plugin import StarStreamCore


class TestStarStreamCore:
    """Test suite for StarStreamCore class."""

    @pytest.mark.asyncio
    async def test_subscribe_creates_topic(self, core):
        """Verify that subscribing creates a new topic."""
        # Initially no topics
        assert len(core._topics) == 0

        # Start subscription (don't await to avoid blocking)
        task = asyncio.create_task(self._collect_messages(core, "test-topic"))
        await asyncio.sleep(0.1)  # Let subscription register

        # Topic should exist now
        assert "test-topic" in core._topics
        assert len(core._topics["test-topic"]) == 1

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_broadcast_to_topic(self, core):
        """Verify broadcasting to a specific topic works."""
        messages = []

        # Create subscriber
        async def subscriber():
            async for msg in core.subscribe("broadcast-test"):
                messages.append(msg)
                break

        task = asyncio.create_task(subscriber())
        await asyncio.sleep(0.1)  # Let subscriber register

        # Broadcast message
        await core.broadcast("Hello, World!", topic="broadcast-test")

        # Wait for message
        try:
            await asyncio.wait_for(task, timeout=1.0)
        except asyncio.TimeoutError:
            task.cancel()

        # Verify message received
        assert len(messages) == 1
        assert "Hello, World!" in messages[0]

    @pytest.mark.asyncio
    async def test_broadcast_to_multiple_subscribers(self, core):
        """Verify broadcasting reaches multiple subscribers."""
        messages_1 = []
        messages_2 = []

        # Create two subscribers
        async def subscriber_1():
            async for msg in core.subscribe("multi-test"):
                messages_1.append(msg)
                break

        async def subscriber_2():
            async for msg in core.subscribe("multi-test"):
                messages_2.append(msg)
                break

        task_1 = asyncio.create_task(subscriber_1())
        task_2 = asyncio.create_task(subscriber_2())
        await asyncio.sleep(0.1)

        # Broadcast
        await core.broadcast("Multi-message", topic="multi-test")

        # Wait for both
        try:
            await asyncio.wait_for(asyncio.gather(task_1, task_2), timeout=1.0)
        except asyncio.TimeoutError:
            task_1.cancel()
            task_2.cancel()

        # Both should receive
        assert len(messages_1) == 1
        assert len(messages_2) == 1
        assert "Multi-message" in messages_1[0]
        assert "Multi-message" in messages_2[0]

    def test_message_formatting_string(self, core):
        """Verify string message formatting."""
        formatted = core._format_message("Test message")
        assert "data: Test message" in formatted

    def test_message_formatting_elements(self, core):
        """Verify elements message formatting."""
        # Format: ('elements', (content, selector, mode, use_vt, signals))
        message = ("elements", ("<div>Hello</div>", "#chat", "append", False, None))
        formatted = core._format_message(message)

        assert "event: datastar-patch-elements" in formatted
        assert "data: selector #chat" in formatted
        assert "data: mode append" in formatted
        assert "data: elements <div>Hello</div>" in formatted

    def test_message_formatting_signals(self, core):
        """Verify signals message formatting."""
        # Format: ('signals', {'counter': 42})
        message = ("signals", {"counter": 42, "status": "active"})
        formatted = core._format_message(message)

        assert "event: datastar-patch-signals" in formatted
        assert "data: signals" in formatted
        assert '"counter": 42' in formatted
        assert '"status": "active"' in formatted

    @pytest.mark.asyncio
    async def test_unsubscribe_cleanup(self, core):
        """Verify cleanup when subscriber disconnects."""
        topic = "cleanup-test"

        # Subscribe
        async def subscriber():
            async for msg in core.subscribe(topic):
                break

        task = asyncio.create_task(subscriber())
        await asyncio.sleep(0.1)

        # Should have subscriber
        assert topic in core._topics
        assert len(core._topics[topic]) == 1

        # Cancel subscription
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        await asyncio.sleep(0.1)

        # Topic should be cleaned up
        assert topic not in core._topics

    @pytest.mark.asyncio
    async def test_empty_topic_cleanup(self, core):
        """Verify empty topics are removed."""
        topic = "empty-test"

        # Create subscriber
        async def subscriber():
            async for msg in core.subscribe(topic):
                break

        task = asyncio.create_task(subscriber())
        await asyncio.sleep(0.1)

        # Topic exists
        assert topic in core._topics

        # Cancel and cleanup
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        await asyncio.sleep(0.1)

        # Topic removed
        assert topic not in core._topics

    @pytest.mark.asyncio
    async def test_multiple_topics_isolation(self, core):
        """Verify messages don't cross between topics."""
        topic_a_msgs = []
        topic_b_msgs = []

        async def subscriber_a():
            async for msg in core.subscribe("topic-a"):
                topic_a_msgs.append(msg)
                break

        async def subscriber_b():
            async for msg in core.subscribe("topic-b"):
                topic_b_msgs.append(msg)
                break

        task_a = asyncio.create_task(subscriber_a())
        task_b = asyncio.create_task(subscriber_b())
        await asyncio.sleep(0.1)

        # Broadcast to topic A only
        await core.broadcast("Only A", topic="topic-a")

        try:
            await asyncio.wait_for(task_a, timeout=1.0)
        except asyncio.TimeoutError:
            task_a.cancel()

        # Subscriber B should timeout (no message)
        try:
            await asyncio.wait_for(task_b, timeout=0.5)
            assert False, "Should have timed out"
        except asyncio.TimeoutError:
            pass  # Expected

        task_b.cancel()

        # Only A received message
        assert len(topic_a_msgs) == 1
        assert len(topic_b_msgs) == 0

    # Helper methods

    async def _collect_messages(self, core, topic, count=1):
        """Helper to collect messages from a topic."""
        messages = []
        async for msg in core.subscribe(topic):
            messages.append(msg)
            if len(messages) >= count:
                break
        return messages
