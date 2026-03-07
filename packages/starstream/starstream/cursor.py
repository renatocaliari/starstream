"""
Cursor Tracking - Track mouse positions in real-time.

Provides real-time cursor tracking with throttling and auto-removal.
"""

import asyncio
import inspect
import time
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field


@dataclass
class CursorPosition:
    """Represents a cursor position."""

    user_id: str
    x: int
    y: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_seen: float = field(default_factory=time.time)


class CursorTracker:
    """
    Track cursor positions across topics with throttling and auto-removal.

    Example:
        cursors = CursorTracker(throttle_updates=50)  # 50ms throttle

        # Update cursor position
        await cursors.update("canvas", "user_1", 100, 200, {"color": "#ff0000"})

        # Get all cursor positions
        positions = await cursors.get_positions("canvas")
        # → {"user_1": {"x": 100, "y": 200, "color": "#ff0000"}}
    """

    def __init__(
        self,
        throttle_updates: int = 50,  # ms
        auto_remove_after: int = 5,  # seconds
        on_update: Optional[Callable] = None,
        on_remove: Optional[Callable] = None,
    ):
        """
        Initialize cursor tracker.

        Args:
            throttle_updates: Minimum ms between updates from same user
            auto_remove_after: Seconds before removing inactive cursors
            on_update: Callback when cursor updates (topic, user_id, x, y)
            on_remove: Callback when cursor removed (topic, user_id)
        """
        self.throttle_updates = throttle_updates / 1000  # Convert to seconds
        self.auto_remove_after = auto_remove_after
        self.on_update = on_update
        self.on_remove = on_remove

        # Storage: {topic: {user_id: CursorPosition}}
        self._cursors: Dict[str, Dict[str, CursorPosition]] = {}
        self._last_update: Dict[str, float] = {}  # {topic:user_id: timestamp}
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

    async def update(
        self,
        topic: str,
        user_id: str,
        x: int,
        y: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Update cursor position (with throttling).

        Args:
            topic: Topic/canvas identifier
            user_id: User identifier
            x: X coordinate
            y: Y coordinate
            metadata: Optional metadata (color, name, etc.)

        Returns:
            True if updated, False if throttled
        """
        throttle_key = f"{topic}:{user_id}"
        now = time.time()

        # Check throttle
        async with self._lock:
            if throttle_key in self._last_update:
                elapsed = now - self._last_update[throttle_key]
                if elapsed < self.throttle_updates:
                    return False

            # Update position
            if topic not in self._cursors:
                self._cursors[topic] = {}

            self._cursors[topic][user_id] = CursorPosition(
                user_id=user_id,
                x=x,
                y=y,
                metadata=metadata
                or self._cursors[topic].get(user_id, CursorPosition(user_id, 0, 0)).metadata,
                last_seen=now,
            )

            self._last_update[throttle_key] = now

        # Call callback
        if self.on_update:
            asyncio.create_task(self._call_callback(self.on_update, topic, user_id, x, y))

        return True

    async def remove(self, topic: str, user_id: str) -> bool:
        """
        Remove a cursor from a topic.

        Args:
            topic: Topic/canvas identifier
            user_id: User identifier

        Returns:
            True if removed, False if not found
        """
        async with self._lock:
            if topic not in self._cursors:
                return False

            if user_id not in self._cursors[topic]:
                return False

            del self._cursors[topic][user_id]

            # Cleanup empty topics
            if not self._cursors[topic]:
                del self._cursors[topic]

            # Cleanup throttle tracking
            throttle_key = f"{topic}:{user_id}"
            if throttle_key in self._last_update:
                del self._last_update[throttle_key]

        # Call callback
        if self.on_remove:
            asyncio.create_task(self._call_callback(self.on_remove, topic, user_id))

        return True

    async def get_positions(self, topic: str) -> Dict[str, Dict[str, Any]]:
        """
        Get all cursor positions in a topic.

        Args:
            topic: Topic/canvas identifier

        Returns:
            Dict mapping user_id to position data
        """
        async with self._lock:
            if topic not in self._cursors:
                return {}

            return {
                user_id: {"x": cursor.x, "y": cursor.y, **cursor.metadata}
                for user_id, cursor in self._cursors[topic].items()
            }

    async def get_position(self, topic: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific user's cursor position."""
        async with self._lock:
            if topic not in self._cursors:
                return None

            if user_id not in self._cursors[topic]:
                return None

            cursor = self._cursors[topic][user_id]
            return {"x": cursor.x, "y": cursor.y, **cursor.metadata}

    async def get_cursor_count(self, topic: str) -> int:
        """Get number of active cursors in a topic."""
        async with self._lock:
            return len(self._cursors.get(topic, {}))

    async def _cleanup_loop(self):
        """Background task to remove inactive cursors."""
        while True:
            try:
                await asyncio.sleep(self.auto_remove_after)
                await self._cleanup_inactive()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Cursor cleanup error: {e}")

    async def _cleanup_inactive(self):
        """Remove cursors that haven't been updated."""
        now = time.time()
        removed = []

        async with self._lock:
            for topic, users in list(self._cursors.items()):
                for user_id, cursor in list(users.items()):
                    if now - cursor.last_seen > self.auto_remove_after:
                        removed.append((topic, user_id))
                        del users[user_id]

                        # Cleanup throttle tracking
                        throttle_key = f"{topic}:{user_id}"
                        if throttle_key in self._last_update:
                            del self._last_update[throttle_key]

                # Cleanup empty topics
                if not users:
                    del self._cursors[topic]

        # Call callbacks outside lock
        for topic, user_id in removed:
            if self.on_remove:
                asyncio.create_task(self._call_callback(self.on_remove, topic, user_id))

    async def _call_callback(self, callback: Callable, *args):
        """Safely call a callback, catching exceptions."""
        try:
            if inspect.iscoroutinefunction(callback):
                await callback(*args)
            else:
                callback(*args)
        except Exception as e:
            print(f"Cursor tracker callback error: {e}")
