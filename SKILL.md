---
name: building-realtime-starhtml-apps
description: Adds real-time broadcasting, multi-user collaboration, and database persistence to StarHTML applications. Use when implementing chat systems, collaborative editors, presence tracking, typing indicators, or any feature requiring synchronized state across clients. Supports core StarStream (broadcasting), PocketBase (persistence), and Loro (CRDT) plugins.
---

# Building Real-time StarHTML Apps

StarStream provides a "convention over configuration" approach to real-time features in StarHTML. Follow these instructions to implement synchronized user experiences.

## Core Integration Strategy

When tasked with adding real-time features, always follow this workflow:

1.  **Identify Features**: Determine if the app needs simple broadcasting, persistence (PocketBase), or conflict-free editing (Loro).
2.  **Initialize Core**: Add `StarStreamPlugin(app)` to the main application file.
3.  **Enable Modules**: Toggle `enable_presence`, `enable_typing`, `enable_cursor`, or `enable_history` as needed.
4.  **Register SSE**: Ensure a `/stream` route exists to provide the EventSource connection.
5.  **Emit Events**: Use `yield elements(...)` in `@sse` routes to auto-broadcast UI updates.

### Basic Initialization
```python
from starhtml import *
from starstream import StarStreamPlugin

app, rt = star_app()
# Use defaults for auto-detection of topics via route parameters
stream = StarStreamPlugin(app, enable_presence=True, enable_typing=True)

@rt("/chat/{room_id}")
@sse
async def chat(room_id: str, msg: str):
    # Auto-broadcasts to topic "room:{room_id}"
    yield elements(Div(msg), "#messages", "append")
```

## Plugin Selection Guide

| Plugin | Use Case | Implementation File |
| :--- | :--- | :--- |
| **StarStreamCore** | Simple broadcasting, ephemeral state. | `starstream/plugin.py` |
| **PocketBase** | Persistent data with real-time sync. | `starstream_pocketbase/plugin.py` |
| **Loro** | Multi-user document editing (CRDT). | `starstream_loro/plugin.py` |

### Using PocketBase for Persistence
```python
from starstream_pocketbase import PocketBasePlugin

pb = PocketBasePlugin(stream, base_url="http://localhost:8090")
await pb.authenticate(email, password)

# CRUD operations auto-broadcast to relevant topics
await pb.create("messages", {"text": "Hello", "room": room_id})
```

### Using Loro for Collaborative Editing
```python
from starstream_loro import LoroPlugin

loro = LoroPlugin(stream)
# Connect to a shared document
await loro.connect(doc_id, user_id)
# Sync deltas across peers
await loro.receive_delta(doc_id, user_id, delta_bytes)
```

## Implementation Checklist

- [ ] `StarStreamPlugin` initialized with `app`.
- [ ] SSE endpoint `/stream` registered: `app.route("/stream")(stream.get_sse_response)`.
- [ ] Frontend uses `stream.get_stream_element(topic)`.
- [ ] Route parameters match topic conventions (e.g., `{room_id}` -> `room:{id}`).
- [ ] (Optional) Presence/Typing heartbeats implemented in frontend.
- [ ] (Optional) Rate limiting applied for high-frequency updates (cursors).

## Validation & Testing

Always validate the real-time implementation using the provided test suite or by running an example:

```bash
# Run core tests
pytest tests/test_core.py tests/test_presence.py

# Verify with a live example
python examples/full_features.py
```

### Common Debugging Steps
- **No updates?** Check if the client is connected to `/stream?topic=...`.
- **Wrong topic?** Verify `StarStreamPlugin`'s `topic_detector` logic in `conventions.py`.
- **Performance lag?** Ensure `CursorTracker` is throttled (default 50ms).

## Resources & Progressive Disclosure

- **Architecture**: See `starstream/plugin.py` for core logic.
- **Conventions**: Refer to `starstream/conventions.py` for topic detection rules.
- **Full Demo**: `examples/full_features.py` shows all features integrated.
- **API Reference**: Read `starstream/__init__.py` for available exports.
