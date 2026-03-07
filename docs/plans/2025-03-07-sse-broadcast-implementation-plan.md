# StarStream + SSE Broadcast Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implementar a integração StarStream + SSE usando BackgroundTasks, com métricas, error handling e API simplificada.

**Architecture:** Usar Starlette BackgroundTasks para agendar broadcast após resposta SSE. Separar StarStreamCore em módulo próprio. Adicionar BroadcastMetrics para observabilidade.

**Tech Stack:** Python, Starlette, asyncio, Datastar (SSE)

---

## Pré-requisitos

1. Verificar que BackgroundTasks está disponível no Starlette (sempre está)
2. Criar branch de trabalho para implementar as mudanças
3. Executar testes existentes para ter baseline

---

## Task 1: Criar BroadcastMetrics (metrics.py)

**Files:**
- Create: `/Users/cali/Development/starstream-monorepo/packages/starstream/starstream/metrics.py`
- Test: `/Users/cali/Development/starstream-monorepo/packages/starstream/tests/test_metrics.py`

**Step 1: Write the failing test**

```python
# tests/test_metrics.py
import pytest
from starstream.metrics import BroadcastMetrics

def test_metrics_initial_state():
    metrics = BroadcastMetrics()
    stats = metrics.get_stats()
    
    assert stats["success"] == 0
    assert stats["error"] == 0

def test_metrics_record_success():
    metrics = BroadcastMetrics()
    metrics.record_success(0.050)  # 50ms
    
    stats = metrics.get_stats()
    assert stats["success"] == 1
    assert stats["avg_latency_ms"] == 50.0

def test_metrics_record_error():
    metrics = BroadcastMetrics()
    metrics.record_error()
    
    stats = metrics.get_stats()
    assert stats["error"] == 1

def test_metrics_p95_latency():
    metrics = BroadcastMetrics()
    
    # Record 20 samples with increasing latency
    for i in range(20):
        metrics.record_success(i * 0.01)  # 0ms to 190ms
    
    stats = metrics.get_stats()
    # p95 of 0-190ms should be around 180ms
    assert stats["p95_latency_ms"] is not None
    assert stats["p95_latency_ms"] > 150
```

**Step 2: Run test to verify it fails**

```bash
cd /Users/cali/Development/starstream-monorepo/packages/starstream
python -m pytest tests/test_metrics.py -v
```

Expected: FAIL - "No module named 'starstream.metrics'"

**Step 3: Write minimal implementation**

```python
# starstream/metrics.py
"""
Broadcast metrics for monitoring and observability.
"""
from dataclasses import dataclass, field
from collections import deque


@dataclass
class BroadcastMetrics:
    """
    Simple metrics for broadcast operations.
    
    Tracks success/error counts and latency samples.
    KISS design: only essential metrics.
    """
    success_count: int = 0
    error_count: int = 0
    latency_samples: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def record_success(self, latency: float):
        """Record successful broadcast with latency in seconds."""
        self.success_count += 1
        self.latency_samples.append(latency)
    
    def record_error(self):
        """Record broadcast error."""
        self.error_count += 1
    
    def get_stats(self) -> dict:
        """Return statistics dictionary."""
        if not self.latency_samples:
            return {"success": self.success_count, "error": self.error_count}
        
        sorted_latencies = sorted(self.latency_samples)
        n = len(sorted_latencies)
        
        stats = {
            "success": self.success_count,
            "error": self.error_count,
            "avg_latency_ms": round(sum(sorted_latencies) / n * 1000, 2),
        }
        
        if n >= 20:
            stats["p95_latency_ms"] = round(sorted_latencies[int(n * 0.95)] * 1000, 2)
        
        return stats
```

**Step 4: Run test to verify it passes**

```bash
cd /Users/cali/Development/starstream-monorepo/packages/starstream
python -m pytest tests/test_metrics.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add starstream/metrics.py tests/test_metrics.py
git commit -m "feat: add BroadcastMetrics for observability"
```

