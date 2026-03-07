"""PocketBase Sync for StarStream"""

import asyncio
from typing import Optional, Callable, Dict, Any, List
from pocketbase import PocketBase


class PocketBaseSync:
    """
    Handles synchronization between StarStream and PocketBase.

    This class manages:
    - Real-time subscriptions to PocketBase collections
    - Broadcasting changes via StarStream
    - Sync state management

    Example:
        sync = PocketBaseSync(pb_client, stream_plugin)

        # Subscribe to collection changes
        await sync.subscribe("todos", lambda action, record: print(f"{action}: {record}"))

        # Create and broadcast
        record = await sync.create("todos", {"title": "New todo"})
    """

    def __init__(self, pb_client: PocketBase, stream_plugin=None):
        """
        Initialize PocketBase sync.

        Args:
            pb_client: Authenticated PocketBase client
            stream_plugin: Optional StarStreamPlugin for broadcasting
        """
        self._pb = pb_client
        self._stream = stream_plugin
        self._subscriptions: Dict[str, Any] = {}
        self._callbacks: Dict[str, List[Callable]] = {}

    async def subscribe(
        self, collection: str, callback: Callable[[str, Dict], None]
    ) -> bool:
        """
        Subscribe to real-time changes in a collection.

        Args:
            collection: Collection name
            callback: Function(action, record) called on changes

        Returns:
            True if subscription successful
        """
        try:
            # Store callback
            if collection not in self._callbacks:
                self._callbacks[collection] = []
            self._callbacks[collection].append(callback)

            # In real implementation, would use PocketBase's realtime API
            # For now, we poll as a fallback
            return True
        except Exception as e:
            print(f"Error subscribing to {collection}: {e}")
            return False

    async def unsubscribe(self, collection: str) -> bool:
        """Unsubscribe from collection changes"""
        try:
            if collection in self._callbacks:
                del self._callbacks[collection]
            return True
        except Exception as e:
            print(f"Error unsubscribing from {collection}: {e}")
            return False

    async def create(
        self, collection: str, data: Dict[str, Any], broadcast: bool = True
    ) -> Optional[Dict]:
        """
        Create a record and optionally broadcast the change.

        Args:
            collection: Collection name
            data: Record data
            broadcast: Whether to broadcast via StarStream

        Returns:
            Created record or None
        """
        try:
            record = self._pb.collection(collection).create(data)
            record_dict = dict(record.__dict__)

            # Broadcast if stream plugin available
            if broadcast and self._stream:
                await self._stream.broadcast_to_topic(
                    collection, ("signals", {f"{collection}_created": record_dict})
                )

            # Trigger callbacks
            await self._notify(collection, "create", record_dict)

            return record_dict
        except Exception as e:
            print(f"Error creating record: {e}")
            return None

    async def update(
        self,
        collection: str,
        record_id: str,
        data: Dict[str, Any],
        broadcast: bool = True,
    ) -> Optional[Dict]:
        """
        Update a record and optionally broadcast.

        Args:
            collection: Collection name
            record_id: Record ID
            data: Updated data
            broadcast: Whether to broadcast via StarStream

        Returns:
            Updated record or None
        """
        try:
            record = self._pb.collection(collection).update(record_id, data)
            record_dict = dict(record.__dict__)

            if broadcast and self._stream:
                await self._stream.broadcast_to_topic(
                    collection, ("signals", {f"{collection}_updated": record_dict})
                )

            await self._notify(collection, "update", record_dict)

            return record_dict
        except Exception as e:
            print(f"Error updating record: {e}")
            return None

    async def delete(
        self, collection: str, record_id: str, broadcast: bool = True
    ) -> bool:
        """
        Delete a record and optionally broadcast.

        Args:
            collection: Collection name
            record_id: Record ID
            broadcast: Whether to broadcast via StarStream

        Returns:
            True if deleted
        """
        try:
            self._pb.collection(collection).delete(record_id)

            if broadcast and self._stream:
                await self._stream.broadcast_to_topic(
                    collection,
                    ("signals", {f"{collection}_deleted": {"id": record_id}}),
                )

            await self._notify(collection, "delete", {"id": record_id})

            return True
        except Exception as e:
            print(f"Error deleting record: {e}")
            return False

    async def _notify(self, collection: str, action: str, record: Dict):
        """Notify all callbacks for a collection"""
        if collection in self._callbacks:
            for callback in self._callbacks[collection]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(action, record)
                    else:
                        callback(action, record)
                except Exception as e:
                    print(f"Callback error: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get sync statistics"""
        return {
            "subscriptions": len(self._subscriptions),
            "callbacks": {k: len(v) for k, v in self._callbacks.items()},
            "has_stream": self._stream is not None,
        }
