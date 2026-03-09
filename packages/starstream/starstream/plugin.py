"""
StarStream Plugin - Core implementation

Provides automatic real-time broadcasting for StarHTML applications
with zero configuration by default.
"""

import asyncio
import json
import logging
import re
import time
from collections import defaultdict
from functools import wraps
from typing import Any, Dict, Optional, Set, Callable, Union, Tuple, List, TYPE_CHECKING
from starlette.responses import StreamingResponse

from .core import StarStreamCore
from .metrics import BroadcastMetrics

if TYPE_CHECKING:
    from starhtml import Div


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
        persist: bool = False,
        collaborative: bool = False,
        db_path: str = None,
        storage=None,
    ):
        """
        Initialize StarStream plugin.

        Convention over Configuration:
        - persist=True automatically creates SQLite storage
        - collaborative=True enables CRDT-based collaborative editing
        - Use db_path to customize SQLite database location
        - Use storage to override with custom backend

        Args:
            app: StarHTML app instance
            default_topic: Default topic for broadcasts
            enable_presence: Track online users
            enable_typing: Show typing indicators
            enable_cursors: Track mouse positions
            enable_history: (Deprecated) Use persist instead
            persist: Enable persistence (auto-creates SQLite)
            collaborative: Enable collaborative editing (requires loro)
            db_path: Custom SQLite database path (optional, default: starstream.db)
            storage: Custom storage backend (optional, overrides auto-creation)
        """
        self.app = app
        self.core = StarStreamCore()
        self.default_topic = default_topic
        self._interceptors: Dict[str, Callable] = {}
        self._configurations: Dict[str, Dict] = {}

        # Handle backward compatibility: enable_history -> persist
        should_persist = persist or enable_history

        # Auto-create SQLite storage if persist enabled and no custom storage provided
        if storage:
            self.storage = storage
        elif should_persist:
            from .storage.sqlite import SQLiteBackend

            auto_db_path = db_path or "starstream.db"
            self.storage = SQLiteBackend(auto_db_path)
        else:
            self.storage = None

        # Metrics and error handling
        self._metrics = defaultdict(BroadcastMetrics)
        self.on_broadcast_error = None

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

        if should_persist:
            from .history import MessageHistory

            self.history = MessageHistory()

        # Collaborative editing support (lazy loaded)
        self._collaborative_enabled = collaborative
        self._collaborative = None

        # Register stream endpoint
        self._register_stream_endpoint()

    @property
    def collaborative(self):
        """
        Access collaborative editing engine.

        Raises:
            RuntimeError: If collaborative editing not enabled
            ImportError: If loro not installed
        """
        if not self._collaborative_enabled:
            raise RuntimeError(
                "Collaborative editing not enabled. "
                "Initialize with: StarStreamPlugin(app, collaborative=True)"
            )

        if self._collaborative is None:
            self._init_collaborative()

        return self._collaborative

    def _init_collaborative(self):
        """Initialize collaborative editing engine (lazy load)."""
        # Import here to avoid circular dependency
        from .collaborative import CollaborativeEngine

        # Note: Loro is checked when actually using CRDT features
        # This allows the engine to be created even if Loro is not installed
        self._collaborative = CollaborativeEngine(storage=self.storage)

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

    # Unified broadcast API - fire-and-forget by design

    def broadcast(
        self,
        message: Union[str, Tuple],
        target: Union[str, Dict, None] = None,
    ):
        """
        Fire-and-forget broadcast to subscribers.

        Broadcasts are inherently fire-and-forget (pub/sub semantics).
        Use metrics or logs for observability.

        Args:
            message: str, tuple, or StarHTML elements
            target: str, dict, or None

        Example:
            @rt("/todos/add", methods=["POST"])
            @sse
            def add_todo(text: str):
                stream.broadcast(elements(...), target="todos")
                yield elements(...)
        """
        topic = self._resolve_target(target)

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._do_broadcast_safe(message, topic))
        except RuntimeError:
            asyncio.run(self._do_broadcast_safe(message, topic))

    def get_stream_url(self, topic: str = "global") -> str:
        """Get the SSE stream URL for a topic."""
        return f"/starstream?topic={topic}"

    def get_stream_element(self, topic: Union[str, list] = "global") -> Union["Div", list["Div"]]:
        """Get Datastar stream element(s) for topic(s).

        Args:
            topic: Single topic (str) or list of topics (list[str])

        Returns:
            Single Div element if topic is str, list of Div elements if topic is list

        Examples:
            >>> stream.get_stream_element("chat:123")  # Single topic
            <div data-init="@get('/starstream?topic=chat:123', {openWhenHidden: true})"></div>

            >>> stream.get_stream_element(["chat:123", "notifications"])  # Multiple topics
            [<div data-init="@get('/starstream?topic=chat:123', {openWhenHidden: true})"></div>,
             <div data-init="@get('/starstream?topic=notifications', {openWhenHidden: true})"></div>]
        """
        from starhtml import Div

        if isinstance(topic, list):
            return [
                Div(data_init=f"@get('{self.get_stream_url(t)}', {{openWhenHidden: true}})")
                for t in topic
            ]
        else:
            return Div(data_init=f"@get('{self.get_stream_url(topic)}', {{openWhenHidden: true}})")

    async def _do_broadcast_safe(
        self,
        message: Union[str, Tuple],
        topic: str,
    ):
        """
        Internal: Broadcast with error handling and metrics.
        """
        logger = logging.getLogger("starstream")
        start = time.time()

        try:
            await self.core.broadcast(message, topic)

            latency = time.time() - start
            self._metrics[topic].record_success(latency)

            logger.debug(
                f"Broadcast succeeded",
                extra={"topic": topic, "latency_ms": round(latency * 1000, 2)},
            )

        except Exception as e:
            self._metrics[topic].record_error()

            logger.error(
                f"Broadcast failed", extra={"topic": topic, "error": str(e)}, exc_info=True
            )

            if self.on_broadcast_error:
                try:
                    self.on_broadcast_error(topic, message, e)
                except Exception as hook_error:
                    logger.error(f"Broadcast error hook failed", extra={"error": str(hook_error)})

    def _resolve_target(self, target: Union[str, Dict, None]) -> str:
        """Resolve target to topic string."""
        if target is None:
            return self.default_topic
        elif isinstance(target, str):
            return target
        elif isinstance(target, dict):
            t_type = target.get("type", "topic")
            t_id = target.get("id", "global")
            return f"{t_type}:{t_id}" if t_type != "topic" else t_id
        else:
            return self.default_topic

    def get_metrics(self, topic: str = None):
        """Get broadcast metrics."""
        if topic:
            return self._metrics.get(topic, BroadcastMetrics()).get_stats()
        return {t: m.get_stats() for t, m in self._metrics.items()}

    def set_error_hook(self, hook):
        """Set custom error handler for broadcast failures."""
        self.on_broadcast_error = hook


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
        await self.plugin.send_to_user(user_id, ("signals", {"notification": notification}))
