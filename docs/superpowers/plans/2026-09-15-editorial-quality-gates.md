# Editorial Quality Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fazer o pipeline rejeitar reviews formais sem evidência editorial de contexto, coesão e decisão.

**Architecture:** Estender o contrato de review com um bloco opcional-obrigatório por tipo de artefato, validado por `gauntlet_loop`; `editorial_batch` aplicará a validação antes de persistir. Documentação, roadmap e testes usarão o mesmo contrato.

**Tech Stack:** Python 3.12, PyYAML, pytest, Markdown/YAML.

**Spec:** `docs/superpowers/specs/2026-09-15-editorial-quality-gates-design.md`

## Global Constraints

- O fluxo canônico continua com nove stages.
- `approved` continua sendo decisão humana no QA.
- Nenhuma review pode ser fabricada pelo executor.
- Todo draft deve terminar com `## Fontes`.
- Falha editorial bloqueia o topic no stage atual.

---

### Task 1: Contrato substantivo de review

**Files:**
- Modify: `gauntlet_loop.py`
- Test: `tests/test_batch_skill.py`

**Interfaces:**
- Produces `validate_review(review, artifact_content=None, artifact_kind=None)` com erro explícito para evidência editorial ausente.

- [ ] Escrever teste para rejeitar review 10/10 sem `evidence`.
- [ ] Escrever teste para aceitar review com `evidence` contendo contexto, linha causal, decisão, consequência e limites.
- [ ] Implementar validação determinística dos campos e mensagens não vazias.
- [ ] Rodar `python3.12 -m pytest -q tests/test_batch_skill.py`.

### Task 2: Aplicar o contrato no executor

**Files:**
- Modify: `editorial_batch.py`
- Test: `tests/test_batch_skill.py`

**Interfaces:**
- `persist_stage` lê o artefato e passa seu conteúdo à validação; reviews não substantivas não são persistidas.

- [ ] Escrever teste de `persist_stage` que bloqueia review genérica.
- [ ] Implementar a chamada ao validador substantivo sem alterar a idempotência existente.
- [ ] Manter o compartilhamento legítimo do artefato entre stages sem aceitar resultados/reviews órfãos.
- [ ] Rodar a suíte específica e verificar os estados de checkpoint.

### Task 3: Documentação e roadmap

**Files:**
- Modify: `docs/roadmap.md`
- Modify: `.agents/skills/run-editorial-batch/SKILL.md`
- Modify: `.agents/skills/critique-post/SKILL.md`
- Modify: `.agents/skills/qa-draft/SKILL.md`

- [ ] Registrar a pendência ativa e o critério de conclusão no roadmap.
- [ ] Documentar o contrato de evidência e o comportamento fail-closed nas skills.
- [ ] Rodar os testes de consistência documental.

### Task 4: Reclassificar e corrigir drafts da rodada

**Files:**
- Modify: `research/topics/topics_2026-09-15.yaml`
- Modify: `content/drafts/topic_20260915_09.md`
- Modify: `content/drafts/topic_20260915_06.md`
- Modify: `content/drafts/topic_20260915_02.md`

- [ ] Marcar os três topics como necessitando revisão editorial, sem aprová-los.
- [ ] Reescrever topic 09 com uma evidência principal autocontida e transições causais.
- [ ] Rodar crítica substantiva nos três drafts e verificar caracteres, fontes e pergunta final.
