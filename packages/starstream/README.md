# StarStream Core

Zero-config real-time broadcasting for StarHTML applications.

## Installation

```bash
pip install starstream
```

## Quick Start

```python
from starhtml import *
from starstream import StarStreamPlugin

app, rt = star_app()
stream = StarStreamPlugin(app)

@rt("/chat")
@sse
async def chat(msg: str):
    yield elements(Div(msg), "#chat", "append")
```

## Features

- **Zero-config broadcasting** - Works out of the box
- **Auto-detection** - Automatic topic/room detection
- **Presence system** - Track online users
- **Typing indicators** - Show who's typing
- **Cursor tracking** - Real-time cursor positions
- **Message history** - Store and retrieve history

## API Reference

### StarStreamPlugin

```python
from starstream import StarStreamPlugin

stream = StarStreamPlugin(
    app,
    enable_presence=True,
    enable_typing=True,
    enable_cursors=True,
    enable_history=True
)
```

### Broadcasting

```python
# Broadcast to all clients
await stream.broadcast_to_topic("global", "Hello!")

# Broadcast to room
await stream.broadcast_to_room("room1", "Room message")

# Send to specific user
await stream.send_to_user("user1", "Private message")
```

## License

MIT
