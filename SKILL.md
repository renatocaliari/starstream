---
name: starstream
description: Add real-time broadcasting and collaboration to StarHTML apps with zero configuration. Provides plugins for StarStream (core broadcasting), PocketBase (persistent real-time database), and Loro (CRDT collaborative editing). Use for multi-user synchronization, presence tracking, typing indicators, cursor tracking, and conflict-free collaborative editing.
---

# StarStream — Real-time Broadcasting for StarHTML

**Convention over Configuration** — Zero config for common cases, full control when needed.

> **Install:**
> ```bash
> pip install starstream
> pip install starstream-pocketbase  # For database persistence
> pip install starstream-loro        # For CRDT collaboration
> ```

> **Documentation:** `https://github.com/renatocaliari/starstream`

---

## Quick Start

```python
from starhtml import *
from starstream import StarStreamPlugin

app, rt = star_app()
stream = StarStreamPlugin(app)  # Zero config!

@rt("/chat")
@sse
async def chat(msg: str):
    yield elements(Div(msg), "#chat", "append")
    # Automatically broadcasts to ALL connected clients!
```

---

## Core Concepts

### StarStreamPlugin — Main Entry Point

```python
from starstream import StarStreamPlugin

stream = StarStreamPlugin(
    app,
    enable_presence=True,    # Track online users
    enable_typing=True,      # Typing indicators
    enable_cursors=True,     # Cursor tracking
    enable_history=True,     # Message history
)
```

### Broadcasting Patterns

```python
# Broadcast to all clients
await stream.broadcast_to_topic("global", "Hello everyone!")

# Broadcast to specific room
await stream.broadcast_to_room("room:123", "Room-only message")

# Send to specific user
await stream.send_to_user("user_456", "Private message")
```

### Auto-Detection Convention

Routes automatically detect topics from parameters:

```python
@rt("/room/{room_id}/send")
@sse
async def send(room_id: str, msg: str):
    # Auto-detects topic as "room:{room_id}"
    yield elements(Div(msg), "#chat", "append")
```

---

## Features

### Presence System — Track Online Users

```python
from starstream import Presence

presence = Presence(expire_after=300)  # 5 min timeout
stream.presence = presence

# User joins
await presence.join("room:123", "user_1")
online = await presence.get_online("room:123")  # ["user_1", "user_2"]

# Broadcast presence
await stream.broadcast_to_room("room:123", 
    ('signals', {'online_users': list(online.keys())})
)
```

### Typing Indicators

```python
from starstream import TypingIndicator

typing = TypingIndicator(auto_stop_after=5)  # Stop after 5s
stream.typing = typing

# User starts typing
await typing.start("room:123", "user_1")
typers = typing.get_typing("room:123")  # ["user_1"]
```

### Cursor Tracking

```python
from starstream import CursorTracker

cursors = CursorTracker(throttle_updates=50)  # 50ms throttle
stream.cursors = cursors

# Update cursor
await cursors.update("canvas", "user_1", x=100, y=200)
positions = cursors.get_positions("canvas")  # {"user_1": {"x": 100, "y": 200}}
```

---

## PocketBase Plugin — Persistent Real-time

```python
from starstream_pocketbase import PocketBasePlugin

pb = PocketBasePlugin(
    stream,
    base_url="http://localhost:9090",
    admin_email="admin@example.com",
    admin_password="secret"
)

# Initialize
await pb.authenticate()

# CRUD operations auto-broadcast!
todo = await pb.create("todos", {"title": "Buy milk", "completed": False})
await pb.update("todos", todo_id, {"completed": True})
await pb.delete("todos", todo_id)

# Query
todos = await pb.get_all("todos")
active = await pb.query("todos", 'completed = false', '-created')
```

---

## Loro Plugin — CRDT Collaborative Editing

```python
from starstream_loro import LoroPlugin

loro = LoroPlugin(stream)

# Connect peer to document
await loro.connect("doc_1", "user_1")

# Send/receive deltas
delta = "encoded_delta_bytes"
await loro.receive_delta("doc_1", "user_1", delta)

# Get peers to sync
peers = await loro.get_peers("doc_1", exclude="user_1")
for peer in peers:
    await stream.send_to_user(peer, ('signals', {'delta': delta}))

# Get current state
state = await loro.get_state("doc_1")
```

---

## Integration with StarHTML

### SSE Endpoint with StarStream

```python
@rt("/stream")
async def sse_stream(topic: str = "global"):
    return stream.get_sse_response(topic)
```

### Frontend Connection

```python
def ChatComponent():
    return Container(
        # SSE connection
        stream.get_stream_element(topic="room:123"),
        
        # Messages container
        Div(id="messages"),
        
        # Input with typing indicator
        Input(
            data_star_on("input", 
                "fetch('/typing', {method: 'POST', body: 'user=user_1'})"
            )
        ),
    )
```

---

## Best Practices

1. **Use auto-detection** — Let StarStream detect topics from route parameters
2. **Enable features selectively** — Only enable what you need (presence, typing, etc.)
3. **Handle auth in PocketBase** — Call `pb.authenticate()` on startup
4. **Broadcast after persistence** — Save to DB, then broadcast
5. **Use signals for UI state** — Signals for reactive UI, Python variables for data

---

## Common Patterns

### Multi-room Chat

```python
@rt("/room/{room_id}/send", methods=["POST"])
@sse
async def room_send(room_id: str, msg: str, user: str):
    # Auto-detects topic as "room:{room_id}"
    yield elements(
        Div(f"{user}: {msg}"), 
        f"#room-{room_id}", 
        "append"
    )
```

### Collaborative Document

```python
@rt("/doc/{doc_id}/sync", methods=["POST"])
async def doc_sync(doc_id: str, delta: str, peer_id: str):
    await loro.receive_delta(doc_id, peer_id, delta.encode())
    peers = await loro.get_peers(doc_id, exclude=peer_id)
    for peer in peers:
        await stream.send_to_user(peer, ('signals', {'delta': delta}))
```

---

## Troubleshooting

- **Import errors:** Install `starstream` package: `pip install starstream`
- **Plugin not found:** Install specific plugin: `pip install starstream-pocketbase`
- **No broadcasting:** Check that `starstream_plugin` is properly initialized
- **SSE not connecting:** Ensure `/stream` route is registered

---

## Resources

- **Repository:** `https://github.com/renatocaliari/starstream`
- **Documentation:** See `README.md` in each package
- **Examples:** `examples/` directory in repo
- **Issues:** `https://github.com/renatocaliari/starstream/issues`

---

**Author:** Cali (Renato Caliari)

**License:** MIT

**Contact:** Use [GitHub Issues](https://github.com/renatocaliari/starstream/issues) for questions and support
