"""Loro Plugin for StarStream"""

from typing import Optional
from starstream import StarStreamPlugin
from .sync import LoroSyncManager
from .storage import LoroStorage


class LoroPlugin:
    """
    Loro CRDT plugin for StarStream.

    Convention over Configuration: One-line sync for collaborative editing.

    Example:
        from starhtml import *
        from starstream import StarStreamPlugin
        from starstream_loro import LoroPlugin

        app, rt = star_app()
        stream = StarStreamPlugin(app)
        loro = LoroPlugin(stream)

        @rt("/doc/{doc_id}/sync", methods=["POST"])
        async def sync_doc(doc_id: str, delta: bytes, peer_id: str = None):
            # One-line CRDT sync! Automatic broadcast to other peers.
            await loro.sync(doc_id, delta, peer_id)
    """

    def __init__(self, stream_plugin: StarStreamPlugin, storage=None, auto_peer_id: bool = False):
        """
        Initialize Loro plugin.

        Args:
            stream_plugin: StarStreamPlugin instance
            storage: Optional storage backend
            auto_peer_id: Auto-generate peer_id if not provided (default: False)
        """
        self._stream = stream_plugin
        self._sync = LoroSyncManager(storage)
        self._auto_peer = auto_peer_id

    async def sync(self, doc_id: str, delta: bytes, peer_id: str = None) -> bool:
        """
        One-line CRDT sync.

        Automatically:
        1. Connects peer to document
        2. Applies delta
        3. Broadcasts to other peers

        Args:
            doc_id: Document ID
            delta: CRDT delta bytes
            peer_id: Optional peer ID (auto-generated if auto_peer_id=True)

        Returns:
            True if sync successful

        Raises:
            ValueError: If peer_id is required but not provided

        Example:
            await loro.sync("doc-123", delta_bytes, "user-456")
        """
        if not peer_id and self._auto_peer:
            peer_id = self._get_auto_peer_id()

        if not peer_id:
            raise ValueError("peer_id required (or set auto_peer_id=True)")

        try:
            await self.connect(doc_id, peer_id)
            await self.receive_delta(doc_id, peer_id, delta)

            peers = await self.get_peers(doc_id, exclude=peer_id)
            for peer in peers:
                self._stream.broadcast(
                    delta.decode() if isinstance(delta, bytes) else delta, target=f"user:{peer}"
                )

            return True
        except Exception as e:
            raise RuntimeError(f"Loro sync failed for doc {doc_id}: {e}") from e

    def _get_auto_peer_id(self) -> str:
        """Auto-generate peer ID."""
        import uuid

        return str(uuid.uuid4())[:8]

    async def connect(self, doc_id: str, peer_id: str) -> bool:
        """Connect a peer to a document"""
        return await self._sync.connect(doc_id, peer_id)

    async def disconnect(self, doc_id: str, peer_id: str) -> bool:
        """Disconnect a peer from a document"""
        return await self._sync.disconnect(doc_id, peer_id)

    async def receive_delta(self, doc_id: str, peer_id: str, delta: bytes) -> bool:
        """Receive and apply a delta from a peer"""
        return await self._sync.receive_delta(doc_id, peer_id, delta)

    async def get_delta(self, doc_id: str, since_version: int = 0) -> Optional[bytes]:
        """Get delta since a specific version"""
        return await self._sync.get_delta(doc_id, since_version)

    async def get_peers(self, doc_id: str, exclude: Optional[str] = None) -> list:
        """Get list of peers to broadcast to"""
        return await self._sync.broadcast_delta(doc_id, exclude)

    async def get_state(self, doc_id: str) -> Optional[dict]:
        """Get document state for a new peer"""
        return await self._sync.get_document_state(doc_id)

    def on_update(self, doc_id: str, callback):
        """Register callback for document updates"""
        self._sync.on_update(doc_id, callback)

    def get_stats(self) -> dict:
        """Get plugin statistics"""
        return self._sync.get_stats()
