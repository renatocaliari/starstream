"""
Message History - Store and retrieve message history.

Provides message history with TTL and limits.
"""

import asyncio
import inspect
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import deque


@dataclass
class HistoryEntry:
    """Represents a message in history."""

    topic: str
    message: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    id: str = field(default_factory=lambda: str(time.time()))


class MessageHistory:
    """
    Store and retrieve message history per topic.

    Example:
        history = MessageHistory(max_per_topic=1000, ttl=86400)

        # Add message
        await history.add("room:123", {"text": "Hello!"}, {"user": "joao"})

        # Get history
        messages = await history.get("room:123", limit=50)
        # → [{"text": "Hello!", "user": "joao", "timestamp": 1234567890}]
    """

    def __init__(
        self,
        max_per_topic: int = 1000,
        ttl: Optional[int] = None,  # seconds
        on_add: Optional[callable] = None,
        on_clear: Optional[callable] = None,
    ):
        """
        Initialize message history.

        Args:
            max_per_topic: Maximum messages per topic
            ttl: Time-to-live in seconds (None = no expiration)
            on_add: Callback when message added (topic, message)
            on_clear: Callback when history cleared (topic)
        """
        self.max_per_topic = max_per_topic
        self.ttl = ttl
        self.on_add = on_add
        self.on_clear = on_clear

        # Storage: {topic: deque of HistoryEntry}
        self._history: Dict[str, deque] = {}
        self._lock = asyncio.Lock()

    async def add(self, topic: str, message: Any, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Add a message to history.

        Args:
            topic: Topic identifier
            message: Message content
            metadata: Optional metadata

        Returns:
            ID of the added message
        """
        async with self._lock:
            if topic not in self._history:
                self._history[topic] = deque(maxlen=self.max_per_topic)

            entry = HistoryEntry(topic=topic, message=message, metadata=metadata or {})

            self._history[topic].append(entry)

            # Cleanup expired if TTL is set
            if self.ttl:
                await self._cleanup_expired(topic)

        # Call callback
        if self.on_add:
            asyncio.create_task(self._call_callback(self.on_add, topic, message))

        return entry.id

    async def get(
        self, topic: str, limit: int = 50, before: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Get message history for a topic.

        Args:
            topic: Topic identifier
            limit: Maximum number of messages
            before: Get messages before this timestamp

        Returns:
            List of messages with metadata
        """
        async with self._lock:
            if topic not in self._history:
                return []

            # Cleanup expired if TTL is set
            if self.ttl:
                await self._cleanup_expired(topic)

            entries = list(self._history[topic])

            # Filter by timestamp if specified
            if before:
                entries = [e for e in entries if e.timestamp < before]

            # Return most recent first, limited
            entries = entries[-limit:]

            return [
                {
                    "id": entry.id,
                    "message": entry.message,
                    "metadata": entry.metadata,
                    "timestamp": entry.timestamp,
                }
                for entry in entries
            ]

    async def clear(self, topic: str) -> bool:
        """
        Clear all messages for a topic.

        Args:
            topic: Topic identifier

        Returns:
            True if cleared, False if topic not found
        """
        async with self._lock:
            if topic not in self._history:
                return False

            del self._history[topic]

        # Call callback
        if self.on_clear:
            asyncio.create_task(self._call_callback(self.on_clear, topic))

        return True

    async def get_count(self, topic: str) -> int:
        """Get number of messages in a topic."""
        async with self._lock:
            if topic not in self._history:
                return 0

            return len(self._history[topic])

    async def get_all_topics(self) -> List[str]:
        """Get list of all topics with history."""
        async with self._lock:
            return list(self._history.keys())

    async def _cleanup_expired(self, topic: str):
        """Remove expired messages from a topic."""
        if not self.ttl or topic not in self._history:
            return

        now = time.time()
        cutoff = now - self.ttl

        # Filter out expired entries
        self._history[topic] = deque(
            [e for e in self._history[topic] if e.timestamp > cutoff],
            maxlen=self.max_per_topic,
        )

    async def _call_callback(self, callback, *args):
        """Safely call a callback, catching exceptions."""
        try:
            if inspect.iscoroutinefunction(callback):
                await callback(*args)
            else:
                callback(*args)
        except Exception as e:
            print(f"Message history callback error: {e}")
