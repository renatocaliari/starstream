# StarStream-Loro

**Loro CRDT integration for StarStream - Conflict-free collaborative editing**

This plugin adds [Loro](https://loro.dev) CRDT support to StarStream, enabling automatic conflict resolution for collaborative documents.

## What are CRDTs?

CRDTs (Conflict-free Replicated Data Types) are data structures that can be edited by multiple users simultaneously without conflicts. Changes merge automatically, ensuring all users eventually see the same state.

## Installation

```bash
pip install starstream-loro
```

## Quick Start

```python
from starhtml import *
from starstream import StarStreamPlugin
from starstream_loro import LoroPlugin

app, rt = star_app()
stream = StarStreamPlugin(app)
loro = LoroPlugin(stream)

@rt("/doc/{doc_id}/connect")
async def connect_to_doc(doc_id: str, peer_id: str):
    """Connect a peer to a collaborative document"""
    await loro.connect(doc_id, peer_id)
    
    # Get document state for the new peer
    state = await loro.get_state(doc_id)
    return {"state": state}

@rt("/doc/{doc_id}/sync", methods=["POST"])
async def sync_doc(doc_id: str, peer_id: str, delta: bytes):
    """Receive and broadcast updates"""
    # Apply delta to document
    await loro.receive_delta(doc_id, peer_id, delta)
    
    # Get peers to broadcast to (excluding sender)
    peers = await loro.get_peers(doc_id, exclude=peer_id)
    
    # Broadcast to other peers
    for peer in peers:
        await stream.send_to_user(peer, delta)
    
    return {"status": "synced", "peers_notified": len(peers)}
```

## How It Works

```
┌─────────────────────────────────────────────┐
│         Collaborative Document              │
├─────────────────────────────────────────────┤
│                                             │
│  User A ──┐                                 │
│           │    ┌─────────────────────┐     │
│  User B ──┼───►│   LoroSyncManager   │     │
│           │    │   (CRDT merging)    │     │
│  User C ──┘    └─────────────────────┘     │
│                       │                     │
│                       ▼                     │
│              ┌─────────────────┐           │
│              │  LoroStorage    │           │
│              │  (persistence)  │           │
│              └─────────────────┘           │
└─────────────────────────────────────────────┘
```

## Features

- ✅ **Automatic conflict resolution** - No manual merge needed
- ✅ **Offline support** - Edit offline, sync when back online
- ✅ **Version history** - Track all changes
- ✅ **Delta synchronization** - Efficient updates
- ✅ **Storage backend** - Persist documents to SQLite/PostgreSQL
- ✅ **StarStream integration** - Works seamlessly with presence, typing, cursors

## Architecture

### LoroSyncManager

Core CRDT synchronization logic:
- `connect(doc_id, peer_id)` - Add peer to document
- `receive_delta(doc_id, peer_id, delta)` - Apply incoming changes
- `get_delta(doc_id, since_version)` - Get changes since version
- `broadcast_delta(doc_id, exclude)` - Get peers to notify

### LoroStorage

Persistent storage for documents:
- Save/load document snapshots
- Store delta history
- Replay changes

### LoroPlugin

High-level integration with StarStream:
- Automatic SSE broadcasting
- Connection management
- Event callbacks

## Example: Collaborative Text Editor

```python
from starhtml import *
from starstream import StarStreamPlugin
from starstream_loro import LoroPlugin

app, rt = star_app()
stream = StarStreamPlugin(app)
loro = LoroPlugin(stream)

def CollaborativeEditor(doc_id: str):
    """A collaborative text editor component"""
    return Div(
        # Connect to document on load
        data_star_on("load", f"fetch('/doc/{doc_id}/connect?peer_id=' + crypto.randomUUID())"),
        
        # Editor
        TextArea(
            id=f"editor-{doc_id}",
            cls="w-full h-96 p-4 border rounded",
            data_star_on("input", f"syncDocument('{doc_id}', this.value)")
        ),
        
        # Sync status
        Div(id=f"sync-status-{doc_id}", cls="text-sm text-gray-500")
    )

@rt("/editor/{doc_id}")
def editor_page(doc_id: str):
    return CollaborativeEditor(doc_id)

@rt("/doc/{doc_id}/connect")
async def doc_connect(doc_id: str, peer_id: str):
    await loro.connect(doc_id, peer_id)
    return {"status": "connected"}

@rt("/doc/{doc_id}/update", methods=["POST"])
async def doc_update(doc_id: str, peer_id: str, delta: bytes):
    # Apply delta
    await loro.receive_delta(doc_id, peer_id, delta)
    
    # Broadcast to other peers
    peers = await loro.get_peers(doc_id, exclude=peer_id)
    for peer in peers:
        await stream.send_to_user(peer, delta)
    
    return {"synced": len(peers)}
```

## Storage Options

```python
from starstream.storage import SQLiteBackend
from starstream_loro import LoroStorage, LoroPlugin

# Use SQLite for persistence
base_storage = SQLiteBackend("documents.db")
loro_storage = LoroStorage(base_storage)
loro = LoroPlugin(stream, storage=loro_storage)
```

## Integration with StarStream Features

Combine with existing features for rich collaboration:

```python
# Presence + CRDT
stream = StarStreamPlugin(app, enable_presence=True)
loro = LoroPlugin(stream)

# User sees who's editing
await presence.join(doc_id, username)

# Changes sync automatically via CRDT
await loro.receive_delta(doc_id, peer_id, delta)
```

## License

MIT
