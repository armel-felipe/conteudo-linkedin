# Editorial Batch Gauntlet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar a execução sequencial de 1 a X topics, com checkpoints persistentes, executores/revisores isolados e Loop Gauntlet de até 5 rodadas até aprovação ou bloqueio individual.

**Architecture:** A implantação continuará skill-driven, sem orquestrador monolítico. Uma skill de lote seleciona e congela a fila; uma skill independente de Gauntlet executa executor → validação → revisor em ciclos; as skills editoriais existentes fornecem os contratos de cada etapa. O estado persistido em `runs/` permite retomar sem depender da conversa.

**Tech Stack:** Markdown, YAML, OpenCode skills, subagentes `task`, Python 3.12+ e PyYAML apenas para validações determinísticas.

## Global Constraints

- Processar topics sequencialmente, sem paralelismo editorial.
- Selecionar de 1 a X topics, inclusive `all`, congelando a fila no início.
- Loop Gauntlet independente com máximo de 5 rodadas.
- Executor e revisor devem ser tarefas separadas e receber contexto isolado.
- Aprovar somente com cobertura de pelo menos 99% (`coverage >=0.99`) dos requisitos e nenhum critério abaixo de 9/10.
- Aplicar `escrita-humana` duas vezes, com revisor após cada passagem.
- Exigir brief revisado, duas fontes independentes quando disponíveis e conexão autoral explícita.
- Após falha terminal, marcar somente o topic atual como `blocked` e continuar.
- Não publicar nem agendar dentro do lote editorial.
- Não armazenar credenciais, cookies, tokens ou dados privados.

---

### Task 1: Contratos persistentes de execução

**Files:**
- Create: `runs/.gitkeep`
- Create: `docs/schemas/editorial-run.yaml`
- Create: `docs/schemas/gauntlet-review.json`
- Modify: `.gitignore`
- Test: `tests/test_run_contracts.py`

**Interfaces:**
- Produces the `run_id`, queue, per-topic state and review schema consumed by later tasks.

- [ ] **Step 1: Write the failing validation test**

```python
from pathlib import Path
import yaml

def test_run_schema_documents_exist_and_have_required_fields():
    run = yaml.safe_load(Path("docs/schemas/editorial-run.yaml").read_text())
    assert {"run_id", "created_at", "selection", "queue", "topics"} <= set(run)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_run_contracts.py -q`
Expected: FAIL because the schema file does not exist.

- [ ] **Step 3: Add the schemas**

`docs/schemas/editorial-run.yaml` must define:

```yaml
run_id: run_YYYYMMDD_NNN
created_at: ISO-8601
selection: "1 | N | all | comma-separated topic ids"
queue:
  - topic_id: topic_YYYYMMDD_NN
    position: 1
    status: queued
    current_stage: research
topics: {}
```

`docs/schemas/gauntlet-review.json` must define required keys `decision`, `coverage`, `criteria`, `hard_failures`, `feedback`, and `artifact`, with `decision` restricted to `approved` or `feedback`.

- [ ] **Step 4: Protect runtime artifacts**

Add `runs/*` to `.gitignore` while keeping `runs/.gitkeep` tracked. Runtime manifests remain local unless explicitly exported.

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m pytest tests/test_run_contracts.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add .gitignore runs/.gitkeep docs/schemas tests/test_run_contracts.py
git commit -m "feat: define editorial run and gauntlet contracts"
```

---

### Task 2: Skill de lote e seleção de topics

**Files:**
- Create: `.agents/skills/run-editorial-batch/SKILL.md`
- Modify: `mapa.md`
- Modify: `README.md`
- Test: `tests/test_batch_skill.py`

**Interfaces:**
- Consumes: `content/backlog.md`, `research/topics/topics_*.yaml`.
- Produces: `runs/<run_id>/manifest.yaml` and per-topic queue state.

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

def test_batch_skill_documents_selection_and_failure_policy():
    text = Path(".agents/skills/run-editorial-batch/SKILL.md").read_text()
    assert "--topics all" in text
    assert "sequencial" in text
    assert "blocked" in text
    assert "continuar" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_batch_skill.py -q`
Expected: FAIL because the skill does not exist.

- [ ] **Step 3: Write the skill**

The skill must define:

```text
--topics 1
--topics N
--topics all
--topics topic_a,topic_b
```

It must resolve only `ready_for_research`, sort by score unless explicit ids are supplied, freeze the queue, process one topic at a time, resume from the last valid checkpoint, and mark a failed topic `blocked` before continuing to the next queue item.

The skill must call the stage skills in this order for every topic:

```text
research-topic → brief review Gauntlet → write-post → critique-post
→ correction Gauntlet → escrita-humana 1 → review
→ escrita-humana 2 → review → approval humana
```

It must never call `publicar-linkedin`.

- [ ] **Step 4: Update discovery documentation**

