"""
Typing Indicators - Show who's typing in real-time.

Provides automatic typing indicators with auto-stop functionality.
"""

import asyncio
import inspect
import time
from typing import Dict, Set, Optional, Callable


class TypingIndicator:
    """
    Track who's typing in topics with automatic timeout.

    Example:
        typing = TypingIndicator(auto_stop_after=3)

        # User starts typing
        await typing.start("room:123", "user_1")

        # Get typing users
        typing_users = await typing.get_typing("room:123")
        # → {"user_1"}

        # User stops typing (or auto-stops after timeout)
        await typing.stop("room:123", "user_1")
    """

    def __init__(
        self,
        auto_stop_after: int = 3,
        broadcast_to_topic: bool = True,
        on_start: Optional[Callable] = None,
        on_stop: Optional[Callable] = None,
    ):
        """
        Initialize typing indicator.

        Args:
            auto_stop_after: Seconds before auto-stopping typing
            broadcast_to_topic: Whether to broadcast typing changes
            on_start: Callback when user starts typing (topic, user_id)
            on_stop: Callback when user stops typing (topic, user_id)
        """
        self.auto_stop_after = auto_stop_after
        self.broadcast_to_topic = broadcast_to_topic
        self.on_start = on_start
        self.on_stop = on_stop

        # Storage: {topic: {user_id: timestamp}}
        self._typing: Dict[str, Dict[str, float]] = {}
        self._auto_stop_tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def start(self, topic: str, user_id: str) -> bool:
        """
        Mark user as typing in a topic.

        Args:
            topic: Topic/room identifier
            user_id: User identifier

        Returns:
            True if user was newly added, False if already typing
        """
        async with self._lock:
            if topic not in self._typing:
                self._typing[topic] = {}

            is_new = user_id not in self._typing[topic]
            self._typing[topic][user_id] = time.time()

        if is_new:
            # Schedule auto-stop
            task_key = f"{topic}:{user_id}"
            if task_key in self._auto_stop_tasks:
                self._auto_stop_tasks[task_key].cancel()

            self._auto_stop_tasks[task_key] = asyncio.create_task(self._auto_stop(topic, user_id))

            # Call callback
            if self.on_start:
                asyncio.create_task(self._call_callback(self.on_start, topic, user_id))

        return is_new

    async def stop(self, topic: str, user_id: str) -> bool:
        """
        Mark user as stopped typing.

        Args:
            topic: Topic/room identifier
            user_id: User identifier

        Returns:
            True if user was removed, False if not found
        """
        async with self._lock:
            if topic not in self._typing:
                return False

            if user_id not in self._typing[topic]:
                return False

            del self._typing[topic][user_id]

            # Cleanup empty topics
            if not self._typing[topic]:
                del self._typing[topic]

        # Cancel auto-stop task
        task_key = f"{topic}:{user_id}"
        if task_key in self._auto_stop_tasks:
            self._auto_stop_tasks[task_key].cancel()
            del self._auto_stop_tasks[task_key]

        # Call callback
        if self.on_stop:
            asyncio.create_task(self._call_callback(self.on_stop, topic, user_id))

        return True

    async def get_typing(self, topic: str) -> Set[str]:
        """
        Get all users currently typing in a topic.

        Args:
            topic: Topic/room identifier

        Returns:
            Set of user_ids currently typing
        """
        async with self._lock:
            if topic not in self._typing:
                return set()

            return set(self._typing[topic].keys())

    async def is_typing(self, topic: str, user_id: str) -> bool:
        """Check if a user is typing in a topic."""
        async with self._lock:
            return topic in self._typing and user_id in self._typing[topic]

    async def get_typing_count(self, topic: str) -> int:
        """Get number of users typing in a topic."""
        async with self._lock:
            return len(self._typing.get(topic, {}))

    async def stop_all(self, topic: str):
        """Stop all typing users in a topic (e.g., when message sent)."""
        async with self._lock:
            if topic not in self._typing:
                return

            users = list(self._typing[topic].keys())
            del self._typing[topic]

        # Cancel all auto-stop tasks and call callbacks
        for user_id in users:
            task_key = f"{topic}:{user_id}"
            if task_key in self._auto_stop_tasks:
                self._auto_stop_tasks[task_key].cancel()
                del self._auto_stop_tasks[task_key]

            if self.on_stop:
                asyncio.create_task(self._call_callback(self.on_stop, topic, user_id))

    async def _auto_stop(self, topic: str, user_id: str):
        """Background task to auto-stop typing after timeout."""
        try:
            await asyncio.sleep(self.auto_stop_after)
            await self.stop(topic, user_id)
        except asyncio.CancelledError:
            pass

    async def _call_callback(self, callback: Callable, *args):
        """Safely call a callback, catching exceptions."""
        try:
            if inspect.iscoroutinefunction(callback):
                await callback(*args)
            else:
                callback(*args)
        except Exception as e:
            print(f"Typing indicator callback error: {e}")
