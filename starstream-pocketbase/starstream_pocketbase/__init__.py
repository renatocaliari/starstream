"""
StarStream-PocketBase - PocketBase integration for StarStream

PocketBase provides real-time database with:
- REST API
- Real-time subscriptions (SSE)
- File storage
- Authentication

This plugin integrates PocketBase as a storage backend for StarStream,
enabling persistent real-time data with automatic synchronization.

Example:
    from starhtml import *
    from starstream import StarStreamPlugin
    from starstream_pocketbase import PocketBasePlugin

    app, rt = star_app()
    stream = StarStreamPlugin(app)
    pb = PocketBasePlugin(stream, "http://localhost:9090")

    @rt("/todos")
    async def get_todos():
        # Auto-sync with PocketBase!
        return await pb.get_all("todos")
"""

from .storage import PocketBaseStorage
from .plugin import PocketBasePlugin
from .sync import PocketBaseSync

__version__ = "0.1.0"
__all__ = ["PocketBaseStorage", "PocketBasePlugin", "PocketBaseSync"]