---

## Task 2: Criar StarStreamCore em core.py

**Files:**
- Create: `/Users/cali/Development/starstream-monorepo/packages/starstream/starstream/core.py`
- Modify: `/Users/cali/Development/starstream-monorepo/packages/starstream/starstream/plugin.py` (atualizar imports)
- Test: `/Users/cali/Development/starstream-monorepo/packages/starstream/tests/test_core.py`

**Step 1: Write the failing test**

```python
# tests/test_core.py
import pytest
import asyncio
from starstream.core import StarStreamCore

@pytest.fixture
def core():
    return StarStreamCore()

def test_core_initialization(core):
    """Test core initializes with empty topics."""
    assert core._topics == {}
    assert core._user_topics == {}

@pytest.mark.asyncio
async def test_subscribe_and_receive(core):
    """Test subscribing to a topic and receiving messages."""
    messages = []
    
    async def consumer():
        async for msg in core.subscribe("test"):
            messages.append(msg)
            break  # Only need one message
    
    # Start consumer
    consumer_task = asyncio.create_task(consumer())
    
    # Give it time to subscribe
    await asyncio.sleep(0.01)
    
    # Broadcast a message
    await core.broadcast("hello", "test")
    
    # Wait for consumer to receive
    await asyncio.sleep(0.01)
    
    assert "hello" in str(messages)

@pytest.mark.asyncio
async def test_broadcast_formats_sse(core):
    """Test broadcast formats message correctly for SSE."""
    await core.broadcast(("elements", ("<div>test</div>", "#app")), "test")
    
    messages = []
    async for msg in core.subscribe("test"):
        messages.append(msg)
        break
    
    assert "event: datastar-patch-elements" in msg
    assert "data: elements <div>test</div>" in msg
    assert "data: selector #app" in msg
```

**Step 2: Run test to verify it fails**

```bash
cd /Users/cali/Development/starstream-monorepo/packages/starstream
python -m pytest tests/test_core.py -v
```

Expected: FAIL - "No module named 'starstream.core'"

**Step 3: Write minimal implementation**

```python
# starstream/core.py
"""
StarStream Core - Broadcast Engine.

Separated from plugin for testability and clean architecture.
"""
import asyncio
import json
import re
from typing import Any, Dict, Set, Union, Tuple
from starlette.responses import StreamingResponse


class StarStreamCore:
    """
    Core broadcasting engine - manages topics and subscribers.
    
    Responsibilities:
    - Manage topic subscriptions
    - Format messages for SSE protocol
    - Execute broadcast safely
    """
    
    def __init__(self):
        self._topics: Dict[str, Set[asyncio.Queue]] = {}
        self._user_topics: Dict[str, str] = {}
        self._room_topics: Dict[str, Set[str]] = {}
    
    async def subscribe(self, topic: str = "global"):
        """Subscribe to a topic and yield messages."""
        if topic not in self._topics:
            self._topics[topic] = set()
        
        queue = asyncio.Queue()
        self._topics[topic].add(queue)
        
        try:
            while True:
                message = await queue.get()
                yield message
        finally:
            if topic in self._topics:
                self._topics[topic].discard(queue)
                if not self._topics[topic]:
                    del self._topics[topic]
    
    def _format_message(self, msg: Union[str, Tuple]) -> str:
        """Format message for SSE."""
        if isinstance(msg, tuple) and len(msg) >= 2:
            event_type = f"datastar-patch-{msg[0]}"
            payload = msg[1]
            lines = [f"event: {event_type}"]
            
            if msg[0] == "elements":
                content, selector, mode, use_vt, signals = self._unpack_elements(payload)
                if selector:
                    lines.append(f"data: selector {selector}")
                if mode:
                    lines.append(f"data: mode {mode}")
                if use_vt:
                    lines.append(f"data: useViewTransition {str(use_vt).lower()}")
                
                contents = content if isinstance(content, (list, tuple)) else [content]
                for item in contents:
                    for line in str(item).splitlines():
                        lines.append(f"data: elements {line}")
            
            elif msg[0] == "signals":
                for line in json.dumps(payload).splitlines():
                    lines.append(f"data: signals {line}")
            
            return "\n".join(lines) + "\n\n"
        
        if isinstance(msg, str):
            if msg.startswith("event:"):
                return msg + ("\n\n" if not msg.endswith("\n\n") else "")
            return f"data: {msg}\n\n"
        return ""
    
    def _unpack_elements(self, payload) -> Tuple:
        """Unpack elements payload - handles various formats."""
        if isinstance(payload, tuple):
            # (content, selector, mode, use_vt, signals)
            if len(payload) >= 5:
                return payload[:5]
            elif len(payload) >= 2:
                # (content, selector)
                return (payload[0], payload[1], None, None, None)
        # Default: content only
        return (payload, None, None, None, None)
    
    async def broadcast(
        self,
        message: Union[str, Tuple],
        topic: str = "global",
        exclude: Set = None,
    ):
        """Broadcast message to all subscribers of a topic."""
        formatted = self._format_message(message)
        
        if topic in self._topics:
            for queue in list(self._topics[topic]):
                await queue.put(formatted)
    
    def sse_response(self, topic: str = "global"):
        """Create Starlette StreamingResponse for SSE."""
        
        async def event_publisher():
            try:
                async for msg in self.subscribe(topic):
                    yield msg
            except asyncio.CancelledError:
                pass
        
        return StreamingResponse(
            event_publisher(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
```

