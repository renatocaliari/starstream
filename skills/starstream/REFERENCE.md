# StarStream Reference

Detailed API and plugin information for StarStream.

## Plugin API Details

### StarStreamPlugin (Core)
The main entry point for real-time broadcasting.
- `app`: StarHTML application instance.
- `enable_presence`: Boolean (default False).
- `enable_typing`: Boolean (default False).
- `enable_cursor`: Boolean (default False).
- `enable_history`: Boolean (default False).

### PocketBase Plugin
Used for persistent real-time database sync.
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
