# Orquestrador híbrido com revisão obrigatória Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tornar obrigatório e recuperável o ciclo executor → revisor subagente → feedback/correção → aprovação, usando OpenCode para coordenação e `contentctl` como autoridade determinística.

**Architecture:** O runtime OpenCode carregará explicitamente o `AGENT.md` e `memory.md` corretos e disparará subagentes por `task`. O `contentctl` persistirá eventos, recibos de revisão e invariantes de rodada no SQLite, aceitando conclusão somente quando o recibo aprovado corresponder ao bloco, ciclo e artefato.

**Tech Stack:** Python 3.12+, SQLite, `unittest`/pytest existente, Markdown, OpenCode `task`, `AGENT.md`.

## Global Constraints

- O runtime deve usar o backend OpenCode nativamente via `task`; não deve exigir alteração em `config.jsonc` global.
- O runtime deve carregar explicitamente o `AGENT.md` exato do executor/revisor e o `memory.md` do revisor.
- O `contentctl` continua sendo a autoridade de estado e invariantes; ele não dispara subagentes.
- Qualquer timeout, erro, resposta ambígua, artefato ausente ou divergência de estado interrompe a rodada.
- O limite padrão é de três ciclos por bloco e deve ser configurável.
- B7 é sempre humano e nunca pode ser aprovado automaticamente.
- Não persistir valores de `.env`, tokens, credenciais ou prompts contendo segredos.
- Usar Python 3.12+ para comandos e testes: `python3.12 -m pytest ...`.

---

## Mapa de arquivos

- Modify: `src/content_ops/db.py` — migração e API transacional de eventos/recibos/estado de blocos.
- Modify: `src/content_ops/cli.py` — comandos determinísticos para iniciar ciclos, registrar revisão e concluir blocos.
- Create: `src/content_ops/orchestration.py` — validação de decisões estruturadas, ordem canônica e cálculo do próximo estado.
- Modify: `.agents/skills/orquestrador-runtime/SKILL.md` — protocolo operacional explícito para chamar `task`, carregar contratos e repetir ciclos.
- Modify: `.agents/agents/*-executor/AGENT.md` e `.agents/agents/*-revisor/AGENT.md` — padronizar saída estruturada e limites de escopo sem alterar contratos editoriais.
- Create: `tests/test_orchestration.py` — testes unitários do protocolo e da máquina de estados.
- Modify: `tests/test_db.py` — testes da migração, transações e recuperação.
- Modify: `tests/test_cli_smoke.py` — testes dos comandos e falha fechada.

### Task 1: Persistência transacional de ciclos e recibos

**Files:**
- Modify: `src/content_ops/db.py`
- Test: `tests/test_db.py`

**Interfaces:**
- Produces `Database.start_block_cycle(round_id: int, block: str, artifact_path: str) -> int`.
- Produces `Database.record_review_result(cycle_id: int, reviewer_agent: str, decision: str, result_json: str) -> None`.
- Produces `Database.review_is_approved(round_id: int, block: str, artifact_path: str, cycle: int) -> bool`.
- Produces `Database.record_workflow_event(round_id: int, block: str, event: str, payload_json: str = "{}") -> int`.
- Produces `Database.latest_block_state(round_id: int, block: str) -> sqlite3.Row | None`.

- [ ] **Step 1: Write the failing migration and transaction tests**

Add tests asserting that initialization creates `workflow_events` and `review_receipts`, both writes are durable, and an approval receipt is scoped to the same round, block, artifact, and cycle.

