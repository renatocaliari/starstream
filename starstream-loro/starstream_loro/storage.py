"""Loro Storage Backend"""

from typing import Optional, Dict, Any
from starstream.storage.base import StorageBackend


class LoroStorage:
    """
    Storage wrapper for Loro CRDT documents.

    Wraps an existing StorageBackend to add Loro-specific operations
    like saving/loading document snapshots and deltas.

    Example:
        from starstream.storage import SQLiteBackend
        base_storage = SQLiteBackend("loro.db")
        storage = LoroStorage(base_storage)
        await storage.save("doc1", content, version=5)
        data = await storage.load("doc1")
    """

    def __init__(self, backend: StorageBackend):
        self._backend = backend

    async def save(
        self,
        doc_id: str,
        content: bytes,
        version: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Save a Loro document.

        Args:
            doc_id: Document identifier
            content: Serialized Loro document (snapshot or delta)
            version: Document version number
            metadata: Optional metadata (timestamp, peer_id, etc.)
        """
        key = f"loro:{doc_id}"
        value = {
            "content": content,
            "version": version,
            "metadata": metadata or {},
            "type": "loro_document",
        }
        return await self._backend.set(key, value, ttl=None)  # Documents don't expire

    async def load(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Load a Loro document by ID"""
        key = f"loro:{doc_id}"
        return await self._backend.get(key)

    async def delete_doc(self, doc_id: str) -> bool:
        """Delete a Loro document"""
        key = f"loro:{doc_id}"
        return await self._backend.delete(key)

    async def save_delta(
        self, doc_id: str, delta: bytes, from_version: int, to_version: int
    ) -> bool:
        """
        Save a delta update for replay/audit.

        This allows reconstructing document history.
        """
        key = f"loro:{doc_id}:delta:{to_version}"
        value = {
            "delta": delta,
            "from_version": from_version,
            "to_version": to_version,
            "type": "loro_delta",
        }
        return await self._backend.set(key, value, ttl=None)

    async def get_deltas(self, doc_id: str, since_version: int = 0) -> list:
        """
        Get all deltas for a document since a version.

        Useful for replaying history or catching up peers.
        """
        # In real implementation, would query storage for delta range
        # For now, return empty list
        return []

    async def list_documents(self) -> list:
        """List all stored document IDs"""
        # In real implementation, would scan storage
        return []

    async def cleanup_old_versions(self, doc_id: str, keep_last: int = 10) -> int:
        """
        Clean up old delta versions, keeping only the last N.

        Returns number of deleted entries.
        """
        # Implementation would remove old deltas
        return 0
