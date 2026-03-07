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

With features:
    stream = StarStreamPlugin(
        app,
        enable_presence=True,
        enable_typing=True,
        enable_cursors=True,
        enable_history=True
    )
"""

from .plugin import StarStreamPlugin
from .conventions import AutoTopic, AutoRoom, AutoUser
from .tracker import TopicTracker, TopicEntry
from .presence import Presence
from .typing import TypingIndicator
from .cursor import CursorTracker
from .history import MessageHistory
from .storage.base import StorageBackend
from .storage.sqlite import SQLiteBackend
from .helpers import throttle, debounce, RateLimiter, MessageBuilder

__version__ = "0.1.1"
__all__ = [
    "StarStreamPlugin",
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
