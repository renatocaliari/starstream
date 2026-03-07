"""
Presence System - Track online users in topics/rooms.

Provides real-time presence tracking with automatic expiration.
"""

import asyncio
import inspect
import time
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field


@dataclass
class PresenceEntry:
    """Represents a user's presence in a topic."""

    user_id: str
    topic: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    joined_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)


class Presence:
    """
    Track online users across topics with automatic expiration.

    Example:
        presence = Presence(expire_after=30)

        # User joins
        await presence.join("room:123", "user_1", {"name": "João"})

        # Get online users
        online = await presence.get_online("room:123")
        # → {"user_1": {"name": "João", "joined_at": 1234567890}}

        # Heartbeat to keep alive
        await presence.heartbeat("room:123", "user_1")
    """

    def __init__(
        self,
        expire_after: int = 30,
        check_interval: int = 5,
        on_join: Optional[Callable] = None,
        on_leave: Optional[Callable] = None,
    ):
        """
        Initialize presence tracker.

        Args:
            expire_after: Seconds before inactive users are removed
            check_interval: Seconds between expiration checks
            on_join: Callback when user joins (topic, user_id, metadata)
            on_leave: Callback when user leaves (topic, user_id)
        """
        self.expire_after = expire_after
        self.check_interval = check_interval
        self.on_join = on_join
        self.on_leave = on_leave

        # Storage: {topic: {user_id: PresenceEntry}}
        self._presence: Dict[str, Dict[str, PresenceEntry]] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the background cleanup task."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self):
        """Stop the background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

    async def join(
        self, topic: str, user_id: str, metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Register a user as online in a topic.

        Args:
            topic: Topic/room identifier
            user_id: User identifier
            metadata: Optional user metadata (name, avatar, etc.)

        Returns:
            True if user was newly added, False if already present
        """
        async with self._lock:
            if topic not in self._presence:
                self._presence[topic] = {}

            is_new = user_id not in self._presence[topic]

            self._presence[topic][user_id] = PresenceEntry(
                user_id=user_id,
                topic=topic,
                metadata=metadata or {},
                joined_at=time.time() if is_new else self._presence[topic][user_id].joined_at,
                last_seen=time.time(),
            )

        if is_new and self.on_join:
            asyncio.create_task(self._call_callback(self.on_join, topic, user_id, metadata or {}))

        return is_new

    async def leave(self, topic: str, user_id: str) -> bool:
        """
        Remove a user from a topic.

        Args:
            topic: Topic/room identifier
            user_id: User identifier

        Returns:
            True if user was removed, False if not found
        """
        async with self._lock:
            if topic not in self._presence:
                return False

            if user_id not in self._presence[topic]:
                return False

            del self._presence[topic][user_id]

            # Cleanup empty topics
            if not self._presence[topic]:
                del self._presence[topic]

        if self.on_leave:
            asyncio.create_task(self._call_callback(self.on_leave, topic, user_id))

        return True

    async def heartbeat(self, topic: str, user_id: str) -> bool:
        """
        Update last_seen timestamp to keep user online.

        Args:
            topic: Topic/room identifier
            user_id: User identifier

        Returns:
            True if heartbeat successful, False if user not found
        """
        async with self._lock:
            if topic not in self._presence:
                return False

            if user_id not in self._presence[topic]:
                return False

            self._presence[topic][user_id].last_seen = time.time()
            return True

    async def get_online(self, topic: str) -> Dict[str, Dict[str, Any]]:
        """
        Get all online users in a topic.

        Args:
            topic: Topic/room identifier

        Returns:
            Dict mapping user_id to metadata + joined_at
        """
        async with self._lock:
            if topic not in self._presence:
                return {}

            return {
                user_id: {
                    **entry.metadata,
                    "joined_at": entry.joined_at,
                    "last_seen": entry.last_seen,
                }
                for user_id, entry in self._presence[topic].items()
            }

    async def is_online(self, topic: str, user_id: str) -> bool:
        """Check if a user is online in a topic."""
        async with self._lock:
            return topic in self._presence and user_id in self._presence[topic]

    async def get_user_count(self, topic: str) -> int:
        """Get number of online users in a topic."""
        async with self._lock:
            return len(self._presence.get(topic, {}))

    async def get_all_topics(self) -> List[str]:
        """Get list of all topics with users."""
        async with self._lock:
            return list(self._presence.keys())

    async def _cleanup_loop(self):
        """Background task to remove expired users."""
        while True:
            try:
                await asyncio.sleep(self.check_interval)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Presence cleanup error: {e}")

    async def _cleanup_expired(self):
        """Remove users that haven't sent heartbeat."""
        now = time.time()
        expired: List[tuple] = []

        async with self._lock:
            for topic, users in list(self._presence.items()):
                for user_id, entry in list(users.items()):
                    if now - entry.last_seen > self.expire_after:
                        expired.append((topic, user_id))
                        del users[user_id]

                # Cleanup empty topics
                if not users:
                    del self._presence[topic]

        # Call callbacks outside lock
        for topic, user_id in expired:
            if self.on_leave:
                asyncio.create_task(self._call_callback(self.on_leave, topic, user_id))

    async def _call_callback(self, callback: Callable, *args):
        """Safely call a callback, catching exceptions."""
        try:
            if inspect.iscoroutinefunction(callback):
                await callback(*args)
            else:
                callback(*args)
        except Exception as e:
            print(f"Presence callback error: {e}")
