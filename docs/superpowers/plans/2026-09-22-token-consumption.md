# Token Consumption Reduction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** reduzir o consumo de tokens do pipeline editorial em 35–60%, medindo o custo por stage e evitando pesquisas/contextos repetidos.

**Architecture:** a telemetria opcional será adicionada aos loggers existentes, sem registrar prompts, respostas ou segredos. Um relatório agregado lerá JSONL e calculará tokens por stage, run e modelo. A pesquisa usará uma chave determinística baseada em topic, janela temporal e versão do contrato; cache válido será reutilizado, enquanto resultados degradados só serão reutilizados explicitamente.

**Tech Stack:** Python 3, Node.js, JSONL, pytest, contratos Markdown/YAML existentes.

## Global Constraints

- Não registrar prompts, respostas, URLs privadas, credenciais, cookies ou tokens secretos.
- Não remover os gates editoriais obrigatórios nem marcar `approved` automaticamente.
- Não reutilizar automaticamente uma pesquisa degradada (`Sources: none`, erro de fontes ou evidência insuficiente) como evidência nova.
- Toda métrica de custo deve ser opcional para manter compatibilidade com logs antigos.
- Toda mudança deve preservar a operação fail-closed e os contratos atuais de execução.

## Task 1: Telemetria de uso de tokens

**Files:**
- Modify: `execution_log.py`
- Modify: `scripts/execution_log.js`
- Test: `tests/test_execution_log.py`
- Test: `tests/test_execution_log_runtime.js`

**Interfaces:**
- `ExecutionLogger.emit(..., model=None, input_tokens=None, output_tokens=None, cached_input_tokens=None)` adiciona campos somente quando informados.
- `createExecutionLogger(...).emit(stage, event, options)` aceita os mesmos campos em `options`.
- Valores devem ser inteiros não negativos; uso inválido deve falhar cedo.

- [x] Escrever testes para campos válidos, omissão em logs antigos e rejeição de valores negativos/não inteiros.
- [x] Executar os testes novos e observar falhas antes da implementação.
- [x] Implementar validação e sanitização nos dois loggers.
- [x] Executar os testes Python e Node dos loggers.

## Task 2: Relatório agregado de tokens

**Files:**
- Create: `token_usage.py`
- Create: `scripts/token_usage_report.py`
- Test: `tests/test_token_usage.py`

**Interfaces:**
- `summarize_token_usage(records) -> dict` agrega `input_tokens`, `output_tokens`, `cached_input_tokens`, chamadas e custo por `run_id`, `stage` e `model`.
- CLI: `python scripts/token_usage_report.py runs/*.jsonl` imprime JSON determinístico e aceita logs legados sem uso de tokens.

- [x] Escrever testes para agregação, logs sem métricas e múltiplos modelos/stages.
- [x] Executar os testes para confirmar a falha inicial.
- [x] Implementar o agregador sem dependências externas.
- [x] Executar testes unitários e um relatório sobre `runs/browser-check.jsonl` como smoke test.

## Task 3: Cache determinístico de pesquisa

**Files:**
- Create: `research_cache.py`
- Modify: `.agents/skills/research-topic/SKILL.md`
- Test: `tests/test_research_cache.py`

**Interfaces:**
- `build_research_cache_key(topic_id, window_start, window_end, contract_version, source_config_hash) -> str` retorna SHA-256 estável.
- `cache_is_reusable(metadata, *, degraded=False) -> bool` rejeita cache degradado por padrão.
- O skill deve persistir a chave e a decisão de reuso no brief/run, sem substituir uma pesquisa cuja janela ou contrato tenha mudado.

- [x] Escrever testes para estabilidade da chave, mudança de janela/configuração e bloqueio de resultados degradados.
- [x] Executar testes para confirmar a falha inicial.
- [x] Implementar o módulo e a política documental de reuso.
- [x] Executar os testes de cache e os testes de contratos do lote editorial.

## Task 4: Compactação controlada do contexto `last30days`

**Files:**
- Create: `.agents/skills/last30days/references/editorial-compact-mode.md`
- Modify: `.agents/skills/research-topic/SKILL.md`
- Test: `tests/test_editorial_context_budget.py`

- [x] Definir um modo compacto que carregue somente instruções normativas, plano de busca, evidências ranqueadas e avisos de qualidade.
- [x] Manter o arquivo completo como referência de compatibilidade e não alterar as leis de segurança/citação.
- [x] Testar que `research-topic` aponta para o modo compacto e que a saída mantém fontes, incertezas e limites.
- [ ] Medir tamanho de contexto antes/depois em uma pesquisa A/B.

## Task 5: Reviews direcionadas e monitoramento do runtime

**Files:**
- Modify: `.agents/skills/run-editorial-batch/SKILL.md`
- Modify: `.agents/skills/critique-post/SKILL.md`
- Modify: `docs/roadmap.md`
- Test: `tests/test_batch_skill.py`

- [ ] Separar critérios substantivos por stage, sem remover `humanize_pass_1`, `humanize_review_1`, `humanize_pass_2` ou `humanize_review_2`.
- [ ] Não repetir o rubric completo de 14 critérios em stages que não produzem o draft final.
- [x] Remover a exigência de rodada A/B: a próxima execução normal será monitorada pelo `token-usage.jsonl`.
- [ ] Acompanhar tokens por draft, número de retries, coverage e hard failures na primeira rodada instrumentada.
- [ ] Atualizar a meta no roadmap somente com dados observados.

## Verification

- [ ] `pytest -q tests/test_execution_log.py tests/test_token_usage.py tests/test_research_cache.py tests/test_editorial_context_budget.py`
- [ ] `node --test tests/test_execution_log_runtime.js`
- [ ] `pytest -q`
- [ ] `git diff --check`
