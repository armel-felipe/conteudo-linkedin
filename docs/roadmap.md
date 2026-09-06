# Roadmap do pipeline editorial

Legenda: `[x]` concluído · `[~]` parcialmente validado · `[ ]` pendente · `[!]` bloqueado.

## Estado atual

O pipeline editorial já possui descoberta, agrupamento, scoring manual, pesquisa,
brief, redação, humanização e gates de aprovação. O contrato de automação de
navegador agora prioriza **MCP Chrome DevTools** e usa **Playwright somente como
fallback**.

Última verificação do `main`:

- Node: 22 testes passaram.
- Python: 275 testes passaram.
- `compileall`: passou.
- `git diff --check`: passou.
- Nenhum segredo foi versionado.

## Planos por prioridade

### P0 — Fechar riscos e inconsistências

- [x] Oficializar as alterações locais em commit.
- [x] Integrar o branch MCP-first ao `main`.
- [x] Adicionar `runs/*` ao `.gitignore`.
- [x] Validar o contrato de rota: MCP Chrome DevTools → Playwright fallback → stop.
- [x] Comprovar uma execução browser-real via MCP Chrome DevTools em página pública
  do LinkedIn, com navegação e snapshot somente leitura; não houve Playwright nem mutação.
- [x] Registrar o incidente de agendamento: o post foi publicado em 05/09/2026
  às 21:45, em vez de ser reagendado para 07/09 às 10:00. Não é mais possível
  reagendar uma publicação já realizada.

### P1 — Próximas entregas operacionais

- [x] Confirmar o backend X em uma pesquisa real: backend `bird` acionável via
  cookies autorizados do Chrome; pesquisa retornou 30 posts em modo somente leitura.
- [x] Configurar e validar a Brave Search API; backend `brave` ativo.
- [x] Criar logs JSONL sanitizados por etapa, rota, estado e receipt em `runs/`;
  cobertura de logger Python/Node e integração de receipts concluída.
- [x] Criar scripts Python determinísticos para scoring e clustering; artefatos
  gerados em `research/topics/topics_scored_2026-09-06.yaml` e
  `research/topics/clusters_2026-09-06.yaml`.
- [ ] Executar a matriz de cenários de agendamento somente quando existir uma
  publicação real e houver autorização explícita.

### P2 — Evolução do sistema

- [ ] Criar automação recorrente após os gates P0/P1 estarem estáveis.
- [ ] Ajustar periodicamente as frentes conforme métricas de engajamento e posicionamento.
- [ ] Revisar fontes e pesos de scoring com base na qualidade observada.

## O que já foi feito

### Pipeline editorial

- [x] Descoberta de sinais e persistência em `research/signals/`.
- [x] Clusterização, temas e backlog persistente.
- [x] Brief de pesquisa com fontes, URLs e contexto do autor.
- [x] Post com estrutura editorial e seção `## Fontes`.
- [x] Duas passagens de `escrita-humana` com revisões intermediárias.
- [x] Gauntlet com executor/revisor isolados, até cinco ciclos e gates fail-closed.
- [x] Batch com fila congelada, checkpoints, retomada e falha isolada por topic.

### Contratos e segurança

- [x] Boundaries de filesystem, estado terminal e validação de receipts.
- [x] Idempotência, seleção congelada e rejeição de IDs/entradas inválidas.
- [x] Bloqueio de timestamp sem confirmação pós-ação.
- [x] Prevenção de duplicata e proibição de novo composer para reagendamento.
- [x] Contrato MCP-first em `docs/browser-route-contract.md`.
- [x] Implementação integrada em `scripts/linkedin_browser_check.js` e
  `scheduling_contract.py`.

### Evidência P0.1 — MCP Chrome DevTools

- [x] O MCP navegou até `https://www.linkedin.com/` e capturou um snapshot real.
- [x] A página estava deslogada; a evidência comprova a rota MCP, mas não uma sessão autenticada.
- [x] Nenhum clique, preenchimento, publicação ou agendamento foi executado.
- [x] A execução usou `mcp_chrome_devtools`; Playwright não foi chamado.

### Política de rota e evidência

A sequência normativa é MCP Chrome DevTools → Playwright
`playwright_fallback` → screenshot e visão nativa → `stop`. O screenshot e a
visão nativa acontecem depois das duas rotas de controle; em caso de falha, o
fluxo termina com `stop` e fail-closed.
Cada operação registra a rota, o motivo e a evidência observada.

### Receipt estruturada

```yaml
route: stop
evidence_status: simulated
fallback: none
requested_timestamp: ""
displayed_timestamp: ""
date_selected: not_run
time_selected: not_run
summary: not_run
preview: not_run
confirmation: not_run
scheduled_list: not_run
timestamp_registered: not_run
duplicate_created: false
route_attempted:
  - mcp_chrome_devtools
mcp_attempted: true
route_reasons:
  mcp_chrome_devtools: ausência de sessão autenticada para ação mutante
observed_state: public_page_read_only
verification_evidence: snapshot MCP da página pública
post_action_confirmation: not_run
```

Status auxiliar: `not_run: criação não executada por segurança`; evidência
`simulated: contrato/teste`.

### Matriz de agendamento — pendente

Quando P1-D for autorizada, a matriz deverá cobrir exatamente:

- new schedule with different date and time;
- new schedule for today with explicit date and time;
- reschedule existing post with same time and different date;
- wrong summary detected before Avançar;
- scheduled post missing from the scheduled list.

Nenhum caso será executado no post do incidente. Cada caso precisa de
evidência, receipt e confirmação do estado final antes de persistir qualquer
timestamp.
Os casos mutantes ainda não foram executados.

Operational gates: summary divergence blocks Avançar; confirmation/list absence blocks registration; never duplicate.

### Integrações

- [x] Brave Search API ativa no arquivo global do `last30days`.
- [x] X: backend `bird` validado em pesquisa real; 30 posts retornados.
- [x] `yt-dlp`, Digg, arXiv e Techmeme disponíveis.

## Documentos e planos de referência

- [x] `docs/superpowers/plans/2026-09-06-mcp-first-browser-automation.md` — implementação MCP-first concluída.
- [~] `docs/superpowers/plans/2026-09-01-linkedin-scheduling.md` — publicação e agendamento; matriz mutante ainda pendente.
- [x] `docs/browser-route-contract.md` — contrato compartilhado de navegador.
- [x] `.agents/skills/publicar-linkedin/SKILL.md` — regras operacionais do LinkedIn.
- [x] `AGENTS.md` — contrato geral do projeto.

## Histórico e evidências

Detalhes de ciclos, receipts e revisões ficam em `.superpowers/sdd/` e nos
planos específicos. O roadmap não replica esses logs: ele registra somente o
estado atual, a próxima ação e o vínculo para a evidência detalhada.

O post publicado fora do horário desejado permanece como incidente histórico;
nenhuma nova publicação deve ser criada para “corrigi-lo” sem decisão editorial
explícita.
