"""
Presence System - Track online users in topics/rooms.

Simple, convention-based presence tracking.
"""

from typing import Dict, Any, Optional, Callable
from .tracker import TopicTracker, TopicEntry


class Presence(TopicTracker):
    """
    Track online users across topics.

    Convention: users automatically expire after inactivity.

    Example:
        presence = Presence(expire_after=30)

        # User joins
        await presence.enter("room:123", "user_1", {"name": "João"})

        # Get online users
        online = await presence.get_all("room:123")
    """

    def __init__(
        self,
        expire_after: int = 30,
        on_join: Optional[Callable] = None,
        on_leave: Optional[Callable] = None,
    ):
        super().__init__(
            expire_after=expire_after,
            on_enter=on_join,
            on_exit=on_leave,
        )

    def _create_entry(self, user_id: str, topic: str, metadata: Dict) -> TopicEntry:
        """Create presence entry."""
        return TopicEntry(user_id, topic, metadata)

    # Convenience methods (wrappers for clarity)
    async def join(self, topic: str, user_id: str, metadata: dict = None):
        """Add user to topic."""
        return await self.enter(topic, user_id, metadata)

    async def leave(self, topic: str, user_id: str):
        """Remove user from topic."""
        return await self.exit(topic, user_id)

    async def get_online(self, topic: str) -> dict:
        """Get all online users with joined_at timestamp."""
        async with self._lock:
            entries = self._entries.get(topic, {})
            return {
                user_id: {
                    **entry.metadata,
                    "joined_at": entry.created_at,
                    "last_seen": entry.last_seen,
                }
                for user_id, entry in entries.items()
            }

    async def is_online(self, topic: str, user_id: str) -> bool:
        """Check if user is online."""
        return await self.has(topic, user_id)

    async def heartbeat(self, topic: str, user_id: str) -> bool:
        """Update user's last_seen timestamp."""
        return await self.touch(topic, user_id)

    async def get_user_count(self, topic: str) -> int:
        """Count online users in topic."""
        return await self.count(topic)

    async def get_all_topics(self):
        """Get all topics with users."""
        async with self._lock:
            return list(self._entries.keys())