**Step 4: Run test to verify it passes**

```bash
cd /Users/cali/Development/starstream-monorepo/packages/starstream
python -m pytest tests/test_core.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add starstream/core.py tests/test_core.py
git commit -m "feat: extract StarStreamCore to separate module"
```

---

## Task 3: Adicionar schedule_broadcast ao Plugin

**Files:**
- Modify: `/Users/cali/Development/starstream-monorepo/packages/starstream/starstream/plugin.py`

**Step 1: Write the failing test**

```python
# tests/test_schedule_broadcast.py
import pytest
from unittest.mock import Mock, AsyncMock, patch
from starlette.background import BackgroundTasks
from starstream.plugin import StarStreamPlugin

def test_schedule_broadcast_exists():
    """Test that schedule_broadcast method exists."""
    app = Mock()
    plugin = StarStreamPlugin(app)
    
    assert hasattr(plugin, 'schedule_broadcast')
    assert callable(plugin.schedule_broadcast)

def test_schedule_broadcast_adds_task():
    """Test schedule_broadcast adds task to BackgroundTasks."""
    app = Mock()
    plugin = StarStreamPlugin(app)
    plugin.core = Mock()
    
    mock_background = Mock()
    mock_message = ("elements", ("<div>test</div>", "#app"))
    
    plugin.schedule_broadcast(mock_background, mock_message, target="test")
    
    # Verify add_task was called
    assert mock_background.add_task.called
    
    # Get the task function
    task_func = mock_background.add_task.call_args[0][0]
    
    # Verify it's a coroutine function
    import asyncio
    assert asyncio.iscoroutinefunction(task_func)

def test_schedule_broadcast_with_string_message():
    """Test schedule_broadcast with string message."""
    app = Mock()
    plugin = StarStreamPlugin(app)
    plugin.core = Mock()
    
    mock_background = Mock()
    
    plugin.schedule_broadcast(mock_background, "hello world", target="chat")
    
    assert mock_background.add_task.called
```

**Step 2: Run test to verify it fails**

```bash
cd /Users/cali/Development/starstream-monorepo/packages/starstream
python -m pytest tests/test_schedule_broadcast.py -v
```

Expected: FAIL - "schedule_broadcast not found"

**Step 3: Write minimal implementation**

Adicionar ao final da classe StarStreamPlugin em `plugin.py`:

