"""PocketBase Plugin for StarStream"""

from typing import Optional, Dict, Any
from starstream import StarStreamPlugin
from .storage import PocketBaseStorage
from .sync import PocketBaseSync


class PocketBasePlugin:
    """
    PocketBase plugin for StarStream.

    Provides seamless integration between PocketBase database and StarStream
    real-time broadcasting. Data changes in PocketBase are automatically
    broadcast to connected clients via SSE.

    Example:
        from starhtml import *
        from starstream import StarStreamPlugin
        from starstream_pocketbase import PocketBasePlugin

        app, rt = star_app()
        stream = StarStreamPlugin(app)

        # Initialize PocketBase plugin
        pb = PocketBasePlugin(
            stream,
            base_url="http://localhost:9090",
            admin_email="admin@example.com",
            admin_password="secret"
        )

        @rt("/todos", methods=["POST"])
        async def create_todo(title: str):
            # Creates in PocketBase + broadcasts to all clients!
            todo = await pb.create("todos", {"title": title, "completed": False})
            return todo

        @rt("/todos/{todo_id}", methods=["PATCH"])
        async def update_todo(todo_id: str, completed: bool):
            # Updates PocketBase + broadcasts!
            return await pb.update("todos", todo_id, {"completed": completed})
    """

    def __init__(
        self,
        stream_plugin: StarStreamPlugin,
        base_url: str = "http://127.0.0.1:9090",
        admin_email: Optional[str] = None,
        admin_password: Optional[str] = None,
    ):
        """
        Initialize PocketBase plugin.

        Args:
            stream_plugin: StarStreamPlugin instance for broadcasting
            base_url: PocketBase server URL
            admin_email: Admin email for authentication
            admin_password: Admin password for authentication
        """
        self._stream = stream_plugin
        self._storage = PocketBaseStorage(base_url)
        self._sync: Optional[PocketBaseSync] = None
        self._admin_email = admin_email
        self._admin_password = admin_password
        self._authenticated = False

    async def authenticate(
        self, email: Optional[str] = None, password: Optional[str] = None
    ) -> bool:
        """
        Authenticate with PocketBase.

        Uses credentials from initialization if not provided.

        Args:
            email: Admin email (optional)
            password: Admin password (optional)

        Returns:
            True if authentication successful
        """
        email = email or self._admin_email
        password = password or self._admin_password

        if not email or not password:
            print("No credentials provided for PocketBase authentication")
            return False

        self._authenticated = await self._storage.authenticate(email, password)

        if self._authenticated:
            # Initialize sync after authentication
            self._sync = PocketBaseSync(self._storage.get_client(), self._stream)

        return self._authenticated

    async def create(
        self, collection: str, data: Dict[str, Any], broadcast: bool = True
    ) -> Optional[Dict]:
        """
        Create a record in PocketBase and broadcast.

        Args:
            collection: Collection name
            data: Record data
            broadcast: Whether to broadcast the change

        Returns:
            Created record or None
        """
        if not self._authenticated:
            print("Not authenticated with PocketBase")
            return None

        return await self._sync.create(collection, data, broadcast)

    async def update(
        self,
        collection: str,
        record_id: str,
        data: Dict[str, Any],
        broadcast: bool = True,
    ) -> Optional[Dict]:
        """
        Update a record in PocketBase and broadcast.

        Args:
            collection: Collection name
            record_id: Record ID
            data: Updated data
            broadcast: Whether to broadcast the change

        Returns:
            Updated record or None
        """
        if not self._authenticated:
            print("Not authenticated with PocketBase")
            return None

        return await self._sync.update(collection, record_id, data, broadcast)

    async def delete(
        self, collection: str, record_id: str, broadcast: bool = True
    ) -> bool:
        """
        Delete a record from PocketBase and broadcast.

        Args:
            collection: Collection name
            record_id: Record ID
            broadcast: Whether to broadcast the change

        Returns:
            True if deleted
        """
        if not self._authenticated:
            print("Not authenticated with PocketBase")
            return False

        return await self._sync.delete(collection, record_id, broadcast)

    async def get_all(
        self, collection: str, query_params: Optional[Dict] = None
    ) -> list:
        """
        Get all records from a collection.

        Args:
            collection: Collection name
            query_params: Optional query parameters

        Returns:
            List of records
        """
        return await self._storage.get_all(collection, query_params)

    async def get_one(self, collection: str, record_id: str) -> Optional[Dict]:
        """
        Get a single record by ID.

        Args:
            collection: Collection name
            record_id: Record ID

        Returns:
            Record or None
        """
        return await self._storage.get(collection, record_id)

    async def query(self, collection: str, filter_str: str, sort: str = "") -> list:
        """
        Query records with filter.

        Args:
            collection: Collection name
            filter_str: PocketBase filter string
            sort: Sort string

        Returns:
            List of matching records
        """
        return await self._storage.query(collection, filter_str, sort)

    async def subscribe(self, collection: str, callback) -> bool:
        """
        Subscribe to collection changes.

        Args:
            collection: Collection name
            callback: Function(action, record) called on changes

        Returns:
            True if subscription successful
        """
        if not self._sync:
            print("Not authenticated with PocketBase")
            return False

        return await self._sync.subscribe(collection, callback)

    def is_authenticated(self) -> bool:
        """Check if authenticated"""
        return self._authenticated

    def get_storage(self) -> PocketBaseStorage:
        """Get storage instance"""
        return self._storage

    def get_stats(self) -> Dict[str, Any]:
        """Get plugin statistics"""
        return {
            "authenticated": self._authenticated,
            "sync_stats": self._sync.get_stats() if self._sync else None,
        }
