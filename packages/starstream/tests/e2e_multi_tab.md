# Testes E2E Multi-Tab com agent-browser

## Objetivo

Validar broadcasting entre múltiplas abas usando agent-browser para testar o fluxo completo frontend → backend → frontend.

## Por que agent-browser?

| Problema Detectado | Teste Unitário | Teste agent-browser |
|--------------------|----------------|---------------------|
| `data-star-sse` inválido | ✅ Passa (atributo existe) | ❌ Falha (não funciona) |
| Versão Loro diferente | ✅ Passa (backend ok) | ❌ Falha (WASM error) |
| Broadcast não recebido | ✅ Passa (backend envia) | ❌ Falha (frontend não recebe) |

## Cenários de Teste

### 1. TODO Broadcasting

```yaml
test: todo_broadcast_multi_tab
steps:
  - action: open_tab
    id: tab1
    url: http://localhost:8000/todo-bc
    
  - action: open_tab
    id: tab2
    url: http://localhost:8000/todo-bc
    
  - action: screenshot
    tab: tab1
    save: tab1_initial.png
    
  - action: type
    tab: tab1
    selector: input[placeholder*="Broadcast"]
    text: "Test multi-tab"
    
  - action: click
    tab: tab1
    selector: button:has(svg)  # Send button
    
  - action: wait
    duration: 500ms
    
  - action: screenshot
    tab: tab2
    save: tab2_after_broadcast.png
    
  - action: assert_text
    tab: tab2
    selector: #todo-bc-list
    contains: "Test multi-tab"
```

### 2. Canvas Delta Sync

```yaml
test: canvas_delta_multi_tab
steps:
  - action: open_tab
    id: tab1
    url: http://localhost:8000/canvas-delta
    
  - action: open_tab
    id: tab2
    url: http://localhost:8000/canvas-delta
    
  - action: wait
    duration: 1000ms  # Wait for Loro init
    
  - action: assert_console
    tab: tab1
    not_contains: "panic"
    not_contains: "error"
    
  - action: screenshot
    tab: tab1
    save: canvas_tab1.png
```

### 3. Version Sync

```yaml
test: loro_version_sync
steps:
  - action: open_tab
    url: http://localhost:8000/canvas-delta
    
  - action: wait
    duration: 500ms
    
  - action: evaluate_js
    script: |
      // Check if Loro loaded with correct version
      const config = await fetch('/api/config').then(r => r.json());
      const loadedVersion = window.LORO_VERSION || 'unknown';
      return {
        backend: config.loro_version,
        frontend: loadedVersion,
        match: config.loro_version === loadedVersion
      };
    
  - action: assert
    condition: result.match === true
```

### 4. SSE Connection

```yaml
test: sse_connection_valid
steps:
  - action: open_tab
    url: http://localhost:8000/todo-bc
    
  - action: wait
    duration: 500ms
    
  - action: evaluate_js
    script: |
      // Check if SSE element has correct attribute
      const el = document.querySelector('[data-init*="@get"]');
      return {
        hasValidAttribute: !!el,
        attribute: el?.getAttribute('data-init'),
        hasOldInvalid: !!document.querySelector('[data-star-sse]')
      };
    
  - action: assert
    condition: result.hasValidAttribute === true
    message: "Should have data-init with @get(), not data-star-sse"
```

## Implementação

### Executar testes

```bash
# Com agent-browser CLI
agent-browser test e2e_multi_tab.yaml --app-url http://localhost:8000

# Ou via dogfood skill
# Usa agent-browser internamente
```

### Integração com CI

```yaml
# .github/workflows/e2e.yml
name: E2E Multi-Tab Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Start server
        run: |
          pip install -r requirements.txt
          python app.py &
          sleep 2
      
      - name: Run agent-browser tests
        run: |
          agent-browser test e2e_multi_tab.yaml \
            --app-url http://localhost:8000 \
            --report-dir ./report
      
      - name: Upload report
        uses: actions/upload-artifact@v4
        with:
          name: e2e-report
          path: ./report
```

## Benefícios

1. **Detecção de bugs reais** - O bug `data-star-sse` seria detectado
2. **Validação multi-tab** - Broadcasting testado de verdade
3. **Regressão visual** - Screenshots automáticos
4. **Console monitoring** - Erros WASM detectados
5. **CI/CD ready** - Integra com pipelines

## Próximos Passos

1. Criar arquivo `e2e_multi_tab.yaml` na POC
2. Executar testes manualmente
3. Integrar com CI quando estável