```python
def schedule_broadcast(
    self,
    background: BackgroundTasks,
    message: Union[str, Tuple],
    target: Union[str, Dict, None] = None,
):
    """
    Schedule broadcast for execution after SSE response.
    
    Use this method in SSE handlers (sync generators with yield)
    to schedule broadcast to other clients after the response
    has been sent.
    
    Args:
        background: BackgroundTasks (injected by Starlette)
        message: Message to broadcast (str, tuple, or StarHTML elements)
        target: Target topic (str or dict). Auto-detected if None.
        
    Example:
        @rt("/todos")
        @sse
        def delete_todo(todo_id: str, background: BackgroundTasks):
            delete_todo_db(todo_id)
            
            stream.schedule_broadcast(
                background,
                elements(todo_list(), "#todos"),
                target="todos"
            )
            
            yield elements(todo_list(), "#todos")
            yield signals()
    """
    # Resolve target to topic
    topic = self._resolve_target(target)
    
    # Add task to background
    background.add_task(
        self._do_broadcast_safe,
        message,
        topic
    )

async def _do_broadcast_safe(
    self,
    message: Union[str, Tuple],
    topic: str,
):
    """
    Internal: Broadcast with error handling and metrics.
    """
    import time
    import logging
    
    logger = logging.getLogger("starstream")
    start = time.time()
    
    try:
        await self.core.broadcast(message, topic)
        
        # Record success metrics
        latency = time.time() - start
        self._metrics[topic].record_success(latency)
        
        logger.debug(
            f"Broadcast succeeded",
            extra={"topic": topic, "latency_ms": round(latency * 1000, 2)}
        )
        
    except Exception as e:
        # Record error metrics
        self._metrics[topic].record_error()
        
        logger.error(
            f"Broadcast failed",
            extra={"topic": topic, "error": str(e)},
            exc_info=True
        )
        
        # Call error hook if configured
        if self.on_broadcast_error:
            try:
                self.on_broadcast_error(topic, message, e)
            except Exception as hook_error:
                logger.error(
                    f"Broadcast error hook failed",
                    extra={"error": str(hook_error)}
                )

def _resolve_target(self, target: Union[str, Dict, None]) -> str:
    """Resolve target to topic string."""
    if target is None:
        return self.default_topic
    elif isinstance(target, str):
        return target
    elif isinstance(target, dict):
        t_type = target.get("type", "topic")
        t_id = target.get("id", "global")
        return f"{t_type}:{t_id}" if t_type != "topic" else t_id
    else:
        return self.default_topic

def get_metrics(self, topic: str = None):
    """Get broadcast metrics."""
    if topic:
        return self._metrics.get(topic, BroadcastMetrics()).get_stats()
    return {
        t: m.get_stats() for t, m in self._metrics.items()
    }

def set_error_hook(self, hook):
    """Set custom error handler for broadcast failures."""
    self.on_broadcast_error = hook
```

**Step 4: Run test to verify it passes**

```bash
cd /Users/cali/Development/starstream-monorepo/packages/starstream
python -m pytest tests/test_schedule_broadcast.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add starstream/plugin.py
git commit -m "feat: add schedule_broadcast for SSE handlers"
```

---

## Task 4: Atualizar __init__.py para exportar novos módulos

**Files:**
- Modify: `/Users/cali/Development/starstream-monorepo/packages/starstream/starstream/__init__.py`

**Step 1: Write the code**

```python
# Adicionar aos imports
from .core import StarStreamCore
from .metrics import BroadcastMetrics

# Adicionar ao __all__
__all__ = [
    "StarStreamPlugin",
    "StarStreamCore",  # NOVO
    "BroadcastMetrics",  # NOVO
    # ... rest unchanged
]
```

**Step 2: Run test to verify exports work**

```bash
cd /Users/cali/Development/starstream-monorepo/packages/starstream
python -c "from starstream import StarStreamCore, BroadcastMetrics; print('OK')"
```

Expected: "OK"

**Step 3: Commit**

```bash
git add starstream/__init__.py
git commit -m "feat: export StarStreamCore and BroadcastMetrics"
```

