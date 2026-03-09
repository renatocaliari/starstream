"""
Collaborative Engine - CRDT-based collaborative editing.

Uses Loro CRDT under the hood for conflict-free collaborative editing.
"""

import asyncio
import json
from typing import Dict, Optional, Set, Any
from dataclasses import dataclass


@dataclass
class CollaborativeDocument:
    """Represents a collaborative CRDT document."""

    doc_id: str
    loro_doc: Any  # LoroDoc instance
    peers: Set[str]
    json_data: Optional[Dict[str, Any]] = None  # Fallback JSON storage when Loro not available
    is_json_mode: bool = False  # True when using JSON instead of Loro


class CollaborativeEngine:
    """
    CRDT-based collaborative editing engine.

    This engine provides:
    - Real-time collaborative editing
    - Automatic conflict resolution
    - Document versioning
    - Peer management

    Example:
        from starstream import StarStreamPlugin

        stream = StarStreamPlugin(app, collaborative=True)

        # Sync document changes
        await stream.collaborative.sync("doc-1", delta, "user-123")

        # Get document state
        state = await stream.collaborative.get_state("doc-1")
    """

    def __init__(self, storage=None, broadcaster=None, topic_prefix: str = "doc"):
        """
        Initialize collaborative engine.

        Args:
            storage: Optional storage backend for persistence.
                     If None, documents are kept in memory.
            broadcaster: Optional broadcast function for real-time updates.
                        Receives (message, target) and broadcasts to peers.
            topic_prefix: Prefix for broadcast topics (default: "doc").
                         Use "canvas" for canvas apps, "doc" for documents, etc.
        """
        self._documents: Dict[str, CollaborativeDocument] = {}
        self._storage = storage
        self._broadcaster = broadcaster
        self._topic_prefix = topic_prefix
        self._lock = asyncio.Lock()

        # Check if Loro is available
        try:
            from loro import LoroDoc

            self._loro_available = True
        except ImportError:
            self._loro_available = False

    def _create_doc(self):
        """Create a new LoroDoc or raise error if Loro not available."""
        if not self._loro_available:
            raise ImportError(
                "Collaborative editing requires 'loro'.\n"
                "Install with: pip install starstream[collaborative]"
            )
        from loro import LoroDoc

        return LoroDoc()

    async def connect(self, doc_id: str, peer_id: str) -> bool:
        """
        Connect a peer to a document.

        Args:
            doc_id: Document identifier
            peer_id: Peer/user identifier

        Returns:
            True if new connection, False if already connected
        """
        async with self._lock:
            if doc_id not in self._documents:
                # Create new document with Loro
                loro_doc = self._create_doc()

                # Load from storage if available
                if self._storage:
                    stored = await self._storage.get(f"loro:{doc_id}")
                    if stored:
                        try:
                            loro_doc.import_(stored["content"])
                        except Exception:
                            pass  # Start fresh if load fails

                self._documents[doc_id] = CollaborativeDocument(
                    doc_id=doc_id, loro_doc=loro_doc, peers=set(), json_data={}
                )

            doc = self._documents[doc_id]
            if peer_id in doc.peers:
                return False

            doc.peers.add(peer_id)
            return True

    async def disconnect(self, doc_id: str, peer_id: str) -> bool:
        """
        Disconnect a peer from a document.

        Args:
            doc_id: Document identifier
            peer_id: Peer/user identifier

        Returns:
            True if disconnected, False if not found
        """
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

            return True

    async def sync(self, doc_id: str, delta: bytes, peer_id: str) -> bool:
        """
        Sync a document with changes from a peer.

        Automatically:
        1. Connects peer if not already connected
        2. Applies delta to document using Loro CRDT
        3. Broadcasts changes to other peers (if broadcaster configured)

        This is the "Convention over Configuration" approach - sync implies
        propagation to other peers by default.

        Args:
            doc_id: Document identifier
            delta: CRDT delta bytes (exported from LoroDoc)
            peer_id: Peer/user identifier

        Returns:
            True if sync successful
        """
        # First apply the delta locally
        success = await self.apply_delta(doc_id, delta, peer_id)
        if not success:
            return False

        # Broadcast to other peers if broadcaster is available
        if self._broadcaster:
            async with self._lock:
                if doc_id in self._documents:
                    doc = self._documents[doc_id]
                    other_peers = doc.peers - {peer_id}

                    if doc.is_json_mode:
                        # In JSON mode, just re-broadcast the delta as-is
                        peer_delta = delta
                    else:
                        # In Loro mode, export update
                        try:
                            peer_delta = doc.loro_doc.export({"mode": "update"})
                        except Exception:
                            # If export fails, use original delta
                            peer_delta = delta

                    # Broadcast via SSE to the document topic
                    # All peers subscribed to this document will receive it
                    self._broadcaster(
                        (
                            "signals",
                            {
                                "collaborative": {
                                    "doc_id": doc_id,
                                    "delta": peer_delta.hex()
                                    if isinstance(peer_delta, bytes)
                                    else peer_delta,  # Convert bytes to hex for JSON
                                    "from_peer": peer_id,
                                    "peers": list(other_peers),  # Debug info
                                    "is_json": doc.is_json_mode,
                                }
                            },
                        ),
                        target=f"{self._topic_prefix}:{doc_id}",  # Use configured prefix (doc, canvas, etc.)
                    )

        return True

    async def apply_delta(self, doc_id: str, delta: bytes, peer_id: str) -> bool:
        """
        Apply a delta to a document WITHOUT broadcasting to other peers.

        Automatically detects delta format:
        - Loro CRDT deltas: Applied using Loro (if available)
        - JSON deltas: Stored as JSON data (fallback mode)

        Use this for:
        - Manual control over when to broadcast
        - Server-side only updates
        - Custom synchronization logic

        For automatic broadcast, use sync() instead.

        Args:
            doc_id: Document identifier
            delta: CRDT delta bytes (exported from LoroDoc) or JSON data
            peer_id: Peer/user identifier

        Returns:
            True if delta applied successfully
        """
        # Auto-connect if needed
        if doc_id not in self._documents or peer_id not in self._documents[doc_id].peers:
            await self.connect(doc_id, peer_id)

        async with self._lock:
            if doc_id not in self._documents:
                return False

            doc = self._documents[doc_id]

            # Try to import as Loro CRDT first
            if not doc.is_json_mode and self._loro_available:
                try:
                    doc.loro_doc.import_(delta)
                    doc.loro_doc.commit()
                    return True
                except Exception:
                    # Failed to import as Loro - switch to JSON mode
                    doc.is_json_mode = True
                    if doc.json_data is None:
                        doc.json_data = {}

            # JSON fallback mode
            if doc.is_json_mode or not self._loro_available:
                try:
                    # Decode bytes to string
                    json_str = delta.decode("utf-8")
                    # Parse JSON
                    data = json.loads(json_str)
                    # Merge into document data
                    if doc.json_data is None:
                        doc.json_data = {}
                    # Store under peer_id to track who sent what
                    if "updates" not in doc.json_data:
                        doc.json_data["updates"] = []
                    doc.json_data["updates"].append(
                        {
                            "peer": peer_id,
                            "data": data,
                            "timestamp": asyncio.get_event_loop().time(),
                        }
                    )
                    return True
                except Exception as e:
                    print(f"Error applying JSON delta to document {doc_id}: {e}")
                    return False

            return False

    async def get_state(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current document state.

        Args:
            doc_id: Document identifier

        Returns:
            Document state dict or None if not found
        """
        async with self._lock:
            if doc_id not in self._documents:
                return None

            doc = self._documents[doc_id]

            # Export snapshot from Loro
            snapshot = doc.loro_doc.export({"mode": "snapshot"})

            return {
                "doc_id": doc.doc_id,
                "peers": list(doc.peers),
                "content": snapshot,
                "version": doc.loro_doc.oplog_vv.encode()
                if hasattr(doc.loro_doc, "oplog_vv")
                else b"",
            }

    def get_stats(self) -> Dict[str, Any]:
        """
        Get engine statistics.

        Returns:
            Stats dict with document and peer counts
        """
        return {
            "documents": len(self._documents),
            "total_peers": sum(len(d.peers) for d in self._documents.values()),
            "doc_ids": list(self._documents.keys()),
        }

    async def _save_document(self, doc_id: str):
        """Persist document to storage."""
        if self._storage and doc_id in self._documents:
            doc = self._documents[doc_id]

            # Export snapshot
            snapshot = doc.loro_doc.export({"mode": "snapshot"})

            # Save to storage
            await self._storage.set(
                f"loro:{doc_id}",
                {
                    "content": snapshot,
                    "doc_id": doc_id,
                },
            )
