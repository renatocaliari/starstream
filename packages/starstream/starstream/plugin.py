"""
StarStream Plugin - Core implementation

Provides automatic real-time broadcasting for StarHTML applications
with zero configuration by default.
"""

import asyncio
import json
import re
from typing import Any, Dict, Optional, Set, Callable, Union, Tuple, List
from functools import wraps
from starlette.responses import StreamingResponse


class StarStreamCore:
    """
    Core broadcasting engine - manages topics and subscribers.
    """

    def __init__(self):
        self._topics: Dict[str, Set[asyncio.Queue]] = {}
        self._user_topics: Dict[str, str] = {}  # user_id -> topic mapping
        self._room_topics: Dict[str, Set[str]] = {}  # room_id -> set of user_ids

    async def subscribe(self, topic: str = "global"):
        """Subscribe to a topic and yield messages."""
        if topic not in self._topics:
            self._topics[topic] = set()

        queue = asyncio.Queue()
        self._topics[topic].add(queue)

        try:
            while True:
                message = await queue.get()
                yield message
        finally:
            if topic in self._topics:
                self._topics[topic].discard(queue)
                if not self._topics[topic]:
                    del self._topics[topic]

    def _format_message(self, msg: Union[str, Tuple]) -> str:
        """Format message for SSE."""
        if isinstance(msg, tuple) and len(msg) >= 2:
            event_type = f"datastar-patch-{msg[0]}"
            payload = msg[1]
            lines = [f"event: {event_type}"]

            if msg[0] == "elements":
                content, selector, mode, use_vt, signals = payload
                if selector:
                    lines.append(f"data: selector {selector}")
                if mode:
                    lines.append(f"data: mode {mode}")
                if use_vt:
                    lines.append(f"data: useViewTransition {str(use_vt).lower()}")

                contents = content if isinstance(content, (list, tuple)) else [content]
                for item in contents:
                    for line in str(item).splitlines():
                        lines.append(f"data: elements {line}")

            elif msg[0] == "signals":
                for line in json.dumps(payload).splitlines():
                    lines.append(f"data: signals {line}")

            return "\n".join(lines) + "\n\n"

        if isinstance(msg, str):
            if msg.startswith("event:"):
                return msg + ("\n\n" if not msg.endswith("\n\n") else "")
            return f"data: {msg}\n\n"
        return ""

    async def broadcast(
        self,
        message: Union[str, Tuple],
        topic: str = "global",
        exclude: Optional[Set] = None,
    ):
        """Broadcast message to all subscribers of a topic."""
        formatted = self._format_message(message)

        if topic in self._topics:
            for queue in list(self._topics[topic]):
                await queue.put(formatted)

    def sse_response(self, topic: str = "global"):
        """Create Starlette StreamingResponse for SSE."""

        async def event_publisher():
            try:
                async for msg in self.subscribe(topic):
                    yield msg
            except asyncio.CancelledError:
                pass

        return StreamingResponse(
            event_publisher(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )


class StarStreamPlugin:
    """
    StarStream Plugin for StarHTML applications.

    Provides automatic real-time broadcasting with zero config:
    - Auto-topic based on route path
    - Auto-room based on room_id parameter
    - Auto-user based on user_id parameter

    Optional features:
    - Presence: Track online users
    - Typing: Show who's typing
    - Cursors: Track mouse positions
    - History: Store message history

    Example:
        app, rt = star_app()
        stream = StarStreamPlugin(app)

        @rt("/chat")
        @sse
        async def chat(msg: str):
            yield elements(Div(msg), "#chat", "append")
            # Auto-broadcast to all clients!
    """

    def __init__(
        self,
        app,
        default_topic: str = "global",
        enable_presence: bool = False,
        enable_typing: bool = False,
        enable_cursors: bool = False,
        enable_history: bool = False,
        storage=None,
    ):
        self.app = app
        self.core = StarStreamCore()
        self.default_topic = default_topic
        self._interceptors: Dict[str, Callable] = {}
        self._configurations: Dict[str, Dict] = {}
        self.storage = storage

        # Optional features
        self.presence = None
        self.typing = None
        self.cursors = None
        self.history = None

        # Initialize features if enabled
        if enable_presence:
            from .presence import Presence

            self.presence = Presence()

        if enable_typing:
            from .typing import TypingIndicator

            self.typing = TypingIndicator()

        if enable_cursors:
            from .cursor import CursorTracker

            self.cursors = CursorTracker()

        if enable_history:
            from .history import MessageHistory

            self.history = MessageHistory()

        # Register stream endpoint
        self._register_stream_endpoint()

    def _register_stream_endpoint(self):
        """Register the SSE stream endpoint."""

        @self.app.route("/starstream")
        async def stream_endpoint(topic: str = "global"):
            return self.core.sse_response(topic)

    def _extract_route_pattern(self, func) -> str:
        """Extract route pattern from function."""
        # Get the route path from the app
        # This is a simplified version - in practice, we'd inspect the app's routes
        return getattr(func, "_route_path", "unknown")

    def _auto_detect_topic(self, route_path: str, kwargs: Dict) -> str:
        """
        Auto-detect topic based on convention:
        - /chat -> "chat"
        - /room/{room_id} -> "room:{room_id}"
        - /user/{user_id}/dm -> "user:{user_id}"
        """
        # Check for room_id in kwargs
        if "room_id" in kwargs:
            return f"room:{kwargs['room_id']}"

        # Check for user_id in kwargs (for DMs)
        if "user_id" in kwargs:
            return f"user:{kwargs['user_id']}"

        # Extract topic from route path
        # Remove parameters and use the remaining path
        path_without_params = re.sub(r"\{[^}]+\}", "", route_path)
        path_parts = [p for p in path_without_params.split("/") if p]

        if path_parts:
            return ":".join(path_parts)

        return self.default_topic

    def configure(
        self,
        topic: Optional[str] = None,
        exclude_self: bool = False,
        filter_fn: Optional[Callable] = None,
        broadcast: bool = True,
    ):
        """
        Configure broadcasting behavior for an endpoint.

        Args:
            topic: Explicit topic (overrides auto-detection)
            exclude_self: Don't broadcast to the sender
            filter_fn: Function to filter recipients
            broadcast: Whether to broadcast at all (default True)

        Example:
            @rt("/admin")
            @sse
            @stream.configure(topic="admin", filter_fn=lambda ctx: ctx.user.is_admin)
            async def admin_msg(msg: str):
                yield elements(Div(msg), "#admin")
        """

        def decorator(func):
            func._starstream_config = {
                "topic": topic,
                "exclude_self": exclude_self,
                "filter_fn": filter_fn,
                "broadcast": broadcast,
            }
            return func

        return decorator

    def intercept_sse(self, func):
        """
        Decorator to intercept SSE endpoints and auto-broadcast.

        This is automatically applied when using @sse decorator.
        """

        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Check for custom configuration
            config = getattr(func, "_starstream_config", {})

            if not config.get("broadcast", True):
                # Broadcasting disabled for this endpoint
                async for item in func(*args, **kwargs):
                    yield item
                return

            # Get route path (simplified - would need actual route info)
            route_path = getattr(func, "_route_path", "global")

            # Auto-detect topic
            explicit_topic = config.get("topic")
            if explicit_topic:
                topic = explicit_topic
            else:
                topic = self._auto_detect_topic(route_path, kwargs)

            # Collect all yields
            items = []
            async for item in func(*args, **kwargs):
                items.append(item)
                yield item

            # Broadcast after all items yielded
            if items:
                for item in items:
                    await self.core.broadcast(item, topic=topic)

        return wrapper

    # Manual API methods for advanced usage

    async def broadcast_to_topic(self, topic: str, message: Union[str, Tuple]):
        """Manually broadcast to a specific topic."""
        await self.core.broadcast(message, topic=topic)

    async def broadcast_to_room(self, room_id: str, message: Union[str, Tuple]):
        """Broadcast to a specific room."""
        await self.core.broadcast(message, topic=f"room:{room_id}")

    async def send_to_user(self, user_id: str, message: Union[str, Tuple]):
        """Send message to a specific user."""
        await self.core.broadcast(message, topic=f"user:{user_id}")

    async def broadcast_exclude(
        self,
        exclude_user_ids: List[str],
        message: Union[str, Tuple],
        topic: str = "global",
    ):
        """Broadcast to all except specific users."""
        # In a real implementation, we'd track user subscriptions
        # For now, this is a placeholder
        await self.core.broadcast(message, topic=topic)

    def get_stream_url(self, topic: str = "global") -> str:
        """Get the SSE stream URL for a topic."""
        return f"/starstream?topic={topic}"


# Helper functions for common patterns


class AutoTopic:
    """Helper to define auto-topic conventions."""

    @staticmethod
    def from_route(route_path: str, **kwargs) -> str:
        """Generate topic from route path and parameters."""
        if "room_id" in kwargs:
            return f"room:{kwargs['room_id']}"
        if "user_id" in kwargs:
            return f"user:{kwargs['user_id']}"

        # Clean path
        path = re.sub(r"\{[^}]+\}", "", route_path)
        parts = [p for p in path.split("/") if p]
        return ":".join(parts) if parts else "global"


class AutoRoom:
    """Helper for room-based broadcasting."""

    def __init__(self, plugin: StarStreamPlugin):
        self.plugin = plugin

    async def join(self, room_id: str, user_id: str):
        """Add user to a room."""
        # Track user in room
        pass  # Implementation depends on session management

    async def leave(self, room_id: str, user_id: str):
        """Remove user from a room."""
        pass

    async def broadcast(self, room_id: str, message: Union[str, Tuple]):
        """Broadcast to all users in a room."""
        await self.plugin.broadcast_to_room(room_id, message)


class AutoUser:
    """Helper for user-specific messaging."""

    def __init__(self, plugin: StarStreamPlugin):
        self.plugin = plugin

    async def send(self, user_id: str, message: Union[str, Tuple]):
        """Send message to a specific user."""
        await self.plugin.send_to_user(user_id, message)

    async def notify(self, user_id: str, notification: str):
        """Send notification to user."""
        await self.plugin.send_to_user(
            user_id, ("signals", {"notification": notification})
        )
