# Design: StarStream + SSE Broadcast Integration

## Contexto

O projeto `poc-starhtml-todo-canvas` apresenta um conflito arquitetural fundamental:

- **StarHTML SSE**: Requer handlers síncronos com `yield` (geradores)
- **StarStream Broadcast**: Requer `await` (operações assíncronas)
- **Problema**: Não é possível usar `await` dentro de geradores síncronos

## Objetivo

Criar uma integração limpa entre StarStream e StarHTML SSE que permita broadcast multi-cliente sem quebrar a semântica de geradores SSE.

## Princípios de Design

1. **KISS (Keep It Simple, Stupid)**: APIs devem ser óbvias e fáceis de usar
2. **DRY (Don't Repeat Yourself)**: Lógica de broadcast centralizada, não duplicada
3. **Polimorfismo**: API unificada que se adapta ao contexto (async vs sync)
4. **Convention over Configuration**: Funciona por padrão, configuração opcional

## Solução Proposta

### Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                    REQUEST FLOW                              │
└─────────────────────────────────────────────────────────────┘

Cliente A ──POST /todos──┐
                        │
                        ▼
                  ┌──────────────┐
                  │  Handler SSE │  ← Síncrono (yield)
                  │  (def)       │
                  └─────┬────────┘
                        │
                        ├─→ yield elements() → Cliente A (SSE)
                        │
                        └─→ schedule_broadcast(
                                background,
                                elements(...)
                            )  ← Agendado via BackgroundTasks
                        │
                        ▼  (Após response enviada)
                  ┌──────────────┐
                  │  Background  │  ← Async (await)
                  │  Task        │
                  └─────┬────────┘
                        │
                        └─→ broadcast() → Clientes B, C, D...
```

### Componentes

#### 1. StarStreamPlugin (API Principal)

```python
class StarStreamPlugin:
    """
    Plugin para broadcast real-time em aplicações StarHTML.
    
    Princípios:
    - KISS: 2 métodos principais (broadcast, schedule_broadcast)
    - Polimorfismo: mesma mensagem funciona em async e sync
    - Convention: topic auto-detect por padrão
    """
    
    async def broadcast(self, message, target=None):
        """
        Broadcast para uso em código async.
        
        Args:
            message: str, tuple, ou elementos StarHTML
            target: str (topic), dict, ou None (auto-detect)
            
        Examples:
            await stream.broadcast("Hello!")  # Auto-detect
            await stream.broadcast("Hello!", "room:123")  # Topic explícito
            await stream.broadcast(elements(...), {"type": "room", "id": "123"})
        """
        ...
    
    def schedule_broadcast(self, background, message, target=None):
        """
        Agenda broadcast via BackgroundTasks para handlers SSE.
        
        Args:
            background: BackgroundTasks (injetado pelo Starlette)
            message: str, tuple, ou elementos StarHTML
            target: str (topic), dict, ou None (auto-detect)
            
        Example:
            @rt("/todos")
            @sse
            def delete_todo(todo_id: str, background: BackgroundTasks):
                delete_todo_db(todo_id)
                bc_html = todo_bc_list_ui()
                
                # Agenda broadcast para outros clientes
                stream.schedule_broadcast(
                    background,
                    elements(bc_html, selector="#todos"),
                    target="todos"
                )
                
                # Resposta para cliente atual
                yield elements(bc_html, selector="#todos")
                yield signals()
        """
        ...
```

#### 2. StarStreamCore (Engine)

```python
class StarStreamCore:
    """
    Engine de broadcast - separado do plugin para testabilidade.
    
    Responsabilidades:
    - Gerenciar tópicos e subscribers
    - Formatar mensagens para SSE
    - Executar broadcast de forma segura
    """
    
    async def broadcast(self, message, topic="global"):
        """
        Broadcast message to all subscribers.
        Safe to call from async context.
        """
        formatted = self._format_message(message)
        
        if topic in self._topics:
            for queue in list(self._topics[topic]):
                await queue.put(formatted)
    
    def _format_message(self, msg):
        """
        Formata mensagem para protocolo SSE.
        Suporta strings, tuplas Datastar, e elementos StarHTML.
        """
        ...
```

#### 3. BroadcastMetrics (Observabilidade)

```python
@dataclass
class BroadcastMetrics:
    """
    Métricas simples de broadcast.
    
    Design KISS: apenas contadores e latência básica.
    """
    success_count: int = 0
    error_count: int = 0
    latency_samples: list = field(default_factory=lambda: deque(maxlen=100))
    
    def record_success(self, latency: float):
        self.success_count += 1
        self.latency_samples.append(latency)
    
    def record_error(self):
        self.error_count += 1
    
    def get_stats(self):
        """Retorna estatísticas básicas."""
        if not self.latency_samples:
            return {"success": self.success_count, "error": self.error_count}
        
        sorted_latencies = sorted(self.latency_samples)
        n = len(sorted_latencies)
        
        return {
            "success": self.success_count,
            "error": self.error_count,
            "avg_latency_ms": round(sum(sorted_latencies) / n * 1000, 2),
            "p95_latency_ms": round(sorted_latencies[int(n * 0.95)] * 1000, 2) if n >= 20 else None
        }
```

## Convenções

### Auto-detecção de Topic

```python
# Convenção: tópico é inferido automaticamente
await stream.broadcast("msg")  # topic="global"
await stream.broadcast("msg", "chat")  # topic="chat"
await stream.broadcast("msg", "room:123")  # topic="room:123"
await stream.broadcast("msg", {"type": "room", "id": "123"})  # topic="room:123"
```

### Target Polimórfico

```python
# Target pode ser: None, str, ou dict
stream.broadcast(msg)              # None → auto-detect
stream.broadcast(msg, "global")    # str → topic direto
stream.broadcast(msg, "room:123")  # str com prefixo → room
stream.broadcast(msg, {"type": "room", "id": "123"})  # dict → room:123
stream.broadcast(msg, {"type": "user", "id": "456"})  # dict → user:456
```

## Fluxo de Dados

### Handler Async (broadcast direto)

```python
@rt("/api/message")
async def send_message(msg: str):
    # Código async - pode usar await
    await save_message(msg)
    await stream.broadcast(f"New message: {msg}", topic="chat")
    return {"sent": True}
```

### Handler SSE (schedule_broadcast)

```python
@rt("/todos/delete")
@sse
def delete_todo(todo_id: str, background: BackgroundTasks):
    # Handler síncrono - não pode usar await
    delete_todo_db(todo_id)
    
    # Agenda broadcast para executar depois
    stream.schedule_broadcast(
        background,
        elements(todo_list(), "#todos"),
        target="todos"
    )
    
    # Resposta imediata via SSE
    yield elements(todo_list(), "#todos")
    yield signals(deleted=True)
```

## Estrutura de Arquivos

```
starstream/
├── __init__.py          # Exporta StarStreamPlugin, StarStreamCore
├── plugin.py            # StarStreamPlugin (API pública)
├── core.py              # StarStreamCore (engine)
├── metrics.py           # BroadcastMetrics
├── errors.py            # Error hooks e tratamento
├── storage/
│   ├── base.py
│   └── sqlite.py
├── features/            # Features opcionais
│   ├── presence.py
│   ├── typing.py
│   └── cursor.py
└── examples/
    ├── basic.py
    ├── todo_broadcast.py
    └── chat.py
```

## API Removida (Breaking Changes Aceitos)

Métodos legados/confusos removidos:

```python
# Removidos - não fazem mais sentido com nova API
- broadcast_to_topic()  # Usar broadcast(topic=...)
- broadcast_to_room()   # Usar broadcast("room:X")
- send_to_user()        # Usar broadcast("user:X")
- broadcast_exclude()   # Feature complexa, remover por ora
```

## Testabilidade

### Teste Unitário

```python
def test_schedule_broadcast():
    mock_background = Mock()
    plugin = StarStreamPlugin(app=Mock())
    
    plugin.schedule_broadcast(
        mock_background,
        elements(Div("test")),
        target="test"
    )
    
    # Verifica se task foi agendada
    assert mock_background.add_task.called
    
    # Verifica se função é corrotina
    task_func = mock_background.add_task.call_args[0][0]
    assert asyncio.iscoroutinefunction(task_func)
```

### Teste de Integração

```python
async def test_broadcast_flow():
    app, rt = star_app()
    stream = StarStreamPlugin(app)
    
    received = []
    
    @rt("/connect")
    async def connect():
        async for msg in stream.core.subscribe("test"):
            received.append(msg)
    
    @rt("/send")
    @sse
    def send(background: BackgroundTasks):
        stream.schedule_broadcast(background, "test msg", "test")
        yield elements(Div("sent"))
    
    async with TestClient(app) as client:
        # Cliente conecta
        connect_task = asyncio.create_task(client.get("/connect"))
        
        # Envia mensagem
        await client.post("/send")
        
        # Verifica broadcast
        await asyncio.sleep(0.1)
        assert "test msg" in received
```

## Migração da POC

### Antes (Sem Broadcast)

```python
@rt("/todos-bc", methods=["DELETE"])
@sse
def delete_todo_bc(todo_id: str, active_filter_bc: Signal = None):
    delete_todo_db(todo_id)
    bc_html = todo_bc_list_ui(active_filter_bc)
    # Broadcast desabilitado
    yield elements(bc_html, selector="#todo-bc-list-content")
    yield signals()
```

### Depois (Com Broadcast)

```python
@rt("/todos-bc", methods=["DELETE"])
@sse
def delete_todo_bc(
    todo_id: str,
    active_filter_bc: Signal = None,
    background: BackgroundTasks  # Injetado pelo Starlette
):
    delete_todo_db(todo_id)
    bc_html = todo_bc_list_ui(active_filter_bc)
    
    # Broadcast agendado para outros clientes
    stream.schedule_broadcast(
        background,
        elements(bc_html, selector="#todo-bc-list-content"),
        target="todos"
    )
    
    # Resposta para cliente atual
    yield elements(bc_html, selector="#todo-bc-list-content")
    yield signals()
```

## Vantagens da Solução

1. **KISS**: API com apenas 2 métodos principais
2. **DRY**: Lógica de broadcast centralizada no Core
3. **Polimorfismo**: Mesma mensagem funciona em async e sync
4. **Convention**: Topic auto-detect por padrão
5. **Observabilidade**: Métricas simples mas úteis
6. **Testabilidade**: Fácil de mockar e testar
7. **Compatibilidade**: Funciona com StarHTML atual
8. **Extensibilidade**: Fácil adicionar features no futuro

## Riscos e Mitigações

| Risco | Mitigação |
|-------|-----------|
| BackgroundTasks não disponível | Verificar compatibilidade StarHTML |
| Race condition (broadcast antes de subscribe) | Documentar que broadcast é eventual |
| Performance com muitos subscribers | Métricas identificam gargalo |
| Erros silenciosos em background | Logs estruturados + métricas |

## Próximos Passos

1. Implementar `BroadcastMetrics`
2. Refatorar `plugin.py` com `schedule_broadcast()`
3. Mover `StarStreamCore` para `core.py`
4. Adicionar error hooks
5. Criar testes unitários
6. Criar testes de integração SSE
7. Atualizar POC com nova API
8. Criar exemplos e documentação

---

**Data**: 2025-03-07
**Autor**: opencode
**Status**: Design Aprovado
