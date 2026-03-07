# StarStream-PocketBase

**PocketBase integration for StarStream - Real-time database with automatic broadcasting**

This plugin seamlessly integrates [PocketBase](https://pocketbase.io) with StarStream, enabling automatic real-time synchronization between your database and connected clients.

## Why PocketBase?

**PocketBase** is an open-source backend solution that provides:
- ✅ **One-file** - Single executable, no dependencies
- ✅ **Self-hosted** - You own your data
- ✅ **Real-time** - Built-in SSE subscriptions
- ✅ **File storage** - Built-in media handling
- ✅ **Authentication** - Users & OAuth out of the box
- ✅ **Admin UI** - Beautiful dashboard included

Unlike Supabase/Convex which push you toward SaaS, PocketBase is **truly open-source** and self-hostable.

## Installation

```bash
pip install starstream-pocketbase
```

## Quick Start

```python
from starhtml import *
from starstream import StarStreamPlugin
from starstream_pocketbase import PocketBasePlugin

app, rt = star_app()
stream = StarStreamPlugin(app)

# Initialize PocketBase plugin
pb = PocketBasePlugin(
    stream,
    base_url="http://localhost:9090",
    admin_email="admin@example.com",
    admin_password="secret"
)

@app.on_event("startup")
async def startup():
    # Authenticate with PocketBase
    await pb.authenticate()

@rt("/todos", methods=["POST"])
async def create_todo(title: str):
    """Creates in PocketBase + broadcasts to all clients!"""
    todo = await pb.create("todos", {
        "title": title,
        "completed": False
    })
    return todo

@rt("/todos/{todo_id}", methods=["PATCH"])
async def update_todo(todo_id: str, completed: bool):
    """Updates PocketBase + broadcasts!"""
    return await pb.update("todos", todo_id, {"completed": completed})

@rt("/todos")
async def list_todos():
    """Get all todos from PocketBase"""
    return await pb.get_all("todos")
```

## Architecture

```
┌──────────────────────────────────────────────┐
│           StarStream (Broadcast Layer)       │
│   - SSE real-time to all clients             │
│   - Presence, Typing, Cursors                │
└───────────────┬──────────────────────────────┘
                │
┌───────────────▼──────────────────────────────┐
│        PocketBasePlugin                      │
│   - Auto-broadcast on CRUD                   │
│   - Sync management                          │
└───────────────┬──────────────────────────────┘
                │
┌───────────────▼──────────────────────────────┐
│        PocketBase Database                   │
│   - REST API                                 │
│   - Real-time subscriptions                  │
│   - File storage                             │
└──────────────────────────────────────────────┘
```

## Features

- ✅ **Automatic broadcasting** - Changes sync to all clients instantly
- ✅ **CRUD operations** - Create, Read, Update, Delete with one line
- ✅ **Real-time subscriptions** - Listen to collection changes
- ✅ **Query support** - Filter and sort with PocketBase syntax
- ✅ **Type hints** - Full type support
- ✅ **StarStream integration** - Works with presence, typing, cursors

## API Reference

### PocketBasePlugin

```python
from starstream_pocketbase import PocketBasePlugin

pb = PocketBasePlugin(
    stream_plugin,                    # StarStreamPlugin instance
    base_url="http://localhost:9090", # PocketBase URL
    admin_email="admin@example.com",  # Admin credentials
    admin_password="secret"
)

# Authenticate
await pb.authenticate()

# CRUD Operations
todo = await pb.create("todos", {"title": "Buy milk"})
await pb.update("todos", todo_id, {"completed": True})
await pb.delete("todos", todo_id)
todos = await pb.get_all("todos")
todo = await pb.get_one("todos", todo_id)

# Query
active = await pb.query("todos", 'completed = false', '-created')

# Subscribe to changes
await pb.subscribe("todos", lambda action, record: print(f"{action}: {record}"))
```

### Storage Layer

For lower-level access:

```python
from starstream_pocketbase import PocketBaseStorage

storage = PocketBaseStorage("http://localhost:9090")
await storage.authenticate("admin@example.com", "password")

# Store data
await storage.set("todos", {"title": "New todo"})

# Retrieve
todos = await storage.get_all("todos")
```

### Sync Layer

For fine-grained control:

```python
from starstream_pocketbase import PocketBaseSync

sync = PocketBaseSync(pb_client, stream_plugin)

# Create with optional broadcast
record = await sync.create("todos", data, broadcast=True)
```

## Example: Real-time Todo App

```python
from starhtml import *
from starstream import StarStreamPlugin
from starstream_pocketbase import PocketBasePlugin

app, rt = star_app()
stream = StarStreamPlugin(app)
pb = PocketBasePlugin(stream, "http://localhost:9090")

@app.on_event("startup")
async def startup():
    await pb.authenticate("admin@example.com", "Adminpassword123!")

@rt("/todos")
def todo_page():
    return Container(
        stream.get_stream_element(topic="todos"),
        
        H1("Real-time Todos"),
        
        # Todo list (auto-updates via SSE)
        Div(
            id="todo-list",
            data_star_on("load", "fetch('/todos/list').then(r => r.json()).then(data => this.innerHTML = renderTodos(data))"),
            data_star_signals={"todos": []}
        ),
        
        # Add todo form
        Form(
            Input(name="title", placeholder="New todo..."),
            Button("Add", type="submit"),
            data_on_submit=post("/todos/add")
        )
    )

@rt("/todos/list")
async def list_todos():
    return await pb.get_all("todos")

@rt("/todos/add", methods=["POST"])
async def add_todo(title: str):
    # Creates in PocketBase + broadcasts to all!
    return await pb.create("todos", {
        "title": title,
        "completed": False
    })

@rt("/todos/{todo_id}/toggle", methods=["POST"])
async def toggle_todo(todo_id: str, completed: bool):
    return await pb.update("todos", todo_id, {"completed": completed})
```

## PocketBase Setup

1. Download PocketBase:
   ```bash
   wget https://github.com/pocketbase/pocketbase/releases/latest/download/pocketbase_linux_amd64.zip
   unzip pocketbase_linux_amd64.zip
   ```

2. Start PocketBase:
   ```bash
   ./pocketbase serve
   ```

3. Open admin UI at `http://localhost:8090/_/`

4. Create collections (e.g., "todos") in the admin UI

5. Use the plugin!

## Storage Priority

```
1. SQLite (default) - Local development
2. PocketBase (via this plugin) - Shared state with persistence
3. PostgreSQL (future) - Enterprise scale
```

## Comparison

| Feature | SQLite | PocketBase | PostgreSQL |
|---------|--------|------------|------------|
| Setup | Zero | Single binary | Complex |
| Persistence | ✅ File | ✅ Database | ✅ Database |
| Real-time | Via StarStream | Via StarStream | Via StarStream |
| Self-hosted | ✅ | ✅ | ✅ |
| Admin UI | ❌ | ✅ | Partial |
| Auth | Manual | Built-in | Manual |
| File Storage | ❌ | ✅ | ❌ |

## Integration with Other Features

Works seamlessly with all StarStream features:

```python
# Presence + PocketBase
stream = StarStreamPlugin(app, enable_presence=True)
pb = PocketBasePlugin(stream)

@rt("/todos")
async def get_todos():
    # Track who's viewing
    await stream.presence.join("todos", user_id)
    # Get data from PocketBase
    return await pb.get_all("todos")
```

## License

MIT
