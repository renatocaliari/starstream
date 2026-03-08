# Unified Broadcast API Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor StarStreamPlugin to use a single, fire-and-forget broadcast() method that works in SSE handlers.

**Architecture:** Remove schedule_broadcast() and broadcast_exclude(), replace async broadcast() with sync fire-and-forget implementation using asyncio.create_task() internally.

**Tech Stack:** Python 3.10+, asyncio, pytest, StarHTML/Starlette

---

## Task 1: Remove schedule_broadcast() method

**Files:**
- Modify: `packages/starstream/starstream/plugin.py:306-341`
- Delete: `packages/starstream/tests/test_schedule_broadcast.py`

**Step 1: Delete schedule_broadcast() method**

Remove lines 306-341 in `packages/starstream/starstream/plugin.py`:

```python
# DELETE THIS ENTIRE METHOD:
def schedule_broadcast(
    self,
    background,
    message: Union[str, Tuple],
    target: Union[str, Dict, None] = None,
):
    """
    Schedule broadcast for execution after SSE response.
    ...
    """
    topic = self._resolve_target(target)
    background.add_task(self._do_broadcast_safe, message, topic)
```

**Step 2: Delete test_schedule_broadcast.py**

```bash
rm packages/starstream/tests/test_schedule_broadcast.py
```

**Step 3: Verify tests still pass**

Run: `cd packages/starstream && python3 -m pytest tests/ -v --ignore=tests/test_e2e.py -k "not schedule_broadcast"`
Expected: All tests pass

**Step 4: Commit**

```bash
git add packages/starstream/starstream/plugin.py packages/starstream/tests/test_schedule_broadcast.py
git commit -m "refactor: remove schedule_broadcast() method"
```

---

## Task 2: Remove broadcast_exclude() method

**Files:**
- Modify: `packages/starstream/starstream/plugin.py:265-274`

**Step 1: Delete broadcast_exclude() method**

Remove lines 265-274 in `packages/starstream/starstream/plugin.py`:

```python
# DELETE THIS ENTIRE METHOD:
async def broadcast_exclude(
    self,
    exclude_user_ids: List[str],
    message: Union[str, Tuple],
    topic: str = "global",
):
    """Broadcast to all except specific users."""
    # In a real implementation, we'd track user subscriptions
    # For now, this is a placeholder
    await self.core.broadcast(message, topic=topic)
```

**Step 2: Verify tests still pass**

Run: `cd packages/starstream && python3 -m pytest tests/ -v --ignore=tests/test_e2e.py`
Expected: All tests pass

**Step 3: Commit**

```bash
git add packages/starstream/starstream/plugin.py
git commit -m "refactor: remove broadcast_exclude() method"
```

---

## Task 3: Rewrite broadcast() as fire-and-forget sync

**Files:**
- Modify: `packages/starstream/starstream/plugin.py:215-263`

**Step 1: Write new broadcast() implementation**

Replace the async broadcast() method (lines 215-263) with:

```python
def broadcast(
    self,
    message: Union[str, Tuple],
    target: Union[str, Dict, None] = None,
):
    """
    Fire-and-forget broadcast to subscribers.
    
    Broadcasts are inherently fire-and-forget (pub/sub semantics).
    Use metrics or logs for observability.
    
    Args:
        message: str, tuple, or StarHTML elements
        target: str, dict, or None
    
    Example:
        @rt("/todos/add", methods=["POST"])
        @sse
        def add_todo(text: str):
            stream.broadcast(elements(...), target="todos")
            yield elements(...)
    """
    topic = self._resolve_target(target)
    
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(self._do_broadcast_safe(message, topic))
    except RuntimeError:
        asyncio.run(self._do_broadcast_safe(message, topic))
```

**Step 2: Verify tests still pass**

Run: `cd packages/starstream && python3 -m pytest tests/ -v --ignore=tests/test_e2e.py`
Expected: All tests pass

**Step 3: Commit**

```bash
git add packages/starstream/starstream/plugin.py
git commit -m "refactor: make broadcast() fire-and-forget sync"
```

---

## Task 4: Create test_broadcast_unified.py

**Files:**
- Create: `packages/starstream/tests/test_broadcast_unified.py`

**Step 1: Write test file**

