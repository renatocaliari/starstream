"""PocketBase Storage Backend for StarStream"""

from typing import Optional, Dict, Any, List
from pocketbase import PocketBase


class PocketBaseStorage:
    """
    Storage backend using PocketBase database.

    PocketBase provides:
    - REST API for CRUD operations
    - Real-time subscriptions
    - File storage
    - Authentication

    This class wraps PocketBase to provide a storage interface
    compatible with StarStream's storage abstraction.

    Example:
        pb = PocketBaseStorage("http://localhost:9090")
        await pb.authenticate("admin@example.com", "password123")

        # Store data
        await pb.set("todos", {"title": "Buy milk", "completed": False})

        # Retrieve data
        todos = await pb.get_all("todos")
    """

    def __init__(self, base_url: str = "http://127.0.0.1:9090"):
        """
        Initialize PocketBase storage.

        Args:
            base_url: PocketBase server URL
        """
        self._client = PocketBase(base_url)
        self._base_url = base_url
        self._authenticated = False

    async def authenticate(self, email: str, password: str) -> bool:
        """
        Authenticate with PocketBase as admin.

        Args:
            email: Admin email
            password: Admin password

        Returns:
            True if authentication successful
        """
        try:
            self._client.admins.auth_with_password(email, password)
            self._authenticated = True
            return True
        except Exception as e:
            print(f"Authentication failed: {e}")
            return False

    async def set(
        self,
        collection: str,
        data: Dict[str, Any],
        key: Optional[str] = None,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Store data in PocketBase collection.

        Args:
            collection: Collection name
            data: Data to store
            key: Record ID (optional, creates new if None)
            ttl: Time-to-live (not used in PocketBase, for interface compatibility)

        Returns:
            True if stored successfully
        """
        try:
            if key:
                # Update existing
                self._client.collection(collection).update(key, data)
            else:
                # Create new
                self._client.collection(collection).create(data)
            return True
        except Exception as e:
            print(f"Error storing data: {e}")
            return False

    async def get(self, collection: str, key: str) -> Optional[Dict[str, Any]]:
        """
        Get a record by ID.

        Args:
            collection: Collection name
            key: Record ID

        Returns:
            Record data or None if not found
        """
        try:
            record = self._client.collection(collection).get_one(key)
            return dict(record.__dict__)
        except Exception as e:
            print(f"Error retrieving data: {e}")
            return None

    async def delete(self, collection: str, key: str) -> bool:
        """
        Delete a record by ID.

        Args:
            collection: Collection name
            key: Record ID

        Returns:
            True if deleted successfully
        """
        try:
            self._client.collection(collection).delete(key)
            return True
        except Exception as e:
            print(f"Error deleting data: {e}")
            return False

    async def get_all(
        self, collection: str, query_params: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all records from a collection.

        Args:
            collection: Collection name
            query_params: Optional query parameters (sort, filter, etc.)

        Returns:
            List of records
        """
        try:
            records = self._client.collection(collection).get_full_list(
                query_params=query_params or {}
            )
            return [dict(r.__dict__) for r in records]
        except Exception as e:
            print(f"Error retrieving records: {e}")
            return []

    async def query(
        self, collection: str, filter_str: str, sort: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Query records with filter.

        Args:
            collection: Collection name
            filter_str: PocketBase filter string
            sort: Sort string (e.g., "-created" for descending)

        Returns:
            List of matching records
        """
        try:
            params = {"filter": filter_str}
            if sort:
                params["sort"] = sort
            records = self._client.collection(collection).get_full_list(
                query_params=params
            )
            return [dict(r.__dict__) for r in records]
        except Exception as e:
            print(f"Error querying records: {e}")
            return []

    def is_authenticated(self) -> bool:
        """Check if authenticated with PocketBase"""
        return self._authenticated

    def get_client(self) -> PocketBase:
        """Get raw PocketBase client for advanced operations"""
        return self._client
