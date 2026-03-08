# StarStream Reference

Detailed API and plugin information for StarStream.

## Plugin API Details

### StarStreamPlugin (Core)

The main entry point for real-time broadcasting.

**Initialization:**
```python
StarStreamPlugin(
    app,                    # StarHTML app instance
    default_topic="global", # Default topic for broadcasts
    enable_presence=False,  # Track online users
    enable_typing=False,    # Show who's typing
    enable_cursors=False,   # Track mouse positions
    enable_history=False,   # Store message history
    storage=None,           # SQLite backend (auto if True)
)
```

**Methods:**

- `broadcast(message, target=None)` - Fire-and-forget broadcast
  - `message`: str, tuple, or StarHTML elements
  - `target`: str ("chat"), dict ({"type": "room", "id": "123"}), or None

- `get_stream_element(topic)` - Returns Div element with SSE connection
- `get_stream_url(topic)` - Returns SSE endpoint URL
- `get_metrics(topic=None)` - Returns broadcast statistics
- `set_error_hook(hook)` - Sets callback for broadcast errors
- `configure(...)` - Decorator for custom broadcast config

### Storage

SQLite is the default backend when storage is enabled:

```python
# Automatic SQLite storage
stream = StarStreamPlugin(app, enable_history=True)  # SQLite auto-created

# Custom SQLite path
from starstream.storage import SQLiteBackend
stream = StarStreamPlugin(app, storage=SQLiteBackend("custom.db"))
```

For PocketBase (auth, admin UI, files), see `starstream-pocketbase` plugin.

### PocketBase Plugin

Used for persistent real-time database sync with auth and admin UI.
```python
from starstream_pocketbase import PocketBasePlugin
pb = PocketBasePlugin(stream, base_url="http://localhost:8090")
await pb.authenticate(email, password)
```

### Loro Plugin

Used for CRDT-based conflict-free collaborative editing.
```python
from starstream_loro import LoroPlugin
loro = LoroPlugin(stream)
```

## Conventions

Refer to `starstream/conventions.py` for full details.
- `{room_id}` parameters are automatically detected as topics in the format `room:{id}`.
- `{user_id}` parameters are detected for private user-specific topics.

## Troubleshooting

- **No updates?** Check if the client is connected to `/stream?topic=...`.
- **Wrong topic?** Verify route parameter names.
- **Performance lag?** Cursor updates are throttled to 50ms by default.
