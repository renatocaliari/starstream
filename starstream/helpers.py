"""
Helper utilities for StarStream
"""

import asyncio
import time
from typing import Any, Optional
from functools import wraps


def throttle(seconds: float):
    """
    Decorator to throttle function calls.

    Example:
        @throttle(0.1)  # Max 10 calls per second
        async def send_cursor_update(x, y):
            await stream.broadcast(...)
    """

    def decorator(func):
        last_call = 0

        @wraps(func)
        async def wrapper(*args, **kwargs):
            nonlocal last_call
            current = asyncio.get_event_loop().time()

            if current - last_call >= seconds:
                last_call = current
                return await func(*args, **kwargs)

        return wrapper

    return decorator


def debounce(seconds: float):
    """
    Decorator to debounce function calls.
    Waits for calls to stop before executing.

    Example:
        @debounce(0.3)  # Wait 300ms after last call
        async def save_document(doc):
            await stream.broadcast(...)
    """

    def decorator(func):
        task: Optional[asyncio.Task] = None

        @wraps(func)
        async def wrapper(*args, **kwargs):
            nonlocal task

            if task:
                task.cancel()

            async def delayed_call():
                await asyncio.sleep(seconds)
                return await func(*args, **kwargs)

            task = asyncio.create_task(delayed_call())
            return task

        return wrapper

    return decorator


async def retry_with_backoff(
    func, max_retries: int = 3, base_delay: float = 0.1, max_delay: float = 2.0
):
    """
    Retry a function with exponential backoff.

    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries
        max_delay: Maximum delay between retries
    """
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise

            delay = min(base_delay * (2**attempt), max_delay)
            await asyncio.sleep(delay)


class RateLimiter:
    """
    Rate limiter for broadcasts.

    Example:
        limiter = RateLimiter(max_calls=10, per_seconds=1)

        async def broadcast_message(msg):
            if await limiter.acquire():
                await stream.broadcast(msg)
    """

    def __init__(self, max_calls: int, per_seconds: float):
        self.max_calls = max_calls
        self.per_seconds = per_seconds
        self.calls: list = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> bool:
        """Try to acquire a slot. Returns True if allowed."""
        async with self._lock:
            now = asyncio.get_event_loop().time()

            # Remove old calls outside the window
            cutoff = now - self.per_seconds
            self.calls = [c for c in self.calls if c > cutoff]

            if len(self.calls) < self.max_calls:
                self.calls.append(now)
                return True

            return False

    async def wait(self):
        """Wait until a slot is available."""
        while not await self.acquire():
            await asyncio.sleep(0.01)


class ConnectionPool:
    """
    Manage connection pools for different topics.
    """

    def __init__(self, max_connections_per_topic: int = 1000):
        self.max_per_topic = max_connections_per_topic
        self._pools: dict = {}

    def add_connection(self, topic: str, connection_id: str) -> bool:
        """Add a connection to a topic pool."""
        if topic not in self._pools:
            self._pools[topic] = set()

        if len(self._pools[topic]) >= self.max_per_topic:
            return False

        self._pools[topic].add(connection_id)
        return True

    def remove_connection(self, topic: str, connection_id: str):
        """Remove a connection from a topic pool."""
        if topic in self._pools:
            self._pools[topic].discard(connection_id)

    def get_connection_count(self, topic: str) -> int:
        """Get number of connections in a topic."""
        return len(self._pools.get(topic, set()))

    def get_all_topics(self):
        """Get all topic names."""
        return list(self._pools.keys())


# Message builders for common patterns


class MessageBuilder:
    """Helper to build common message patterns."""

    @staticmethod
    def signal_update(**signals) -> tuple:
        """Build a signal update message."""
        return ("signals", signals)

    @staticmethod
    def element_append(
        selector: str, content, use_view_transition: bool = False
    ) -> tuple:
        """Build an element append message."""
        return ("elements", (content, selector, "append", use_view_transition, None))

    @staticmethod
    def element_replace(
        selector: str, content, use_view_transition: bool = False
    ) -> tuple:
        """Build an element replace message."""
        return ("elements", (content, selector, "replace", use_view_transition, None))

    @staticmethod
    def notification(text: str, type_: str = "info") -> tuple:
        """Build a notification message."""
        return (
            "signals",
            {
                "notification": {
                    "text": text,
                    "type": type_,
                    "timestamp": time.time(),
                }
            },
        )

    @staticmethod
    def toast(message: str, duration: int = 3000) -> tuple:
        """Build a toast message."""
        return ("signals", {"toast": {"message": message, "duration": duration}})


# Utility functions


def generate_topic(*parts: str) -> str:
    """Generate a topic string from parts."""
    return ":".join(str(p) for p in parts if p)


def parse_topic(topic: str) -> list:
    """Parse a topic string into parts."""
    return topic.split(":")


def is_room_topic(topic: str) -> bool:
    """Check if topic is a room topic."""
    return topic.startswith("room:")


def is_user_topic(topic: str) -> bool:
    """Check if topic is a user topic."""
    return topic.startswith("user:")


def extract_room_id(topic: str) -> Optional[str]:
    """Extract room ID from room topic."""
    if topic.startswith("room:"):
        return topic[5:]
    return None


def extract_user_id(topic: str) -> Optional[str]:
    """Extract user ID from user topic."""
    if topic.startswith("user:"):
        return topic[5:]
    return None