```python
def test_initialize_creates_orchestration_tables(self):
    with sqlite3.connect(self.path) as connection:
        tables = {row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )}
    self.assertTrue({"workflow_events", "review_receipts"} <= tables)

def test_review_approval_is_scoped_to_round_block_artifact_and_cycle(self):
    round_id = self.db.create_round("Pilar", "runtime/rodadas/1.md")
    cycle_id = self.db.start_block_cycle(round_id, "B5", "content/drafts/x.md")
    self.db.record_review_result(
        cycle_id, "cruzamento-revisor", "approved", '{"decision":"approved"}'
    )
    self.assertTrue(self.db.review_is_approved(round_id, "B5", "content/drafts/x.md", 1))
    self.assertFalse(self.db.review_is_approved(round_id, "B6", "content/drafts/x.md", 1))
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `python3.12 -m pytest tests/test_db.py -k orchestration -v`

Expected: FAIL because the tables and methods do not exist.

- [ ] **Step 3: Add schema version 7 and minimal database methods**

Increment `CURRENT_SCHEMA_VERSION`, add `_migrate_to_v7`, and create tables with foreign keys, unique `(round_id, block, cycle, artifact_path)`, decision checks limited to `approved`/`feedback`, and JSON text payloads. Keep writes inside `Database.transaction()` where approval state is read or changed.

- [ ] **Step 4: Run the focused tests and the database suite**

Run: `python3.12 -m pytest tests/test_db.py -v`

Expected: PASS with no schema regressions.

- [ ] **Step 5: Commit**

```bash
git add src/content_ops/db.py tests/test_db.py
git commit -m "feat: persist orchestration review cycles"
```

### Task 2: Deterministic state machine and fail-closed CLI

**Files:**
- Create: `src/content_ops/orchestration.py`
- Modify: `src/content_ops/cli.py`
- Test: `tests/test_orchestration.py`
- Test: `tests/test_cli_smoke.py`

**Interfaces:**
- Produces `parse_review_result(raw: str) -> ReviewResult` and raises `InvalidReviewResult` for invalid JSON/schema.
- Produces `validate_block_order(completed: set[str], requested: str) -> None` and raises `WorkflowBlocked` on skips or out-of-order blocks.
- Produces `can_complete_block(database: Database, round_id: int, block: str, artifact_path: str, cycle: int) -> None`.
- Adds CLI commands `workflow-cycle-start`, `workflow-review`, and `workflow-block-complete`.

- [ ] **Step 1: Write failing tests for structured decisions and gates**

Cover approved JSON, feedback JSON, malformed JSON, missing checks, missing artifacts, missing review receipts, out-of-order blocks, duplicate completion, and the mandatory human status for B7.

```python
def test_invalid_reviewer_json_is_rejected(self):
    with self.assertRaises(InvalidReviewResult):
        parse_review_result('{"decision":"maybe"}')

def test_block_completion_requires_matching_review_receipt(self):
    with self.assertRaises(WorkflowBlocked):
        can_complete_block(self.database, 1, "B5", "content/drafts/x.md", 1)
