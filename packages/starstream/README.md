# StarStream

**Convention over Configuration for StarHTML Real-time Broadcasting**

StarStream provides automatic real-time broadcasting for StarHTML applications with **zero configuration** by default, while allowing full customization when needed.

## Philosophy

> **"It just works"** - Zero config for common cases, full control when you need it.

```python
from starhtml import *
from starstream import StarStreamPlugin

app, rt = star_app()
stream = StarStreamPlugin(app)  # That's it!

@rt("/chat")
@sse
async def chat(msg: str):
    yield elements(Div(msg), "#chat", "append")
    # Automatically broadcasts to all clients! 🚀
```

## Installation

```bash
# Core package (lightweight)
pip install starstream

# With collaborative editing support
pip install starstream[collaborative]
```

## 🛠 AI Agent Skills

StarStream includes a `SKILL.md` for AI agents. This skill provides expert instructions for building real-time apps.
Agents can install it via:

```bash
npx skills add renatocaliari/starstream
```

## Quick Start

### 1. Global Chat (Zero Config)

```python
from starhtml import *
from starstream import StarStreamPlugin

app, rt = star_app()
stream = StarStreamPlugin(app)

@rt("/chat", methods=["POST"])
@sse
async def chat(msg: str):
    yield elements(Div(msg), "#chat", "append")
```

**That's it!** All connected clients automatically receive messages.

### 2. Chat with Persistence

```python
# Messages are saved to SQLite automatically
stream = StarStreamPlugin(app, persist=True)

@rt("/chat", methods=["POST"])
@sse
async def chat(msg: str):
    yield elements(Div(msg), "#chat", "append")
    # Messages persist across restarts!
```

### 3. Collaborative Editing

```python
# Install: pip install starstream[collaborative]
stream = StarStreamPlugin(app, collaborative=True)

@rt("/doc/{doc_id}/sync", methods=["POST"])
async def sync_doc(doc_id: str, delta: bytes, user_id: str):
    # One-line CRDT sync! Automatic conflict resolution.
    await stream.collaborative.sync(doc_id, delta, user_id)
```

### 4. Multi-Room Chat (Auto-Room Detection)

```python
@rt("/room/{room_id}/send", methods=["POST"])
@sse
async def room_chat(room_id: str, msg: str):
    """Automatically broadcasts only to clients in this room!"""
    yield elements(Div(msg), f"#room-{room_id}", "append")
```

StarStream automatically detects the `room_id` parameter and creates a room-specific topic.

### 3. Direct Messages (Auto-User Detection)

```python
@rt("/dm/{user_id}", methods=["POST"])
@sse
async def direct_message(user_id: str, msg: str):
    """Automatically sends only to this user!"""
    yield elements(Div(msg, cls="dm"), "#dms", "append")
```

## How It Works

### Auto-Detection Conventions

StarStream automatically detects the appropriate broadcast topic based on your route:

| Route Pattern | Auto-Detected Topic | Description |
|--------------|-------------------|-------------|
| `/chat` | `chat` | Global topic |
| `/room/{room_id}` | `room:{room_id}` | Room-specific |
| `/user/{user_id}/dm` | `user:{user_id}` | User-specific |
| `/api/notifications` | `api:notifications` | Namespaced |

### Convention Priority

1. **Room ID** (`room_id` parameter) → `room:{room_id}`
2. **User ID** (`user_id` parameter) → `user:{user_id}`
3. **Route Path** → Cleaned path as topic
4. **Default** → `global`

## Customization

When you need more control, use the configuration decorator:

```python
@rt("/admin")
@stream.configure(
    topic="admin-only",
    filter_fn=lambda ctx: ctx.get('is_admin', False)
)
@sse
async def admin_message(msg: str):
    yield elements(Div(msg), "#admin")
```

### Manual API

For complete control, use the broadcast method:

```python
# Broadcast to topic
stream.broadcast(message, target="my-topic")

# Broadcast to room
stream.broadcast(message, target="room:123")

# Send to user
stream.broadcast(message, target="user:456")

# Get stream URL
url = stream.get_stream_url(topic="my-topic")
```

## Advanced Features

### Rate Limiting

```python
from starstream.helpers import throttle

@rt("/cursor", methods=["POST"])
@throttle(0.05)  # Max 20 updates/second
async def cursor_update(x: int, y: int):
    stream.broadcast(
        ('signals', {'cursor': {'x': x, 'y': y}}),
        target="global"
    )
```

### Debouncing

```python
from starstream.helpers import debounce

@rt("/doc/{doc_id}/save", methods=["POST"])
@debounce(0.5)  # Wait 500ms after last change
async def save_document(doc_id: str, content: str):
    # Save and notify
    stream.broadcast(
        ('signals', {'saved': True}),
        target=f"doc:{doc_id}"
    )
```

### Message Builders

```python
from starstream.helpers import MessageBuilder

# Build common message patterns
msg = MessageBuilder.notification("Hello!", type_="success")
msg = MessageBuilder.element_append("#list", Div("New item"))
msg = MessageBuilder.signal_update(counter=42, status="active")
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              StarStreamPlugin                       │
├─────────────────────────────────────────────────────┤
│  Auto-Detection → Convention → Topic → Broadcast   │
├─────────────────────────────────────────────────────┤
│  SSE Interceptor (automatic)                        │
├─────────────────────────────────────────────────────┤
│  StarStream Core (topics, subscribers, broadcast)  │
└─────────────────────────────────────────────────────┘
```

## API Reference

### StarStreamPlugin

```python
StarStreamPlugin(
    app,
    default_topic="global",
    persist=False,           # Enable persistence (auto-creates SQLite)
    collaborative=False,     # Enable collaborative editing (requires loro)
    db_path=None,            # Custom SQLite path
    storage=None,            # Custom storage backend
    enable_presence=False,   # Track online users
    enable_typing=False,     # Show typing indicators
    enable_cursors=False     # Track mouse positions
)
```

