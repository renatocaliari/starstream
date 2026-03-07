"""
Unit tests for helper utilities (throttle, debounce, rate limiter, message builder).
"""

import pytest
import asyncio
from starstream.helpers import (
    throttle,
    debounce,
    RateLimiter,
    MessageBuilder,
    generate_topic,
    parse_topic,
    is_room_topic,
    is_user_topic,
    extract_room_id,
    extract_user_id,
)


class TestThrottle:
    """Test throttle decorator."""

    @pytest.mark.asyncio
    async def test_throttle_decorator(self):
        """Verify throttle limits calls."""
        calls = []

        @throttle(0.1)  # 100ms throttle
        async def my_func(x):
            calls.append(x)

        # Rapid calls
        await my_func(1)
        await my_func(2)
        await my_func(3)

        # Only first should execute immediately
        assert len(calls) == 1
        assert calls[0] == 1

    @pytest.mark.asyncio
    async def test_throttle_allows_after_period(self):
        """Verify throttle allows calls after period."""
        calls = []

        @throttle(0.05)  # 50ms throttle
        async def my_func(x):
            calls.append(x)

        await my_func(1)
        await asyncio.sleep(0.06)  # Wait for throttle period
        await my_func(2)

        # Both should execute
        assert len(calls) == 2
        assert calls == [1, 2]


class TestDebounce:
    """Test debounce decorator."""

    @pytest.mark.asyncio
    async def test_debounce_decorator(self):
        """Verify debounce waits for pause."""
        calls = []

        @debounce(0.1)  # 100ms debounce
        async def my_func(x):
            calls.append(x)

        # Rapid calls
        task1 = await my_func(1)
        task2 = await my_func(2)
        task3 = await my_func(3)

        # Wait for debounce period
        await asyncio.sleep(0.15)

        # Only last call should execute
        assert len(calls) == 1
        assert calls[0] == 3

    @pytest.mark.asyncio
    async def test_debounce_cancels_previous(self):
        """Verify debounce cancels previous calls."""
        calls = []

        @debounce(0.1)
        async def my_func(x):
            calls.append(x)

        task1 = await my_func(1)
        await asyncio.sleep(0.02)
        task2 = await my_func(2)
        await asyncio.sleep(0.02)
        task3 = await my_func(3)

        await asyncio.sleep(0.15)

        # Only last should execute
        assert len(calls) == 1
        assert calls[0] == 3


class TestRateLimiter:
    """Test rate limiter."""

    @pytest.mark.asyncio
    async def test_rate_limiter_acquire(self):
        """Verify rate limiter allows up to limit."""
        limiter = RateLimiter(max_calls=3, per_seconds=1.0)

        # Should allow first 3
        assert await limiter.acquire() is True
        assert await limiter.acquire() is True
        assert await limiter.acquire() is True

    @pytest.mark.asyncio
    async def test_rate_limiter_blocks_over_limit(self):
        """Verify rate limiter blocks over limit."""
        limiter = RateLimiter(max_calls=2, per_seconds=1.0)

        # Use up quota
        await limiter.acquire()
        await limiter.acquire()

        # Should block
        assert await limiter.acquire() is False

    @pytest.mark.asyncio
    async def test_rate_limiter_refreshes(self):
        """Verify rate limiter refreshes after period."""
        limiter = RateLimiter(max_calls=1, per_seconds=0.05)

        # Use quota
        await limiter.acquire()
        assert await limiter.acquire() is False

        # Wait for refresh
        await asyncio.sleep(0.06)

        # Should allow again
        assert await limiter.acquire() is True

    @pytest.mark.asyncio
    async def test_rate_limiter_wait(self):
        """Verify wait method waits for slot."""
        limiter = RateLimiter(max_calls=1, per_seconds=0.05)

        # Use quota
        await limiter.acquire()

        # Start wait in background
        start_time = asyncio.get_event_loop().time()
        await limiter.wait()
        end_time = asyncio.get_event_loop().time()

        # Should have waited
        assert end_time - start_time >= 0.04


class TestMessageBuilder:
    """Test message builder utilities."""

    def test_signal_update(self):
        """Build signal update message."""
        msg = MessageBuilder.signal_update(counter=42, status="active")

        assert msg[0] == "signals"
        assert msg[1] == {"counter": 42, "status": "active"}

    def test_element_append(self):
        """Build element append message."""
        content = "<div>Hello</div>"
        msg = MessageBuilder.element_append("#chat", content)

        assert msg[0] == "elements"
        assert msg[1][0] == content
        assert msg[1][1] == "#chat"
        assert msg[1][2] == "append"
        assert msg[1][3] is False

    def test_element_append_with_transition(self):
        """Build element append with view transition."""
        content = "<div>Hello</div>"
        msg = MessageBuilder.element_append("#chat", content, use_view_transition=True)

        assert msg[1][3] is True

    def test_element_replace(self):
        """Build element replace message."""
        content = "<div>New</div>"
        msg = MessageBuilder.element_replace("#content", content)

        assert msg[0] == "elements"
        assert msg[1][0] == content
        assert msg[1][1] == "#content"
        assert msg[1][2] == "replace"

    def test_notification(self):
        """Build notification message."""
        msg = MessageBuilder.notification("Test message", type_="success")

        assert msg[0] == "signals"
        assert "notification" in msg[1]
        assert msg[1]["notification"]["text"] == "Test message"
        assert msg[1]["notification"]["type"] == "success"
        assert "timestamp" in msg[1]["notification"]

    def test_toast(self):
        """Build toast message."""
        msg = MessageBuilder.toast("Saved!", duration=5000)

        assert msg[0] == "signals"
        assert "toast" in msg[1]
        assert msg[1]["toast"]["message"] == "Saved!"
        assert msg[1]["toast"]["duration"] == 5000


class TestTopicUtilities:
    """Test topic utility functions."""

    def test_generate_topic(self):
        """Generate topic from parts."""
        assert generate_topic("room", "123") == "room:123"
        assert generate_topic("user", "john", "dm") == "user:john:dm"
        assert generate_topic("chat") == "chat"

    def test_parse_topic(self):
        """Parse topic into parts."""
        assert parse_topic("room:123") == ["room", "123"]
        assert parse_topic("user:john:dm") == ["user", "john", "dm"]

    def test_is_room_topic(self):
        """Check if topic is room topic."""
        assert is_room_topic("room:123") is True
        assert is_room_topic("user:john") is False
        assert is_room_topic("global") is False

    def test_is_user_topic(self):
        """Check if topic is user topic."""
        assert is_user_topic("user:john") is True
        assert is_user_topic("room:123") is False
        assert is_user_topic("global") is False

    def test_extract_room_id(self):
        """Extract room ID from topic."""
        assert extract_room_id("room:123") == "123"
        assert extract_room_id("room:general") == "general"
        assert extract_room_id("user:john") is None

    def test_extract_user_id(self):
        """Extract user ID from topic."""
        assert extract_user_id("user:john") == "john"
        assert extract_user_id("user:123") == "123"
        assert extract_user_id("room:general") is None