```python
import asyncio
import pytest
from unittest.mock import Mock, patch
from starstream.plugin import StarStreamPlugin


def test_broadcast_in_sync_context():
    """Test broadcast() works in sync context (SSE handler)."""
    app = Mock()
    plugin = StarStreamPlugin(app)
    
    # Should not raise
    plugin.broadcast("test message", target="chat")


def test_broadcast_in_async_context():
    """Test broadcast() works in async context."""
    app = Mock()
    plugin = StarStreamPlugin(app)
    
    async def test():
        plugin.broadcast("test message", target="chat")
        await asyncio.sleep(0.01)  # Let task execute
    
    # Should not raise
    asyncio.run(test())


def test_broadcast_without_event_loop():
    """Test broadcast() when no event loop exists (edge case)."""
    app = Mock()
    plugin = StarStreamPlugin(app)
    
    # Ensure no event loop is running
    with patch('asyncio.get_running_loop', side_effect=RuntimeError("No loop")):
        plugin.broadcast("test message", target="chat")


def test_broadcast_with_string_target():
    """Test broadcast with string target."""
    app = Mock()
    plugin = StarStreamPlugin(app)
    
    plugin.broadcast("msg", target="todos")


def test_broadcast_with_dict_target():
    """Test broadcast with dict target."""
    app = Mock()
    plugin = StarStreamPlugin(app)
    
    plugin.broadcast("msg", target={"type": "room", "id": "123"})


def test_broadcast_with_none_target():
    """Test broadcast with None target uses default."""
    app = Mock()
    plugin = StarStreamPlugin(app, default_topic="my_default")
    
    plugin.broadcast("msg", target=None)


def test_broadcast_with_tuple_message():
    """Test broadcast with tuple message (Datastar format)."""
    app = Mock()
    plugin = StarStreamPlugin(app)
    
    plugin.broadcast(("elements", ("<div>test</div>", "#app")), target="test")
```

**Step 2: Run tests to verify they pass**

Run: `cd packages/starstream && python3 -m pytest tests/test_broadcast_unified.py -v`
Expected: All tests pass

**Step 3: Commit**

```bash
git add packages/starstream/tests/test_broadcast_unified.py
git commit -m "test: add unified broadcast tests"
```

---

## Task 5: Update todo_broadcast.py example

**Files:**
- Modify: `packages/starstream/examples/todo_broadcast.py`

**Step 1: Remove BackgroundTasks imports and parameters**

Change line 12:
```python
# REMOVE THIS:
from starlette.background import BackgroundTasks
```

**Step 2: Update add_todo handler**

Replace lines 72-90:
```python
@rt("/todos/add", methods=["POST"])
@sse
def add_todo(text: str):
    """Add todo with broadcast to all clients."""
    import uuid
    
    todo_id = str(uuid.uuid4())[:8]
    todos.append({"id": todo_id, "text": text, "completed": False})
    
    # Broadcast to all clients (simplified!)
    stream.broadcast(
        elements(render_todo_list(), "#todo-list"),
        target="todos"
    )
    
    yield elements(render_todo_list(), "#todo-list")
    yield signals(text="")
```

**Step 3: Update toggle_todo handler**

Replace lines 93-109:
```python
@rt("/todos/{todo_id}/toggle", methods=["POST"])
@sse
def toggle_todo(todo_id: str):
    """Toggle todo with broadcast."""
    for todo in todos:
        if todo["id"] == todo_id:
            todo["completed"] = not todo["completed"]
            break
    
    stream.broadcast(
        elements(render_todo_list(), "#todo-list"),
        target="todos"
    )
    
    yield elements(render_todo_list(), "#todo-list")
    yield signals()
```

**Step 4: Update delete_todo handler**

Replace lines 112-126:
```python
@rt("/todos/{todo_id}/delete", methods=["POST"])
@sse
def delete_todo(todo_id: str):
    """Delete todo with broadcast."""
    global todos
    todos = [t for t in todos if t["id"] != todo_id]
    
    stream.broadcast(
        elements(render_todo_list(), "#todo-list"),
        target="todos"
    )
    
    yield elements(render_todo_list(), "#todo-list")
    yield signals()
```

**Step 5: Verify example runs**

Run: `cd packages/starstream && python examples/todo_broadcast.py &`
Expected: Server starts on port 8000
Kill: `pkill -f todo_broadcast.py`

**Step 6: Commit**

```bash
git add packages/starstream/examples/todo_broadcast.py
git commit -m "refactor: update todo_broadcast example to use new broadcast API"
```

---

## Task 6: Update README.md

**Files:**
- Modify: `packages/starstream/README.md`

**Step 1: Update broadcasting section**

Find the broadcasting examples and replace with:

```markdown
## Broadcasting

Fire-and-forget broadcast to all subscribers:

```python
@rt("/todos/add", methods=["POST"])
@sse
def add_todo(text: str):
    todos.append(text)
    
    # Broadcast to all clients
    stream.broadcast(
        elements(render_todos(), "#todo-list"),
        target="todos"
    )
    
    yield elements(render_todos(), "#todo-list")
```

### Targets

```python
# Topic
stream.broadcast(msg, target="chat")

# Room
stream.broadcast(msg, target="room:123")

