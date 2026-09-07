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
- [x] Executar um cenário real de novo agendamento de publicação com autorização
  explícita: `topic_20260901_03` confirmado para 08/09/2026 às 10:00 (BRT), via
  MCP Chrome DevTools, com confirmação na lista de publicações agendadas.
- [x] Matriz de agendamento validada: novo agendamento hoje às
  22:00 e reagendamento da mesma publicação para 10/09/2026 às 10:00 foram
  confirmados na lista; os dois cenários negativos foram validados pelos
  contratos locais, sem mutação adicional no LinkedIn.

### P2 — Evolução do sistema

#### P2.1 — Automação recorrente

- [~] Definir o escopo mínimo da rodada automática: descoberta de sinais,
  clusterização e seleção de topics `ready_for_research`.
- [~] Definir frequência, timezone, modelo e local dos artefatos persistentes.
- [x] Definir os gates que permanecem humanos: aprovação do brief, escrita,
  humanização e autorização de publicação/agendamento.
- [!] Não criar nem ativar uma Automation enquanto a execução depender de o
  OpenWork Desktop, o runner e o workspace permanecerem disponíveis. A
  limitação foi registrada; não há automação ativa.
- [ ] Executar um piloto com uma fila congelada e verificar manifest, checkpoints,
  falha isolada e retomada.
- [ ] Registrar o resultado do piloto, incluindo tempo, cobertura e falhas.

**Decisão atual:** P2.1 está adiado. O sistema de Automations disponível não
oferece, neste momento, garantia suficiente de execução independente do Desktop
e do workspace. Retomar somente quando houver um runner hospedado/independente,
ou quando a limitação for explicitamente aceita.

#### P2.2 — Aprendizado por métricas — excluído

- [!] Excluído do plano ativo: a coleta manual ou assistida de métricas não
  demonstrou benefício proporcional ao custo e à complexidade.
- [x] Registrar a decisão de não criar planilha, rotina de coleta ou nota
  qualitativa obrigatória para cada post.

#### P2.3 — Scoring e fontes

- [x] Auditar a qualidade das fontes por tipo, independência, recência,
  verificabilidade e conexão com a experiência do autor.
- [x] Comparar score previsto com decisões e qualidade observadas; o resultado
  preditivo permanece inconclusivo.
- [x] Propor alterações de pesos somente com amostra e justificativa documentadas;
  a decisão de 2026-09-06 foi `inconclusive`, sem alteração.
- [x] Rodar scoring antigo e novo em paralelo antes de substituir a versão ativa;
  a comparação permaneceu inconclusiva.
- [x] Registrar a decisão, a data, a justificativa, as limitações e o impacto
  deliberadamente mantido em `research/audits/scoring-decision-2026-09-06.md`.

**Decisão P2.3 (2026-09-06):** `inconclusive` / `keep_current`. A amostra de
cinco tópicos não tem resultados comparáveis, apresenta `author_fit: 0` em todos
os itens e a alternativa troca apenas as posições 2 e 3. Os pesos ativos e a
fórmula permanecem inalterados. Nova alteração ou experimento alternativo exige
aprovação humana explícita.

#### Critérios de saída do P2

- [ ] Uma automação piloto executada com aprovação humana e sem publicação
  automática.
- [x] Uma revisão de frentes e pesos baseada em evidência, não em impressão
  isolada.
- [x] Cada decisão registra o que foi aprendido, o que mudou e o que foi
  deliberadamente mantido.

### Decisões e limitações do P2

- [x] Excluir o P2.2 de métricas de posts: muitas métricas, medição manual e
  baixo vínculo comprovado com decisões de construção de conteúdo criariam
  trabalho operacional sem aprendizado confiável.
- [x] Não automatizar o pipeline editorial por enquanto: a dependência de
  Desktop/runner/workspace torna a execução diária pouco confiável para este
  projeto.
- [ ] Reavaliar a automação quando a plataforma oferecer execução hospedada ou
  um runner independente com estado e logs persistentes.

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

### Matriz de agendamento — validada

Quando novos cenários P1-D forem autorizados, a matriz deverá cobrir exatamente:

- new schedule with different date and time;
- new schedule for today with explicit date and time;
- reschedule existing post with same time and different date;
- wrong summary detected before Avançar;
- scheduled post missing from the scheduled list.

Os cenários de nova publicação com data/hora explícitas e de reagendamento de
publicação existente foram executados com `topic_20260901_04`. Cada caso
precisa de evidência, receipt e confirmação do estado final antes de persistir
qualquer timestamp. O post do incidente não foi utilizado.
Os dois cenários negativos ainda não foram executados no browser, pois isso exigiria
criar uma condição artificial ou arriscar uma mutação desnecessária; os gates
correspondentes foram cobertos por testes locais determinísticos.
Os testes locais dos gates de resumo divergente e ausência na lista passaram
(`106 passed`); não houve mutação adicional no LinkedIn.

Operational gates: summary divergence blocks Avançar; confirmation/list absence blocks registration; never duplicate.

### Aprendizados acumulados

- [x] Agendamento exige confirmar data e hora depois de mudar a data; o LinkedIn
  pode manter o horário anterior silenciosamente.
- [x] Reagendamento deve usar `Alterar agenda` na publicação existente; abrir um
  novo composer cria risco de duplicata.
- [x] A confirmação visual na lista de publicações agendadas é o gate independente
  mais forte; toast isolado não basta para registrar timestamp.
- [x] Fontes comerciais e painéis sustentam a existência de um debate, mas não
  comprovam adoção industrial, escala ou resultado operacional.
- [x] A automação editorial precisa congelar a fila e persistir checkpoints para
  que uma falha de um topic não contamine os demais.
- [ ] Revisar estes aprendizados após o primeiro piloto de automação e após uma
  nova amostra comparável de decisões editoriais e qualidade de fontes.

### Integrações

- [x] Brave Search API ativa no arquivo global do `last30days`.
- [x] X: backend `bird` validado em pesquisa real; 30 posts retornados.
- [x] `yt-dlp`, Digg, arXiv e Techmeme disponíveis.

## Documentos e planos de referência

- [x] `docs/superpowers/plans/2026-09-06-mcp-first-browser-automation.md` — implementação MCP-first concluída.
- [x] `docs/superpowers/plans/2026-09-01-linkedin-scheduling.md` — publicação,
  agendamento e validação determinística dos cenários negativos concluídos.
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
