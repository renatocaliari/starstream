# StarStream Loro

**CRDT Integration for StarStream**

Provides conflict-free replicated data types (CRDT) support for collaborative editing in StarStream applications.

## Installation

```bash
pip install starstream-loro
```

## 🛠 AI Agent Skills

StarStream includes a `SKILL.md` for AI agents. This skill provides expert instructions for building real-time apps.
Agents can install it via:

```bash
npx skills add renatocaliari/starstream
```

## Features

- **One-line sync** - Convention over Configuration
- Loro CRDT synchronization
- Collaborative text editing
- Canvas with CRDTs
- Delta synchronization
- Version history

## Quick Start

```python
from starhtml import *
from starstream import StarStreamPlugin
from starstream_loro import LoroPlugin

app, rt = star_app()
stream = StarStreamPlugin(app)
loro = LoroPlugin(stream)

@rt("/doc/{doc_id}/sync", methods=["POST"])
async def sync_doc(doc_id: str, delta: bytes, peer_id: str):
    # One-line CRDT sync! Automatic broadcast to other peers.
    await loro.sync(doc_id, delta, peer_id)
```

## API

### `sync(doc_id, delta, peer_id=None)`

One-line CRDT sync. Automatically:
1. Connects peer to document
2. Applies delta
3. Broadcasts to other peers

```python
# With explicit peer_id
await loro.sync("doc-123", delta_bytes, "user-456")

# With auto-generated peer_id
loro = LoroPlugin(stream, auto_peer_id=True)
await loro.sync("doc-123", delta_bytes)
```

### Advanced Methods

For advanced use cases, the following methods are also available:

- `connect(doc_id, peer_id)` - Connect a peer to a document
- `disconnect(doc_id, peer_id)` - Disconnect a peer from a document
- `receive_delta(doc_id, peer_id, delta)` - Receive and apply a delta
- `get_delta(doc_id, since_version)` - Get delta since a specific version
- `get_peers(doc_id, exclude)` - Get list of peers to broadcast to
- `get_state(doc_id)` - Get document state for a new peer
- `on_update(doc_id, callback)` - Register callback for document updates

## License

MIT