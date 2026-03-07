"""
Base Topic Tracker - Unified tracking system for topics.

Provides common functionality for tracking users across topics
with automatic expiration and callbacks.
"""

import asyncio
import inspect
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, Set
from dataclasses import dataclass, field


@dataclass
class TopicEntry:
    """Base entry for topic tracking."""

    user_id: str
    topic: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)


class TopicTracker(ABC):
    """
    Base class for tracking users across topics.

    Follows Convention over Configuration:
    - Auto-cleanup with configurable intervals
    - Optional callbacks for state changes
    - Thread-safe with asyncio locks

    Example:
        class Presence(TopicTracker):
            def _create_entry(self, user_id, topic, metadata):
                return TopicEntry(user_id, topic, metadata)
    """

    def __init__(
        self,
        expire_after: int = 30,
        check_interval: int = 5,
        on_enter: Optional[Callable] = None,
        on_exit: Optional[Callable] = None,
    ):
        """
        Initialize topic tracker.

        Args:
            expire_after: Seconds before auto-removing entries
            check_interval: Seconds between cleanup checks
            on_enter: Callback when user enters (topic, user_id, metadata)
            on_exit: Callback when user exits (topic, user_id)
        """
        self.expire_after = expire_after
        self.check_interval = check_interval
        self.on_enter = on_enter
        self.on_exit = on_exit

        # Storage: {topic: {user_id: TopicEntry}}
        self._entries: Dict[str, Dict[str, TopicEntry]] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """Start background cleanup."""
        if not self._running:
            self._running = True
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self):
        """Stop background cleanup."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    async def enter(self, topic: str, user_id: str, metadata: Optional[Dict] = None) -> bool:
        """
        Add user to topic.

        Returns:
            True if newly added, False if already present
        """
        async with self._lock:
            if topic not in self._entries:
                self._entries[topic] = {}

            is_new = user_id not in self._entries[topic]

            if is_new:
                self._entries[topic][user_id] = self._create_entry(user_id, topic, metadata or {})
            else:
                # Update last_seen
                self._entries[topic][user_id].last_seen = time.time()

        if is_new and self.on_enter:
            await self._call_callback(self.on_enter, topic, user_id, metadata)

        return is_new

    async def exit(self, topic: str, user_id: str) -> bool:
        """
        Remove user from topic.

        Returns:
            True if removed, False if not found
        """
        async with self._lock:
            removed = self._remove_entry(topic, user_id)

        if removed and self.on_exit:
            await self._call_callback(self.on_exit, topic, user_id)

        return removed

    async def get_all(self, topic: str) -> Dict[str, Dict[str, Any]]:
        """Get all entries in topic."""
        async with self._lock:
            entries = self._entries.get(topic, {})
            return {
                user_id: {
                    **entry.metadata,
                    "created_at": entry.created_at,
                    "last_seen": entry.last_seen,
                }
                for user_id, entry in entries.items()
            }

    async def has(self, topic: str, user_id: str) -> bool:
        """Check if user is in topic."""
        async with self._lock:
            return user_id in self._entries.get(topic, {})

    async def count(self, topic: str) -> int:
        """Count entries in topic."""
        async with self._lock:
            return len(self._entries.get(topic, {}))

    async def touch(self, topic: str, user_id: str) -> bool:
        """Update last_seen timestamp."""
        async with self._lock:
            if topic in self._entries and user_id in self._entries[topic]:
                self._entries[topic][user_id].last_seen = time.time()
                return True
            return False

    @abstractmethod
    def _create_entry(self, user_id: str, topic: str, metadata: Dict) -> TopicEntry:
        """Create appropriate entry type. Override in subclasses."""
        return TopicEntry(user_id, topic, metadata)

    def _remove_entry(self, topic: str, user_id: str) -> bool:
        """Remove entry without lock (internal use)."""
        if topic in self._entries and user_id in self._entries[topic]:
            del self._entries[topic][user_id]
            if not self._entries[topic]:
                del self._entries[topic]
            return True
        return False

    async def _cleanup_loop(self):
        """Background cleanup task."""
        while self._running:
            try:
                await asyncio.sleep(self.check_interval)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception:
                pass  # Continue cleanup loop

    async def _cleanup_expired(self):
        """Remove expired entries."""
        now = time.time()
        expired: list[tuple[str, str]] = []

        async with self._lock:
            for topic, entries in list(self._entries.items()):
                for user_id, entry in list(entries.items()):
                    if now - entry.last_seen > self.expire_after:
                        expired.append((topic, user_id))
                        self._remove_entry(topic, user_id)

        # Call callbacks outside lock
        for topic, user_id in expired:
            if self.on_exit:
                await self._call_callback(self.on_exit, topic, user_id)

    async def _call_callback(self, callback: Callable, *args):
        """Safely call callback."""
        try:
            if inspect.iscoroutinefunction(callback):
                await callback(*args)
            else:
                callback(*args)
        except Exception:
            pass  # Don't let callbacks break tracking