---

## Task 5: Atualizar POC com Nova API

**Files:**
- Modify: `/Users/cali/Development/poc-starhtml-todo-canvas/app.py`

**Step 1: Identificar handlers que precisam de broadcast**

Procurar handlers com comentário "Broadcast disabled":

```bash
grep -n "Broadcast disabled" app.py
```

**Step 2: Atualizar handlers**

Para cada handler SSE que precisa de broadcast:

```python
# ANTES:
@rt("/todos-bc", methods=["DELETE"])
@sse
def delete_todo_bc(todo_id: str, active_filter_bc: Signal = None):
    delete_todo_db(todo_id)
    bc_html = todo_bc_list_ui(active_filter_bc)
    # Note: Broadcast disabled for SSE handlers
    yield elements(bc_html, selector="#todo-bc-list-content")
    yield signals()

# DEPOIS:
@rt("/todos-bc", methods=["DELETE"])
@sse
def delete_todo_bc(
    todo_id: str,
    active_filter_bc: Signal = None,
    background: BackgroundTasks = None  # Starlette injects this
):
    delete_todo_db(todo_id)
    bc_html = todo_bc_list_ui(active_filter_bc)
    
    # Schedule broadcast para outros clientes
    if background:
        starstream_plugin.schedule_broadcast(
            background,
            elements(bc_html, selector="#todo-bc-list-content"),
            target="todos"
        )
    
    yield elements(bc_html, selector="#todo-bc-list-content")
    yield signals()
```

**Step 3: Verificar se app funciona**

```bash
cd /Users/cali/Development/poc-starhtml-todo-canvas
python -c "from app import app; print('App loads OK')"
```

**Step 4: Commit**

```bash
git add app.py
git commit -m "feat: add broadcast to SSE handlers in POC"
```

---

## Task 6: Criar Exemplo Completo

**Files:**
- Create: `/Users/cali/Development/starstream-monorepo/packages/starstream/examples/todo_broadcast.py`

**Step 1: Write complete example**

```python
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


if __name == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Step 2: Test example runs**

```bash
cd /Users/cali/Development/starstream-monorepo/packages/starstream
python examples/todo_broadcast.py &
sleep 2
curl http://localhost:8000 | head -20
```

Expected: HTML with todo list renders

**Step 3: Commit**

```bash
git add examples/todo_broadcast.py
git commit -m "feat: add todo broadcast example"
```

---

## Task 7: Verificação Final e Limpeza

**Step 1: Run all tests**

```bash
cd /Users/cali/Development/starstream-monorepo/packages/starstream
python -m pytest -v
```

Expected: All tests pass

**Step 2: Verify no regressions**

```bash
python -m pytest tests/test_integration.py -v
```

**Step 3: Commit final**

```bash
git add -A
git commit -m "feat: complete SSE broadcast integration - schedule_broadcast, metrics, core separation"
```

---

## Resumo de Arquivos Modificados

| Arquivo | Ação |
|---------|------|
| `starstream/metrics.py` | CREATE - BroadcastMetrics class |
| `starstream/core.py` | CREATE - StarStreamCore extracted |
| `starstream/plugin.py` | MODIFY - Add schedule_broadcast, metrics, error hooks |
| `starstream/__init__.py` | MODIFY - Export new modules |
| `tests/test_metrics.py` | CREATE |
| `tests/test_core.py` | CREATE |
| `tests/test_schedule_broadcast.py` | CREATE |
| `examples/todo_broadcast.py` | CREATE |
| `poc-starhtml-todo-canvas/app.py` | MODIFY - Use new API |

---

## Ordem de Execução

1. Task 1: BroadcastMetrics
2. Task 2: StarStreamCore (core.py)
3. Task 3: schedule_broadcast no Plugin
4. Task 4: Update __init__.py
5. Task 5: Update POC
6. Task 6: Create Example
7. Task 7: Verification

---

**Plan complete.** Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?