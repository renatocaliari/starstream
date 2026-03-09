# StarStream v0.5.0 - Convention over Configuration

## Mudanças Principais

### 1. **Nova API de Persistência**

**Antes:**
```python
stream = StarStreamPlugin(app, enable_history=True)
```

**Depois:**
```python
stream = StarStreamPlugin(app, persist=True)
```

**Benefícios:**
- Nome mais intuitivo (`persist` em vez de `enable_history`)
- SQLite automático em `starstream.db`
- Customizável com `db_path` ou `storage` custom

### 2. **Collaborative Editing Transparente**

**Antes:**
```python
# Precisava importar e instanciar manualmente
from starstream_loro import LoroPlugin
loro = LoroPlugin(stream)
```

**Depois:**
```python
# Uma flag, zero imports
stream = StarStreamPlugin(app, collaborative=True)
await stream.collaborative.sync("doc-1", delta, "user-123")
```

**Benefícios:**
- API centrada na intenção (não na tecnologia)
- Lazy loading (não quebra se Loro não instalado)
- Mensagens de erro claras
- Instalação opcional: `pip install starstream[collaborative]`

### 3. **Storage Customizável**

**Interface unificada:**
```python
from starstream.storage import StorageBackend

class PostgresBackend(StorageBackend):
    async def get(self, key: str):
        # Sua implementação
        pass
    
    async def set(self, key: str, value, ttl=None):
        # Sua implementação
        pass
    
    # ... outros métodos

# Uso
stream = StarStreamPlugin(
    app,
    persist=True,
    storage=PostgresBackend(DATABASE_URL)
)
```

## Instalação

```bash
# Core (leve)
pip install starstream

# Com colaboração
pip install starstream[collaborative]
```

## API Completa

```python
from starstream import StarStreamPlugin

# Chat simples
stream = StarStreamPlugin(app)

# Chat persistente
stream = StarStreamPlugin(app, persist=True)

# Editor colaborativo
stream = StarStreamPlugin(app, collaborative=True)

# Com storage customizado
stream = StarStreamPlugin(
    app,
    persist=True,
    collaborative=True,
    storage=MyPostgresBackend(url)
)
```

## Breaking Changes

- `enable_history` → `persist` (mas ainda funciona por compatibilidade)
- `starstream-loro` → integrado no core (use `collaborative=True`)

## Testes

- ✅ 15 novos testes para `persist` e `collaborative`
- ✅ 158 testes totais passando
- ✅ Cobertura completa das novas features

## Arquivos Modificados

1. `packages/starstream/starstream/plugin.py` - Flags `persist` e `collaborative`
2. `packages/starstream/starstream/collaborative/` - Novo módulo
3. `packages/starstream/pyproject.toml` - Extra `[collaborative]`
4. `packages/starstream/README.md` - Documentação atualizada
5. `packages/starstream/tests/test_persist.py` - Testes de persistência
6. `packages/starstream/tests/test_collaborative.py` - Testes de colaboração
7. `packages/starstream/examples/collaborative_editor.py` - Exemplo prático

## Próximos Passos

1. **Integração real com Loro** (quando `loro` estiver disponível no PyPI)
2. **Exemplos mais completos** com UI real
3. **Documentação de migração** para usuários existentes
4. **Benchmark** de performance com collaborative editing