Add `run-editorial-batch` to `mapa.md`, update the README sequence and document that this is the new batch entry point while `orquestrador-runtime` remains legacy.

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m pytest tests/test_batch_skill.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add .agents/skills/run-editorial-batch mapa.md README.md tests/test_batch_skill.py
git commit -m "feat: add sequential editorial batch skill"
```

---

### Task 3: Procedimento independente Loop Gauntlet

**Files:**
- Create: `.agents/skills/gauntlet-loop/SKILL.md`
- Modify: `mapa.md`
- Test: `tests/test_gauntlet_skill.py`

**Interfaces:**
- Consumes: executor contract, reviewer contract, artifact path and feedback.
- Produces: cycle review files and terminal result `approved` or `blocked`.

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

def test_gauntlet_defines_five_round_limit_and_hard_gate():
    text = Path(".agents/skills/gauntlet-loop/SKILL.md").read_text()
    assert "5 rodadas" in text
    assert "99%" in text
    assert "9/10" in text
    assert "executor" in text and "revisor" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_gauntlet_skill.py -q`
Expected: FAIL because the skill does not exist.

- [ ] **Step 3: Write the independent procedure**

Document the exact cycle:

```text
cycle-start → executor → deterministic checks → fresh reviewer
→ structured result → approve or feedback → next cycle
```

Require fresh `task` calls for executor and reviewer, valid JSON review, complete feedback on retries, a maximum of five cycles, `coverage >= 0.99`, and all criteria at least 9/10. Invalid output, missing artifact or failed validation must be fail-closed.

- [ ] **Step 4: Add terminal failure behavior**

After cycle 5 without approval, write `blocked` with failure reasons, failed criteria, last artifact and cycle count. The caller, not the Gauntlet, decides to continue the batch queue.

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m pytest tests/test_gauntlet_skill.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add .agents/skills/gauntlet-loop mapa.md tests/test_gauntlet_skill.py
git commit -m "feat: add independent editorial gauntlet loop"
```

---

### Task 4: Brief review and author-context gates

**Files:**
- Modify: `.agents/skills/research-topic/SKILL.md`
- Modify: `.agents/skills/write-post/SKILL.md`
- Modify: `AGENTS.md`
- Test: `tests/test_editorial_gates.py`

**Interfaces:**
- Extends the brief and writing contracts consumed by `gauntlet-loop` and `run-editorial-batch`.

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

def test_research_and_write_contracts_require_quality_gates():
    research = Path(".agents/skills/research-topic/SKILL.md").read_text()
    write = Path(".agents/skills/write-post/SKILL.md").read_text()
    assert "duas fontes independentes" in research
    assert "conexão" in research
    assert "9/10" in write
    assert "escrita-humana" in write
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_editorial_gates.py -q`
Expected: FAIL because the new gates are absent.

- [ ] **Step 3: Add mandatory brief gates**

Require two independent sources when available, primary-source coverage or an explicit reason for absence, all front research questions, explicit author connection, limitations, and Gauntlet approval before `researched`.

- [ ] **Step 4: Add mandatory post gates**

Add the 14 criteria, all criteria `>= 9/10`, coverage `>=99%`, and the two-pass human-writing sequence with reviewer after each pass. State that hard failures override the aggregate 95% human-writing score.

- [ ] **Step 5: Update AGENTS.md**

Document the batch entry point, Gauntlet policy, individual `blocked` continuation and two mandatory `escrita-humana` passes.

- [ ] **Step 6: Run test to verify it passes**

Run: `python3 -m pytest tests/test_editorial_gates.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add .agents/skills/research-topic .agents/skills/write-post AGENTS.md tests/test_editorial_gates.py
git commit -m "feat: enforce brief and post quality gates"
```

---

### Task 5: Persistência, retomada e integração documental

**Files:**
- Modify: `.agents/skills/run-editorial-batch/SKILL.md`
- Modify: `.agents/skills/gauntlet-loop/SKILL.md`
- Modify: `README.md`
- Modify: `docs/roadmap.md`
- Test: `tests/test_documentation_consistency.py`

**Interfaces:**
- Consumes: schemas from Task 1 and contracts from Tasks 2–4.
- Produces: documented resumability and acceptance checklist.

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

def test_docs_reference_same_batch_and_gauntlet_names():
    files = [Path("README.md"), Path("mapa.md"), Path("AGENTS.md")]
    text = "\n".join(p.read_text() for p in files)
    assert "run-editorial-batch" in text
    assert "gauntlet-loop" in text
    assert "escrita-humana" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_documentation_consistency.py -q`
Expected: FAIL until all documentation is synchronized.

- [ ] **Step 3: Document checkpoints and resume rules**

Specify that every stage writes an event, every reviewer result is saved per cycle, and a resumed run skips only stages with valid artifacts and passing reviews. Never rerun an approved topic automatically.

- [ ] **Step 4: Document metrics**

Add queue size, completed, blocked, cycles per stage, reviewer coverage, human-writing conformity and time-to-approval to the run manifest.

- [ ] **Step 5: Run all tests**

Run: `python3 -m pytest tests -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add .agents/skills/run-editorial-batch .agents/skills/gauntlet-loop README.md docs/roadmap.md tests
git commit -m "docs: document resumable editorial batch execution"
```

## Plan self-review

- Batch selection and sequential execution: Tasks 2 and 5.
- Independent Gauntlet with executor/reviewer, five cycles and 99% gate: Task 3.
- Brief review, sources and author connection: Task 4.
- Two `escrita-humana` passes and 9/10 criteria: Task 4.
- Individual blocking and continuation: Tasks 2 and 3.
- Persistent manifests and resume: Tasks 1 and 5.
- Scheduling remains outside this plan and is covered by the separate LinkedIn plan.
- No placeholders remain; every task has files, tests, commands and expected results.
