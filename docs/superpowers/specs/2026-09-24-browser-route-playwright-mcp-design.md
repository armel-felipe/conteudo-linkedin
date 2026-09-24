# Design — Rota de browser com Playwright MCP

Data: 2026-09-24
Status: aprovado

## Problema

O projeto removeu o MCP `chrome-devtools` do `opencode.jsonc` e instalou o
Playwright MCP (`@playwright/mcp`). O código vigente ainda carrega resíduos da
era "MCP-first" e o contrato de rota mistura duas dimensões independentes:

1. **Rota de browser** — quem opera o navegador.
2. **Modo de visão** — quem lê a tela.

Hoje `image-analyzer` é tratado como um passo da cadeia de browser, o que
impede que ele funcione como fallback de visão de qualquer rota. Além disso,
`docs/schemas/linkedin-scheduling-checklist.yaml` declara
`browser_route: mcp_chrome_devtools`, um nome fora do vocabulário normativo e
em contradição com `route_attempted: [browser_native]` no mesmo arquivo.

## Objetivo

Substituir o chrome-devtools MCP pelo Playwright MCP no código vigente,
preservando a rota visual-first, e separar rota de browser de modo de visão.

## Decisões

### D1 — Duas dimensões independentes

| Dimensão | Pergunta | Valores |
|---|---|---|
| Rota de browser | Quem opera o navegador? | `browser_native` · `playwright_mcp` · `playwright` · `stop` |
| Modo de visão | Quem lê a tela? | `native` · `image-analyzer` |

### D2 — Cadeia de browser (sequencial)

```text
browser_native → playwright_mcp → playwright → stop
```

- `browser_native`: CUA embedded browser + screenshot. Rota primária em host
  com browser embutido (Desktop).
- `playwright_mcp`: Playwright MCP
  (`@playwright/mcp --cdp-endpoint http://127.0.0.1:9223`). Rota primária em
  host sem browser embutido (CLI). Substitui o chrome-devtools MCP.
- `playwright`: script read-only via CDP (`scripts/linkedin_browser_check.js`).
  Diagnóstico.
- `stop`: fail-closed.

### D3 — Modo de visão (ortogonal)

- `native`: o modelo lê o screenshot direto.
- `image-analyzer`: delega a leitura quando não há visão nativa
  (`no_native_vision`) ou ela falha (`native_failed`).

O `image-analyzer` lê o screenshot de **qualquer** rota de browser que tenha
funcionado. Não é passo da cadeia de browser.

### D4 — Vocabulário do receipt

- `route`: `browser_native | playwright_mcp | playwright | stop`
- `vision`: `native | image-analyzer`
- `route_attempted`: lista ordenada de rotas de browser tentadas
- `vision_fallback_reason`: `no_native_vision | native_failed | null`

### D5 — Checklist alinhado

`docs/schemas/linkedin-scheduling-checklist.yaml` passa a usar
`browser_route: browser_native` (nome normativo), eliminando a contradição com
`route_attempted`.

### D6 — Migração do contrato de eventos

Hoje `image_analyzer` é um valor de rota em `validate_schedule_events(events,
route)` e uma chave de `_VISUAL_BRANCHES`. Com D1–D3, ele deixa de ser rota.

- `validate_schedule_events(events, route)`: `route` passa a aceitar somente
  rotas de browser (`browser_native`, `playwright_mcp`, `playwright`) mais o
  caso terminal `unreadable_image`.
- `_VISUAL_BRANCHES` → `_BROWSER_BRANCHES`, com chaves `browser_native`,
  `playwright_mcp`, `playwright`.
- Eventos de visão (`image-analyzer:reason=...`) deixam de ser eventos de rota e
  passam a ser validados pelo campo `vision` do receipt.
- Novo evento de tentativa `playwright_mcp_attempt`, análogo a
  `playwright_attempt`.
- `_RECEIPT_ROUTES` passa a `{browser_native, playwright_mcp, playwright, stop}`.
- `_RECEIPT_FALLBACKS` passa a `{none, browser_native, playwright_mcp,
  playwright}`.
- `validate_reschedule_events(...)`: `effective_route` aceita `playwright_mcp`;
  a evidência de fallback de visão é validada por `vision`, não por rota.

Os testes que hoje parametrizam `route="image_analyzer"` migram para o eixo de
visão; os que parametrizam `route="playwright"` permanecem, e ganham o caso
`playwright_mcp`.

## Arquivos afetados

### Normativos

- `docs/browser-route-contract.md` — linha da rota, nomes normativos, seções de
  leitura e mutação, registro mínimo.
- `.agents/skills/publicar-linkedin/SKILL.md` — linha da rota, passos, contrato
  comportamental, distinção explícita entre Playwright read-only (script CDP) e
  Playwright MCP (mecanismo de host).
- `AGENTS.md` — regra de rota obrigatória.
- `README.md`, `mapa.md`, `docs/roadmap.md`, `docs/fluxo-operacao.md` — mesma
  linha de rota.

### Código

- `scheduling_contract.py` — vocabulário de rotas, sequências de eventos,
  validação de receipt.
- `scripts/linkedin_browser_check.js` — `browserRouteOrder()`,
  `visualFallbackOrder()`, resolução de rota.
- `docs/schemas/linkedin-scheduling-checklist.yaml` — `browser_route`.

### Testes

- `tests/test_browser_route_contract.py`
- `tests/test_browser_route_documentation.py`
- `tests/test_scheduling_contract_visual.py`
- `tests/test_scheduling_skill.py`
- `tests/linkedin_browser_check.test.js`
- `tests/test_browser_route_runtime.js`

## Fora de escopo

- Histórico (`docs/superpowers/plans|specs`, `.superpowers/sdd`,
  `.worktrees/`, `runs/`) — não normativo, permanece como está.
- Worktree `mcp-first-browser-automation` — remoção é decisão separada.

## Critérios de sucesso

1. Nenhum arquivo vigente menciona `chrome-devtools` ou `mcp_chrome_devtools`,
   exceto a guarda de regressão em `tests/test_browser_route_documentation.py`.
2. `docs/browser-route-contract.md` declara a cadeia
   `browser_native → playwright_mcp → playwright → stop` e o modo de visão
   ortogonal.
3. `scheduling_contract.py` aceita `playwright_mcp` no vocabulário de rotas e
   rejeita `mcp_chrome_devtools`.
4. `docs/schemas/linkedin-scheduling-checklist.yaml` usa `browser_route:
   browser_native` e não contradiz `route_attempted`.
5. A suíte de testes passa (Python e Node).
6. `validate_schedule_events` rejeita `image_analyzer` como rota e aceita
   `playwright_mcp`; o modo de visão é validado pelo campo `vision` do receipt.
