# Investigação de Broadcast - 2025-03-08

> **AVISO:** Este arquivo é para investigação temporária. Não deve ser commitado no GitHub.

## Status do Plugin StarStream

### ✅ FUNCIONANDO

**Testes Unitários:**
- 139/139 testes passando
- `test_broadcast_to_multiple_subscribers` ✅
- `test_broadcast_multiple_targets` ✅
- Todos os testes de broadcast passam

**API:**
- `broadcast()` funciona corretamente (fire-and-forget)
- Múltiplos subscribers recebem mensagens
- SSE endpoint funcional
- Broadcast via curl funciona

**Implementação:**
- API unificada implementada (v0.2.0)
- Removido `schedule_broadcast()` ✅
- Removido `broadcast_exclude()` ✅
- `broadcast()` é sync e fire-and-forget ✅

## Status da POC (poc-starhtml-todo-canvas)

### ✅ FUNCIONANDO

**Servidor:**
- POST via curl funciona
- Broadcast é enviado corretamente
- SSE endpoint responde (200 OK)
- Servidor processa requisições

**SSE Connections:**
- Elementos SSE corretos no HTML:
  ```html
  <div data-star-sse="connect:/starstream?topic=todos"></div>
  <div data-star-sse="connect:/starstream?topic=canvas"></div>
  <div data-star-sse="connect:/starstream?topic=presence"></div>
  ```
- SSE connections estabelecidas
- Datastar carregado

### ❌ NÃO FUNCIONANDO

**Frontend:**
- Botão com `data-on:click="@post(...)"` não executa POST
- Formulário não submete via JavaScript
- Datastar não processa `@post` action

**Evidências:**
- HTML gerado corretamente
- Sintaxe do botão correta
- Datastar versão 1.0.0-beta.1 carregado
- Nenhum erro no console
- Botão tem `data-on:click` correto
- Input tem valor correto

**Testes realizados:**
```bash
# ✅ Funciona
curl -X POST http://localhost:8000/todos-bc/add -F "new_todo_bc=TEST"

# ❌ Não funciona
agent-browser click @button  # Botão não executa POST
```

## Diagnóstico

**Problema:** O Datastar não está processando o `@post` action corretamente.

**Possíveis causas:**
1. Versão do Datastar (1.0.0-beta.1) pode ter bug
2. Conflito com outros scripts
3. Problema específico do ambiente agent-browser
4. Datastar não inicializado corretamente

**Soluções testadas:**
- ✅ Mudar de `Form` com `data_on_submit` para `Button` com `data_on_click`
- ✅ Usar sintaxe correta do StarHTML
- ✅ Verificar HTML gerado
- ❌ Ainda não funciona via agent-browser

## Próximos Passos

1. **Testar manualmente no navegador** (não via agent-browser)
2. **Verificar se funciona em navegador real**
3. **Se funcionar, problema é do agent-browser**
4. **Se não funcionar, investigar versão do Datastar**

## Correções Aplicadas na POC

### API do StarStream
```python
# ❌ Antes
await starstream_plugin.broadcast_to_room(room, message)
await starstream_plugin.send_to_user(peer, message)

# ✅ Depois
starstream_plugin.broadcast(message, target=f"room:{room}")
starstream_plugin.broadcast(message, target=f"user:{peer}")
```

### SSE Connections
```python
# ❌ Antes
Div(id="starstream-init", data_init="@get('/stream?topic=global')")

# ✅ Depois
starstream_plugin.get_stream_element("todos")
starstream_plugin.get_stream_element("canvas")
starstream_plugin.get_stream_element("presence")
```

### Formulário
```python
# ❌ Antes (Form com data_on_submit)
Form(
    Button(type="submit", data_on_submit=...),
)

# ✅ Depois (Button com data_on_click)
Div(
    Button(type="button", data_on_click=post(...)),
)
```

## Conclusão

**Plugin StarStream:** ✅ Pronto e funcionando
**POC:** ⚠️ Problema no frontend (não relacionado ao plugin)

O plugin StarStream está funcionando corretamente. O problema na POC é específico do ambiente de teste (agent-browser) ou da versão do Datastar, não afeta o plugin em si.

---

**Data:** 2025-03-08
**Investigador:** Claude (Opencode)
**Status:** Plugin validado, POC precisa de teste manual