# StarStream PocketBase

**PocketBase Integration for StarStream**

Real-time data persistence with automatic broadcasting on CRUD operations.

## Installation

```bash
pip install starstream-pocketbase
```

## 🛠 AI Agent Skills

StarStream includes a `SKILL.md` for AI agents. This skill provides expert instructions for building real-time apps.
Agents can install it via:

```bash
npx skills add renatocaliari/starstream
```

## Features

- Database storage backend
- Auto-broadcast on CRUD operations
- Real-time sync
- Query support (filter, sort)
- Admin authentication

## Quick Start

```python
from starhtml import *
from starstream import StarStreamPlugin
from starstream_pocketbase import PocketBasePlugin

app, rt = star_app()
stream = StarStreamPlugin(app)
pb = PocketBasePlugin(stream, "http://localhost:8090")

@rt("/todos/create", methods=["POST"])
async def create_todo(title: str):
    todo = await pb.create("todos", {"title": title})
    # Auto-broadcasts to all clients!
```

## License

MIT