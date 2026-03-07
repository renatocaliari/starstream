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
pip install starstream
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

### 2. Multi-Room Chat (Auto-Room Detection)

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

For complete control, use the manual API:

```python
# Broadcast to specific topic
await stream.broadcast_to_topic("my-topic", message)

# Send to specific user
await stream.send_to_user(user_id, message)

# Broadcast to room
await stream.broadcast_to_room(room_id, message)

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
    await stream.broadcast_to_topic("global", 
        ('signals', {'cursor': {'x': x, 'y': y}})
    )
```

### Debouncing

```python
from starstream.helpers import debounce

@rt("/doc/{doc_id}/save", methods=["POST"])
@debounce(0.5)  # Wait 500ms after last change
async def save_document(doc_id: str, content: str):
    # Save and notify
    await stream.broadcast_to_topic(f"doc:{doc_id}",
        ('signals', {'saved': True})
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
StarStreamPlugin(app, default_topic="global")
```

**Methods:**

- `configure(topic, exclude_self, filter_fn, broadcast)` - Decorator for custom config
- `broadcast_to_topic(topic, message)` - Manual broadcast
- `broadcast_to_room(room_id, message)` - Room broadcast
- `send_to_user(user_id, message)` - User-specific message
- `get_stream_url(topic)` - Get SSE endpoint URL

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
    await stream.broadcast_to_room(room_id,
        ('signals', {'online': online_users})
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
    await stream.broadcast_to_room(room_id,
        ('signals', {'typing': typers})
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
    await stream.broadcast_to_room(room_id,
        ('signals', {'cursors': positions})
    )
```

### Message History

Store and retrieve message history:

```python
from starstream import MessageHistory

history = MessageHistory(max_messages=1000, ttl_seconds=3600)

@rt("/chat/send", methods=["POST"])
async def send_message(user: str, msg: str, room_id: str):
    # Store the message
    await history.add(room_id, {
        'user': user,
        'text': msg,
        'timestamp': time.time()
    })
    
    # Get recent history
    recent = history.get_recent(room_id, limit=50)
```

### SQLite Storage Backend (Default)

**SQLite is the default persistence backend** when you enable storage. No external database required.

```python
from starstream import StarStreamPlugin
from starstream.storage import SQLiteBackend

# SQLite backend - default, file-based persistence
storage = SQLiteBackend("starstream.db")
stream = StarStreamPlugin(
    app,
    storage=storage,  # Enable persistence with SQLite (default)
    enable_presence=True,
    enable_typing=True,
    enable_cursor=True,
    enable_history=True
)
```

**Other storage options:**
- **PocketBase** - Database with admin UI, auth, file storage (see `starstream-pocketbase` plugin)
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

# Loro CRDT integration (separate plugin)
pip install starstream-loro
```

## License

MIT