# User
stream.broadcast(msg, target="user:456")

# Default (global)
stream.broadcast(msg)
```

### Observability

```python
# Metrics
stats = stream.get_metrics("todos")
# {"success": 42, "error": 0, "avg_latency_ms": 1.23}

# Error handling
stream.set_error_hook(lambda topic, msg, err: logger.error(f"{topic}: {err}"))
```
```

**Step 2: Commit**

```bash
git add packages/starstream/README.md
git commit -m "docs: update README with new broadcast API"
```

---

## Task 7: Update skills/starstream/SKILL.md

**Files:**
- Modify: `skills/starstream/SKILL.md`

**Step 1: Add broadcasting section**

Add after line 34:

```markdown
## Broadcasting

Fire-and-forget broadcast to all connected clients:

```python
@rt("/todos/add", methods=["POST"])
@sse
def add_todo(text: str):
    todos.append(text)
    
    # Broadcast to all clients
    stream.broadcast(
        elements(render_todos(), "#todo-list"),
        target="todos"
    )
    
    # Response to current client
    yield elements(render_todos(), "#todo-list")
```

### Targets

```python
# Topic
stream.broadcast(msg, target="chat")

# Room
stream.broadcast(msg, target="room:123")

# User
stream.broadcast(msg, target="user:456")

# Default (global)
stream.broadcast(msg)
```

### Observability

```python
# Metrics
stats = stream.get_metrics("todos")

# Error handling
stream.set_error_hook(lambda topic, msg, err: logger.error(f"{topic}: {err}"))
```
```

**Step 2: Commit**

```bash
git add skills/starstream/SKILL.md
git commit -m "docs: update skill with new broadcast API"
```

---

## Task 8: Update skills/starstream/REFERENCE.md

**Files:**
- Modify: `skills/starstream/REFERENCE.md`

**Step 1: Update API Reference section**

Replace lines 7-13 with:

```markdown
## API Reference

### StarStreamPlugin

#### Methods

**`broadcast(message, target=None)`**
Fire-and-forget broadcast to subscribers. Works in SSE handlers.
- `message`: str, tuple, or StarHTML elements
- `target`: str, dict, or None (uses default_topic)

**`get_stream_element(topic)`**
Returns Div element with SSE connection for frontend.
- `topic`: str or list[str]

**`get_metrics(topic=None)`**
Returns broadcast statistics.

**`set_error_hook(hook)`**
Sets callback for broadcast errors.

#### Initialization Parameters

- `app`: StarHTML app instance
- `default_topic`: str (default: "global")
- `enable_presence`: bool
- `enable_typing`: bool
- `enable_cursors`: bool
- `enable_history`: bool
```

**Step 2: Commit**

```bash
git add skills/starstream/REFERENCE.md
git commit -m "docs: update reference with new broadcast API"
```

---

## Task 9: Run full test suite

**Step 1: Run all tests**

Run: `cd packages/starstream && python3 -m pytest tests/ -v --ignore=tests/test_e2e.py`
Expected: All tests pass

**Step 2: Fix any failures**

If tests fail, debug and fix before proceeding.

**Step 3: Commit (if fixes needed)**

```bash
git add .
git commit -m "fix: resolve test failures"
```

---

## Task 10: Update STATUS.md

**Files:**
- Modify: `STATUS.md`

**Step 1: Add changelog entry**

Add after line 60:

```markdown
## Changelog

### v0.3.0 (2025-03-08)

**Breaking Changes:**
- Removed `schedule_broadcast()` - use `broadcast()` directly
- Removed `broadcast_exclude()` - not implemented
- Changed `broadcast()` from async to sync (fire-and-forget)

**Improvements:**
- Simplified API: one method for all broadcasting
- No dependency on BackgroundTasks injection
- Works seamlessly in SSE handlers
```

**Step 2: Commit**

```bash
git add STATUS.md
git commit -m "docs: update STATUS with v0.3.0 changelog"
```

---

## Final Verification

**Step 1: Run full test suite**

```bash
cd packages/starstream && python3 -m pytest tests/ -v --ignore=tests/test_e2e.py
```

Expected: All tests pass

**Step 2: Verify example works**

```bash
cd packages/starstream && python examples/todo_broadcast.py &
# Open browser to http://localhost:8000
# Test adding/deleting todos
pkill -f todo_broadcast.py
```

**Step 3: Final commit**

```bash
git add .
git commit -m "refactor: complete unified broadcast API implementation"
```

---

## Success Criteria

- [ ] All tests pass
- [ ] Example runs without errors
- [ ] Documentation updated
- [ ] No BackgroundTasks dependency in examples
- [ ] Fire-and-forget broadcast works in SSE handlers
- [ ] API is simpler (fewer methods)