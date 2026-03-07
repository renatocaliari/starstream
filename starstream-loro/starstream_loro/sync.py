"""Loro CRDT Sync Manager for StarStream"""

import asyncio
from typing import Dict, Optional, Callable, Any, Set
from dataclasses import dataclass


@dataclass
class LoroDocument:
    """Represents a Loro CRDT document"""

    doc_id: str
    content: bytes  # Serialized Loro document
    version: int
    peers: Set[str]  # Connected peer IDs


class LoroSyncManager:
    """
    Manages CRDT synchronization for collaborative documents.

    This manager handles:
    - Document state tracking
    - Delta generation and application
    - Peer synchronization
    - Conflict resolution (automatic via CRDTs)

    Example:
        manager = LoroSyncManager()

        # Client connects
        await manager.connect(doc_id="doc1", peer_id="user1")

        # Receive update from client
        delta = await manager.receive_delta(doc_id="doc1", peer_id="user1", delta=data)

        # Broadcast to other peers
        await manager.broadcast_delta(doc_id="doc1", exclude="user1")
    """

    def __init__(self, storage=None):
        self._documents: Dict[str, LoroDocument] = {}
        self._storage = storage
        self._update_callbacks: Dict[str, list] = {}
        self._lock = asyncio.Lock()

    async def connect(self, doc_id: str, peer_id: str) -> bool:
        """
        Connect a peer to a document.

        Returns True if new connection, False if already connected.
        """
        async with self._lock:
            if doc_id not in self._documents:
                # Create new document
                self._documents[doc_id] = LoroDocument(
                    doc_id=doc_id, content=b"", version=0, peers=set()
                )

            doc = self._documents[doc_id]
            if peer_id in doc.peers:
                return False

            doc.peers.add(peer_id)

            # Trigger callbacks
            await self._trigger_callbacks(doc_id, "peer_joined", peer_id)

            return True

    async def disconnect(self, doc_id: str, peer_id: str) -> bool:
        """Disconnect a peer from a document"""
        async with self._lock:
            if doc_id not in self._documents:
                return False

            doc = self._documents[doc_id]
            if peer_id not in doc.peers:
                return False

            doc.peers.remove(peer_id)

            # Clean up if no peers
            if not doc.peers:
                await self._save_document(doc_id)
                del self._documents[doc_id]

            await self._trigger_callbacks(doc_id, "peer_left", peer_id)
            return True

    async def receive_delta(self, doc_id: str, peer_id: str, delta: bytes) -> bool:
        """
        Receive a delta update from a peer.

        Returns True if delta was applied successfully.
        """
        async with self._lock:
            if doc_id not in self._documents:
                return False

            doc = self._documents[doc_id]
            if peer_id not in doc.peers:
                return False

            # In real implementation, this would:
            # 1. Deserialize the Loro delta
            # 2. Apply to local document state
            # 3. Increment version
            # 4. Persist if needed

            # For now, simulate update
            doc.content = delta  # In reality: merge(delta)
            doc.version += 1

            await self._trigger_callbacks(
                doc_id, "updated", {"peer_id": peer_id, "version": doc.version}
            )

            return True

    async def get_delta(self, doc_id: str, since_version: int = 0) -> Optional[bytes]:
        """
        Get delta changes since a specific version.

        Returns None if document not found.
        """
        async with self._lock:
            if doc_id not in self._documents:
                return None

            doc = self._documents[doc_id]

            if since_version >= doc.version:
                return b""  # No changes

            # In real implementation:
            # return doc.get_delta_since(since_version)
            return doc.content

    async def broadcast_delta(self, doc_id: str, exclude: Optional[str] = None) -> list:
        """
        Get list of peers to broadcast to (excluding sender).

        Returns list of peer_ids.
        """
        async with self._lock:
            if doc_id not in self._documents:
                return []

            doc = self._documents[doc_id]
            peers = list(doc.peers)

            if exclude and exclude in peers:
                peers.remove(exclude)

            return peers

    async def get_document_state(self, doc_id: str) -> Optional[dict]:
        """Get current document state for a new peer"""
        async with self._lock:
            if doc_id not in self._documents:
                return None

            doc = self._documents[doc_id]
            return {
                "doc_id": doc.doc_id,
                "version": doc.version,
                "peers": list(doc.peers),
                "content": doc.content,  # In reality: snapshot
            }

    def on_update(self, doc_id: str, callback: Callable):
        """Register callback for document updates"""
        if doc_id not in self._update_callbacks:
            self._update_callbacks[doc_id] = []
        self._update_callbacks[doc_id].append(callback)

    async def _trigger_callbacks(self, doc_id: str, event: str, data: Any):
        """Trigger registered callbacks"""
        if doc_id in self._update_callbacks:
            for callback in self._update_callbacks[doc_id]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event, data)
                    else:
                        callback(event, data)
                except Exception as e:
                    print(f"Callback error: {e}")

    async def _save_document(self, doc_id: str):
        """Persist document to storage"""
        if self._storage and doc_id in self._documents:
            doc = self._documents[doc_id]
            await self._storage.save(doc_id, doc.content, doc.version)

    async def load_document(self, doc_id: str) -> bool:
        """Load document from storage"""
        if not self._storage:
            return False

        data = await self._storage.load(doc_id)
        if data:
            async with self._lock:
                self._documents[doc_id] = LoroDocument(
                    doc_id=doc_id,
                    content=data["content"],
                    version=data["version"],
                    peers=set(),
                )
            return True
        return False

    def get_stats(self) -> dict:
        """Get sync manager statistics"""
        return {
            "documents": len(self._documents),
            "total_peers": sum(len(d.peers) for d in self._documents.values()),
            "doc_ids": list(self._documents.keys()),
        }
