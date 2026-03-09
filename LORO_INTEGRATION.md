# StarStream v0.5.0 - Convention over Configuration

## Resumo da Implementação

### ✅ Integração REAL com Loro CRDT

**ANTES:** Stub/skeleton que simulava CRDT (não funcionava de verdade)

**DEPOIS:** Integração real com Loro CRDT (v1.10.3+)

**Como funciona:**

1. **Usuário instala:**
   ```bash
   pip install starstream[collaborative]
   ```

2. **Ativa collaborative:**
   ```python
   stream = StarStreamPlugin(app, collaborative=True)
   ```

3. **Usa Loro REAL:**
   ```python
   # Engine cria LoroDoc real
   loro_doc = LoroDoc()
   
   # Importa delta usando CRDT real
   loro_doc.import_(delta)
   
   # Exporta snapshot
   snapshot = loro_doc.export({"mode": "snapshot"})
   ```

4. **Se loro não instalado:**
   ```
   ImportError: Collaborative editing requires 'loro'.
   Install with: pip install starstream[collaborative]
   ```

---

## Arquitetura

```
StarStreamPlugin(collaborative=True)
         ↓
CollaborativeEngine
         ↓
    [LoroDoc]  ← Loro CRDT real (v1.10.3+)
         ↓
   Storage Backend (SQLite/Custom)
```

---

## API

### Básica

```python
from starstream import StarStreamPlugin

# Criar
stream = StarStreamPlugin(app, collaborative=True)

# Conectar usuário ao documento
await stream.collaborative.connect("doc-1", "user-123")

# Sincronizar mudanças (CRDT real) - AUTO-BROADCAST to other peers
delta = client_loro_doc.export({"mode": "update"})
await stream.collaborative.sync("doc-1", delta, "user-123")

# Manual control: apply delta without broadcast
await stream.collaborative.apply_delta("doc-1", delta, "user-123")

# Obter estado
state = await stream.collaborative.get_state("doc-1")
# {"doc_id": "doc-1", "peers": ["user-123"], "content": <snapshot>}

# Desconectar
await stream.collaborative.disconnect("doc-1", "user-123")
```

### Com Persistência

```python
stream = StarStreamPlugin(
    app,
    collaborative=True,
    persist=True  # Salva em SQLite automaticamente
)
```

### Storage Customizado

```python
from starstream.storage import StorageBackend

class PostgresBackend(StorageBackend):
    # ... implementação

stream = StarStreamPlugin(
    app,
    collaborative=True,
    storage=PostgresBackend(url)
)
```

---

## Fluxo de Dados

```
Client (LoroDoc)          Server (StarStream)            Storage
      │                          │                           │
      ├─ export(delta) ──────────►                           │
      │                          ├─ import(delta)            │
      │                          │   (Loro CRDT merge)       │
      │                          │                           │
      │                          ├─ broadcast to peers       │
      │                          │                           │
      │                          ├─ save to storage ────────►│
      │                          │                           │
      │◄───── receive updates ───┤                           │
```

---

## Testes

**Com Loro instalado:**
```bash
pip install loro
pytest tests/test_collaborative.py  # ✅ Passa
```

**Sem Loro instalado:**
```bash
pytest tests/test_collaborative.py
# ✅ Falha com erro claro: "Install with: pip install starstream[collaborative]"
```

---

## Tecnologias

| Componente | Tecnologia | Versão |
|-----------|-----------|--------|
| CRDT Engine | Loro | v1.10.3+ |
| Storage (default) | SQLite | Built-in |
| Python | Python | 3.10+ |
| Framework | StarHTML | 0.1.0+ |

---

## Comparação: Antes vs Depois

| Aspecto | Antes (Stub) | Depois (Real) |
|---------|-------------|---------------|
| **CRDT** | ❌ Simulado | ✅ Loro real |
| **Conflict Resolution** | ❌ Não funcionava | ✅ Automático |
| **Delta Sync** | ❌ Fake | ✅ Real Loro deltas |
| **Persistence** | ❌ Não salvava | ✅ SQLite/Custom |
| **Time Travel** | ❌ Não suportado | ✅ Loro suporta |
| **Tipos CRDT** | ❌ Nenhum | ✅ Text, List, Map, Tree, Counter |
| **Performance** | ❌ N/A | ✅ Rust-based (fast) |

---

## Exemplo Completo

```python
from starhtml import star_app, rt, serve
from starstream import StarStreamPlugin

app, rt = star_app()
stream = StarStreamPlugin(app, collaborative=True, persist=True)

@rt("/doc/{doc_id}/sync", methods=["POST"])
async def sync_doc(doc_id: str, user_id: str):
    """Recebe delta do cliente e sincroniza"""
    # Em produção, receberia delta do request body
    delta = await request.body()
    
    # Sincroniza usando CRDT real
    success = await stream.collaborative.sync(doc_id, delta, user_id)
    
    return {"success": success}

@rt("/doc/{doc_id}/state")
async def get_doc(doc_id: str):
    """Retorna estado atual do documento"""
    state = await stream.collaborative.get_state(doc_id)
    return state

if __name__ == "__main__":
    print("Editor Colaborativo com Loro CRDT")
    print("Instale: pip install starstream[collaborative]")
    serve()
```

---

## Próximos Passos

1. ✅ **DONE:** Integração real com Loro
2. ✅ **DONE:** API `collaborative=True`
3. ✅ **DONE:** Storage customizável
4. 📝 **TODO:** Exemplo funcional completo com UI
5. 📝 **TODO:** SKILL.md atualizada
6. 📝 **TODO:** Benchmark de performance

---

## Licença

MIT

---

## Links

- **Loro CRDT:** https://loro.dev
- **Loro PyPI:** https://pypi.org/project/loro/
- **Loro GitHub:** https://github.com/loro-dev/loro
- **StarStream:** https://github.com/renatocaliari/starstream