**Key Parameters:**

- `persist` - Enable persistence (messages saved to SQLite automatically)
- `collaborative` - Enable CRDT-based collaborative editing
- `db_path` - Custom SQLite database path (default: `starstream.db`)
- `storage` - Custom storage backend (overrides auto-creation)

**Methods:**

- `configure(topic, exclude_self, filter_fn, broadcast)` - Decorator for custom config
- `broadcast(message, target)` - Fire-and-forget broadcast
- `get_stream_url(topic)` - Get SSE endpoint URL
- `get_stream_element(topic)` - Get SSE connection element
- `collaborative` - Access collaborative editing engine (if enabled)

### Helpers

- `throttle(seconds)` - Rate limit decorator
- `debounce(seconds)` - Wait for pause decorator
- `MessageBuilder` - Common message patterns
- `RateLimiter` - Programmatic rate limiting

## Advanced Features

### Presence System

Track online users with automatic cleanup:

```python
from starstream import PresenceSystem

presence = PresenceSystem(expire_seconds=300)

@rt("/room/{room_id}")
async def join_room(room_id: str, user: str):
    # User joins the room
    await presence.join(room_id, user)
    
    # Broadcast who is online
    online_users = presence.get_online(room_id)
    stream.broadcast(
        ('signals', {'online': online_users}),
        target=f"room:{room_id}"
    )

@rt("/room/{room_id}/leave", methods=["POST"])
async def leave_room(room_id: str, user: str):
    await presence.leave(room_id, user)
```

### Typing Indicators

Show who's typing with auto-timeout:

```python
from starstream import TypingIndicator

typing = TypingIndicator(auto_stop_seconds=5)

@rt("/chat/typing", methods=["POST"])
async def user_typing(user: str, room_id: str):
    await typing.start(room_id, user)
    typers = typing.get_typing(room_id)
    stream.broadcast(
        ('signals', {'typing': typers}),
        target=f"room:{room_id}"
    )
```

### Cursor Tracking

Track user cursors in real-time:

```python
from starstream import CursorTracker
from starstream.helpers import throttle

cursors = CursorTracker(update_throttle=0.05)

@rt("/cursor", methods=["POST"])
@throttle(0.05)  # 20 updates/second max
async def cursor_update(x: int, y: int, user: str, room_id: str):
    await cursors.update(room_id, user, x, y)
    positions = cursors.get_positions(room_id)
    stream.broadcast(
        ('signals', {'cursors': positions}),
        target=f"room:{room_id}"
    )
```

### Persistence

**Automatic with `persist=True`:**

```python
# SQLite auto-created at starstream.db
stream = StarStreamPlugin(app, persist=True)
```

**Custom database path:**

```python
stream = StarStreamPlugin(app, persist=True, db_path="my-app.db")
```

**Custom storage backend:**

```python
from starstream.storage import StorageBackend

class PostgresBackend(StorageBackend):
    # Implement your own backend...
    pass

stream = StarStreamPlugin(
    app,
    persist=True,
    storage=PostgresBackend(DATABASE_URL)
)
```

### Collaborative Editing

**Real CRDT-powered collaborative editing with Loro:**

```python
# Install with Loro support
pip install starstream[collaborative]

# Enable collaborative editing
stream = StarStreamPlugin(app, collaborative=True)

# Sync document changes (uses real Loro CRDT under the hood)
@rt("/doc/{doc_id}/sync", methods=["POST"])
async def sync_doc(doc_id: str, delta: bytes, user_id: str):
    # delta is exported from LoroDoc on the client
    await stream.collaborative.sync(doc_id, delta, user_id)

# Get document state
state = await stream.collaborative.get_state(doc_id)
# Returns: {"doc_id": "...", "peers": [...], "content": <Loro snapshot>}
```

**How it works:**
- Uses **Loro CRDT** (v1.10.3+) for conflict-free collaborative editing
- Automatic conflict resolution
- Documents can be persisted to storage
- Exports/imports Loro snapshots and deltas

**With persistence:**

```python
# Collaborative documents persist to SQLite
stream = StarStreamPlugin(
    app,
    collaborative=True,
    persist=True
)
```

**Note:** Requires `loro` package. Install with:
```bash
pip install starstream[collaborative]
```

### SQLite Storage Backend (Default)

**SQLite is automatic** when you enable `persist`. No imports, no configuration:

```python
# SQLite auto-created at starstream.db
stream = StarStreamPlugin(app, persist=True)
```

**Custom database path (optional):**

```python
# Custom SQLite location
stream = StarStreamPlugin(
    app,
    persist=True,
    db_path="my-app.db"
)
```

**Advanced: Custom backend (optional):**

```python
from starstream.storage import StorageBackend

# Implement your own backend
class PostgresBackend(StorageBackend):
    async def get(self, key: str):
        # Your implementation...
        pass
    
    async def set(self, key: str, value, ttl=None):
        # Your implementation...
        pass
    
    # ... other methods

stream = StarStreamPlugin(
    app,
    persist=True,
    storage=PostgresBackend(DATABASE_URL)
)
```

**Other storage options:**
- **PocketBase** - When you need auth, admin UI, or file storage (see `starstream-pocketbase`)
- **Custom backend** - Implement your own `StorageBackend` ABC

## Examples

See the `examples/` directory:

- `basic.py` - Zero config global chat
- `rooms.py` - Multi-room chat
- `custom.py` - Advanced customization
- `full_features.py` - All features demo

## Optional Dependencies

```bash
# Development
pip install starstream[dev]

# Collaborative editing
pip install starstream[collaborative]
```

## License

MIT
