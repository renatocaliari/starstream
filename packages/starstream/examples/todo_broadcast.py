"""
StarStream SSE Broadcast Example - Todo List

Demonstrates how to use schedule_broadcast in SSE handlers
for real-time sync between multiple clients.

Run: python examples/todo_broadcast.py
Open: http://localhost:8000
"""
from starhtml import *
from starstream import StarStreamPlugin
from starlette.background import BackgroundTasks


app, rt = star_app()
stream = StarStreamPlugin(app)


# In-memory todo storage
todos = [
    {"id": "1", "text": "Learn StarStream", "completed": False},
    {"id": "2", "text": "Build something awesome", "completed": True},
]


def render_todo_list():
    """Render the todo list UI."""
    items = []
    for todo in todos:
        items.append(
            Div(
                Input(
                    type="checkbox",
                    checked=todo["completed"],
                    data_on_click=f"/todos/{todo['id']}/toggle"
                ),
                Span(todo["text"], 
                     cls="ml-2" if not todo["completed"] else "ml-2 line-through"),
                Button("×", 
                       data_on_click=f"/todos/{todo['id']}/delete",
                       cls="ml-2 text-red-500"),
                cls="flex items-center p-2"
            )
        )
    return Div(
        *items,
        id="todo-list",
        cls="space-y-2"
    )


@rt("/")
def home():
    return Div(
        H1("StarStream Todo Demo", cls="text-2xl font-bold mb-4"),
        stream.get_stream_element("todos"),  # Auto-connect to broadcast
        render_todo_list(),
        Form(
            Input(
                name="text",
                placeholder="Add todo...",
                cls="border p-2 rounded"
            ),
            Button("Add", type="submit", cls="ml-2 p-2 bg-blue-500 text-white rounded"),
            data_onsubmit="post:/todos/add",
            cls="flex mb-4"
        ),
        cls="max-w-md mx-auto mt-8 p-4"
    )


@rt("/todos/add", methods=["POST"])
@sse
def add_todo(text: str, background: BackgroundTasks):
    """Add todo with broadcast to all clients."""
    import uuid
    
    todo_id = str(uuid.uuid4())[:8]
    todos.append({"id": todo_id, "text": text, "completed": False})
    
    # Schedule broadcast for other clients
    stream.schedule_broadcast(
        background,
        elements(render_todo_list(), "#todo-list"),
        target="todos"
    )
    
    # Response to current client
    yield elements(render_todo_list(), "#todo-list")
    yield signals(text="")


@rt("/todos/{todo_id}/toggle", methods=["POST"])
@sse
def toggle_todo(todo_id: str, background: BackgroundTasks):
    """Toggle todo with broadcast."""
    for todo in todos:
        if todo["id"] == todo_id:
            todo["completed"] = not todo["completed"]
            break
    
    stream.schedule_broadcast(
        background,
        elements(render_todo_list(), "#todo-list"),
        target="todos"
    )
    
    yield elements(render_todo_list(), "#todo-list")
    yield signals()


@rt("/todos/{todo_id}/delete", methods=["POST"])
@sse
def delete_todo(todo_id: str, background: BackgroundTasks):
    """Delete todo with broadcast."""
    global todos
    todos = [t for t in todos if t["id"] != todo_id]
    
    stream.schedule_broadcast(
        background,
        elements(render_todo_list(), "#todo-list"),
        target="todos"
    )
    
    yield elements(render_todo_list(), "#todo-list")
    yield signals()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    port=8000)