```

- [ ] **Step 2: Run tests to verify the expected failures**

Run: `python3.12 -m pytest tests/test_orchestration.py tests/test_cli_smoke.py -k review -v`

Expected: FAIL because the protocol module and guarded CLI commands do not exist.

- [ ] **Step 3: Implement strict parsing and state checks**

Require exactly `decision`, `artifact`, `feedback`, and `checks`; require `feedback` to be a list; require every check to have `name`, `status`, and `evidence`; accept only `approved` or `feedback`. Verify the artifact path is relative to the repository, exists, and matches the active round. Reject B7 from automatic completion.

- [ ] **Step 4: Add guarded CLI commands**

`workflow-cycle-start` records executor start and returns a cycle number. For B1-B3 it may record a future artifact path; `workflow-review` and `workflow-block-complete` require that artifact to exist and match the cycle. `workflow-review` parses and persists the reviewer receipt only after the artifact and cycle match. `workflow-block-complete` calls `can_complete_block` and records completion only after an approved receipt. The legacy `bloco-ok` command is not part of this protocol.

- [ ] **Step 5: Run focused and full tests**

Run: `python3.12 -m pytest tests/test_orchestration.py tests/test_cli_smoke.py tests/test_db.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/content_ops/orchestration.py src/content_ops/cli.py tests/test_orchestration.py tests/test_cli_smoke.py
git commit -m "feat: enforce fail-closed workflow gates"
```

### Task 3: OpenCode executor/reviewer protocol and bounded loop

**Files:**
- Modify: `.agents/skills/orquestrador-runtime/SKILL.md`
- Modify: `.agents/agents/orquestrador-runtime-executor/AGENT.md`
- Modify: `.agents/agents/orquestrador-runtime-revisor/AGENT.md`
- Modify: `.agents/agents/pilar-executor/AGENT.md`
- Modify: `.agents/agents/pilar-revisor/AGENT.md`
- Modify: `.agents/agents/pesquisa-mece-executor/AGENT.md`
- Modify: `.agents/agents/pesquisa-mece-revisor/AGENT.md`
- Modify: `.agents/agents/pesquisa-executor/AGENT.md`
- Modify: `.agents/agents/pesquisa-revisor/AGENT.md`
- Modify: `.agents/agents/cruzamento-executor/AGENT.md`
- Modify: `.agents/agents/cruzamento-revisor/AGENT.md`
- Test: `tests/test_orquestrador_runtime.py`

**Interfaces:**
- Runtime consumes the CLI commands from Task 2 and OpenCode `task`.
- Runtime requires every reviewer response to match `ReviewResult`.
- Runtime uses `ORCHESTRATOR_MAX_REVIEW_CYCLES` with default `3`; invalid or non-positive values fail closed.

- [ ] **Step 1: Add failing structural tests**

Assert that the runtime skill documents explicit `task` dispatch, exact `AGENT.md` and `memory.md` loading, cycle limits, invalid-response handling, feedback loops, and fail-closed transition commands. Assert every executor and reviewer contract specifies structured output.

- [ ] **Step 2: Run the structural tests and verify failure**

Run: `python3.12 -m pytest tests/test_orquestrador_runtime.py -v`

Expected: FAIL on the missing protocol assertions.

- [ ] **Step 3: Document the exact runtime loop**

Add a copyable procedure: call `workflow-cycle-start`; dispatch the executor with the exact contract path; run deterministic checks; dispatch the reviewer as a fresh `task` subagent with both contract files and current state; call `workflow-review`; on feedback, include the full feedback in a new executor task; stop after the configured limit; on approval call `workflow-block-complete`; then evaluate the human gate.

- [ ] **Step 4: Add machine-readable reviewer output to all agent contracts**

Keep each block's domain rules unchanged, but require the reviewer to return only the `decision/artifact/feedback/checks` `ReviewResult` schema and require the executor to report its artifact path and cycle starting at `1`. Explicitly prohibit reviewers from editing artifacts or registering their own approval.

- [ ] **Step 5: Run structural and full tests**

Run: `python3.12 -m pytest tests/test_orquestrador_runtime.py tests/test_orchestration.py tests/test_cli_smoke.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add .agents/skills/orquestrador-runtime/SKILL.md .agents/agents tests/test_orquestrador_runtime.py
git commit -m "feat: define OpenCode reviewer dispatch protocol"
```

### Task 4: Recovery, observability, and acceptance coverage

**Files:**
- Modify: `src/content_ops/orchestration.py`
- Modify: `src/content_ops/db.py`
- Modify: `src/content_ops/cli.py`
- Test: `tests/test_orchestration.py`
- Test: `tests/test_db.py`
- Modify: `docs/superpowers/specs/2026-08-29-orquestrador-hibrido-revisao-design.md`

**Interfaces:**
- Produces `resume_round(database: Database, round_id: int) -> str` returning the next safe state.
- Produces `redact_event_payload(payload: dict) -> dict` removing secret-shaped values before persistence.

- [ ] **Step 1: Write failing recovery and redaction tests**

Test restart after executor start, restart after feedback, timeout/failure events, unchanged feedback, duplicate completion, and redaction of keys matching `*_API_KEY`, `*_TOKEN`, `CT0`, `AUTH_TOKEN`, and `PASSWORD`.

- [ ] **Step 2: Run tests to verify failure**

Run: `python3.12 -m pytest tests/test_orchestration.py tests/test_db.py -k 'resume or redact or timeout or duplicate' -v`

Expected: FAIL because recovery and redaction are not implemented.

- [ ] **Step 3: Implement recovery and bounded failure handling**

Derive the next state from the latest committed event, never infer approval from missing data, detect unchanged feedback by a stable hash, and persist `failed`/`blocked` events. Redact sensitive keys recursively before storing event payloads.

- [ ] **Step 4: Add the complete acceptance matrix**

Implement tests for first-cycle approval, feedback then approval, max-cycle pause, invalid reviewer response, missing/out-of-round artifact, completion without receipt, restart, canonical order, B7 human-only behavior, and secret-free logs.

- [ ] **Step 5: Run the complete suite and inspect the diff**

Run: `python3.12 -m pytest -q` and `git diff --check`.

Expected: all tests pass and `git diff --check` is clean.

- [ ] **Step 6: Commit**

```bash
git add src/content_ops/orchestration.py src/content_ops/db.py src/content_ops/cli.py tests docs/superpowers/specs/2026-08-29-orquestrador-hibrido-revisao-design.md
git commit -m "test: cover resumable reviewer orchestration"
```

## Final verification

After all tasks, run:

```bash
python3.12 -m pytest -q
git diff --check
./contentctl --help
```

The implementation is complete only when the full suite passes and a manual smoke run demonstrates that a block cannot complete without a matching approved reviewer receipt.
