"""
StarStream - Convention over Configuration for StarHTML Real-time Broadcasting

Zero config by default, customization when needed.

Example:
    from starhtml import *
    from starstream import StarStreamPlugin

    app, rt = star_app()
    stream = StarStreamPlugin(app)  # Zero config!

    @rt("/chat")
    @sse
    async def chat(msg: str):
        yield elements(Div(msg), "#chat", "append")
        # Automatic broadcast to all clients!

With persistence:
    stream = StarStreamPlugin(app, persist=True)

With collaborative editing:
    stream = StarStreamPlugin(app, collaborative=True)

    # Convention: sync() auto-broadcasts to other peers
    await stream.collaborative.sync("doc-1", delta, "user-123")

    # Manual control: apply_delta() without broadcast
    await stream.collaborative.apply_delta("doc-1", delta, "user-123")
"""

from .plugin import StarStreamPlugin
from .core import StarStreamCore
from .metrics import BroadcastMetrics
from .conventions import AutoTopic, AutoRoom, AutoUser
from .tracker import TopicTracker, TopicEntry
from .presence import Presence
from .typing import TypingIndicator
from .cursor import CursorTracker
from .history import MessageHistory
from .storage.base import StorageBackend
from .storage.sqlite import SQLiteBackend
from .helpers import throttle, debounce, RateLimiter, MessageBuilder

__version__ = "0.5.0"
__all__ = [
    "StarStreamPlugin",
    "StarStreamCore",
    "BroadcastMetrics",
    "TopicTracker",
    "TopicEntry",
    "AutoTopic",
    "AutoRoom",
    "AutoUser",
    "Presence",
    "TypingIndicator",
    "CursorTracker",
    "MessageHistory",
    "StorageBackend",
    "SQLiteBackend",
    "throttle",
    "debounce",
    "RateLimiter",
    "MessageBuilder",
]
