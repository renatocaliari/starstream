"""
Unit tests for Message History.
"""

import pytest
import asyncio
from starstream.history import MessageHistory, HistoryEntry


class TestMessageHistory:
    """Test suite for MessageHistory class."""

    @pytest.fixture
    async def history(self):
        """Fresh message history instance."""
        h = MessageHistory(max_per_topic=100)
        yield h

    @pytest.mark.asyncio
    async def test_add_creates_message(self, history):
        """Verify add creates message."""
        msg_id = await history.add("room:123", {"text": "Hello"})

        assert msg_id is not None
        count = await history.get_count("room:123")
        assert count == 1

    @pytest.mark.asyncio
    async def test_add_returns_id(self, history):
        """Verify add returns message ID."""
        msg_id = await history.add("room:123", {"text": "Hello"})

        assert isinstance(msg_id, str)
        assert len(msg_id) > 0

    @pytest.mark.asyncio
    async def test_get_returns_messages(self, history):
        """Verify get returns messages."""
        await history.add("room:123", {"text": "Hello"}, {"user": "joao"})
        await history.add("room:123", {"text": "Hi"}, {"user": "maria"})

        messages = await history.get("room:123")

        assert len(messages) == 2
        assert messages[0]["message"]["text"] == "Hello"
        assert messages[0]["metadata"]["user"] == "joao"
        assert messages[1]["message"]["text"] == "Hi"
        assert messages[1]["metadata"]["user"] == "maria"

    @pytest.mark.asyncio
    async def test_get_returns_empty_if_no_messages(self, history):
        """Verify get returns empty list if no messages."""
        messages = await history.get("room:123")

        assert messages == []

    @pytest.mark.asyncio
    async def test_get_respects_limit(self, history):
        """Verify get respects limit."""
        for i in range(10):
            await history.add("room:123", {"text": f"msg{i}"})

        messages = await history.get("room:123", limit=5)

        assert len(messages) == 5

    @pytest.mark.asyncio
    async def test_get_returns_most_recent(self, history):
        """Verify get returns most recent messages."""
        for i in range(5):
            await history.add("room:123", {"text": f"msg{i}"})

        messages = await history.get("room:123", limit=3)

        # Should be msg2, msg3, msg4 (most recent)
        assert messages[0]["message"]["text"] == "msg2"
        assert messages[2]["message"]["text"] == "msg4"

    @pytest.mark.asyncio
    async def test_clear_removes_all(self, history):
        """Verify clear removes all messages."""
        await history.add("room:123", {"text": "Hello"})
        await history.add("room:123", {"text": "Hi"})

        result = await history.clear("room:123")

        assert result is True
        count = await history.get_count("room:123")
        assert count == 0

    @pytest.mark.asyncio
    async def test_clear_returns_false_if_not_found(self, history):
        """Verify clear returns False if topic not found."""
        result = await history.clear("room:123")

        assert result is False

    @pytest.mark.asyncio
    async def test_get_count(self, history):
        """Verify get_count returns correct count."""
        await history.add("room:123", {"text": "Hello"})
        await history.add("room:123", {"text": "Hi"})

        count = await history.get_count("room:123")
        assert count == 2

    @pytest.mark.asyncio
    async def test_get_all_topics(self, history):
        """Verify get_all_topics returns all topics."""
        await history.add("room:123", {"text": "Hello"})
        await history.add("room:456", {"text": "Hi"})

        topics = await history.get_all_topics()

        assert len(topics) == 2
        assert "room:123" in topics
        assert "room:456" in topics

    @pytest.mark.asyncio
    async def test_messages_isolated_per_topic(self, history):
        """Verify messages are isolated per topic."""
        await history.add("room:123", {"text": "Hello"})
        await history.add("room:456", {"text": "Hi"})

        messages123 = await history.get("room:123")
        messages456 = await history.get("room:456")

        assert len(messages123) == 1
        assert len(messages456) == 1
        assert messages123[0]["message"]["text"] == "Hello"
        assert messages456[0]["message"]["text"] == "Hi"

    @pytest.mark.asyncio
    async def test_max_per_topic_limit(self, history):
        """Verify max_per_topic limits messages."""
        h = MessageHistory(max_per_topic=3)

        for i in range(5):
            await h.add("room:123", {"text": f"msg{i}"})

        messages = await h.get("room:123", limit=10)

        assert len(messages) == 3  # Only 3 kept
        assert messages[0]["message"]["text"] == "msg2"
        assert messages[2]["message"]["text"] == "msg4"
