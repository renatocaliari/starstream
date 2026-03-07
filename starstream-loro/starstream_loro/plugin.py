"""Loro Plugin for StarStream"""

from typing import Optional
from starstream import StarStreamPlugin
from .sync import LoroSyncManager
from .storage import LoroStorage


class LoroPlugin:
    """
    Loro CRDT plugin for StarStream.

    Integrates Loro CRDTs with StarStream for automatic conflict-free
    collaborative editing.

    Example:
        from starhtml import *
        from starstream import StarStreamPlugin
        from starstream_loro import LoroPlugin

        app, rt = star_app()
        stream = StarStreamPlugin(app)
        loro = LoroPlugin(stream)

        @rt("/doc/{doc_id}/sync", methods=["POST"])
        async def sync_doc(doc_id: str, peer_id: str, delta: bytes):
            # Automatic CRDT sync!
            await loro.connect(doc_id, peer_id)
            await loro.receive_delta(doc_id, peer_id, delta)
            peers = await loro.get_peers(doc_id, exclude=peer_id)
            for peer in peers:
                await stream.send_to_user(peer, delta)
    """

    def __init__(self, stream_plugin: StarStreamPlugin, storage=None):
        self._stream = stream_plugin
        self._sync = LoroSyncManager(storage)

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
