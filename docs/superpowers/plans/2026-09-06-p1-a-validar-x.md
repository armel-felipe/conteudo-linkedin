# P1-A — Validar X em pesquisa real

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Confirmar, com uma pesquisa real e somente leitura, se o backend X do `last30days` retorna evidências utilizáveis.

**Architecture:** Usar o primeiro topic `ready_for_research` existente, `topic_20260901_03`, sem alterar seu estado antes do resultado. O preflight e o engine produzem a evidência; um relatório sanitizado registra status, contagem, limitações e próximo passo. Nenhum conteúdo de LinkedIn será publicado ou modificado.

**Tech Stack:** Python 3.12+, `last30days.py`, Brave Search API configurada, cookies locais do Chrome para X, YAML, Markdown.

## Global Constraints

- Usar um tópico já existente no backlog.
- Executar pesquisa somente de leitura.
- Não publicar, seguir contas, enviar mensagens ou alterar qualquer conteúdo.
- Nunca registrar `AUTH_TOKEN`, `CT0`, cookies, API keys ou conteúdo privado em chat, Git ou relatório.
- Se X estiver `unconfigured`, `auth-failed`, `rate-limited`, `timeout` ou outro estado não acionável, marcar P1-A como `blocked` sem executar o engine e sem produzir receipt; registrar apenas `doctor live + report sanitizado + roadmap bloqueado`.
- Executar o engine e exigir receipt somente quando o preflight fornecer backend X acionável. Nunca executar o engine para contornar um preflight não acionável ou produzir pesquisa enganosa.
- Atualizar `docs/roadmap.md` somente depois da evidência desta execução.

---

### Task 1: Preflight seguro e seleção congelada do topic

**Files:**
- Read: `research/topics/topics_2026-09-01.yaml`
- Read: `content/backlog.md`
- Create: `research/briefs/p1-a-x-validation-2026-09-06.md`

**Interfaces:**
- Consumes: `topic_20260901_03` (`status: ready_for_research`).
- Produces: registro da seleção, versão do engine, data, flags de execução e resultado do `doctor`, sem valores secretos.

- [ ] **Step 1: Confirm the selected topic**

Confirm that `topic_20260901_03` remains the first eligible `ready_for_research` topic and record its title and id in the report. Do not change its YAML status.

- [ ] **Step 2: Run the configuration doctor without exposing secrets**

Run:

```bash
python3.12 /Users/mac/.agents/skills/last30days/scripts/last30days.py doctor --json
```

Save only the redacted source statuses in the report. Never copy the JSON wholesale when it contains paths, credentials or account details.

- [ ] **Step 3: Decide whether the test can proceed**

Proceed only if the doctor or runtime preflight provides an actionable X backend. If it reports X as `unconfigured`, `auth-failed`, `rate-limited`, `timeout` or another non-actionable status, record the exact stable status, stop P1-A as `blocked`, do not run the engine, do not produce an engine receipt, and continue only with the sanitized report and blocked roadmap update.

---

### Task 2: Execute one real, read-only research pass

**Files:**
- Read: `research/topics/topics_2026-09-01.yaml`
- Create: engine output under `${LAST30DAYS_MEMORY_DIR}` (runtime artifact, not committed)
- Modify: `research/briefs/p1-a-x-validation-2026-09-06.md`

**Interfaces:**
- Consumes: selected topic and actionable local X/browser configuration from Task 1.
- Produces: raw engine receipt plus a sanitized report containing source status and evidence counts, only when the backend is actionable.

- [ ] **Step 1: Resolve the required runtime interpreter**

Run this step only after Task 1 confirms an actionable X backend. Set `LAST30DAYS_PYTHON` to a discovered Python 3.12+ interpreter and verify:

```bash
python3.12 -c 'import sys; assert sys.version_info >= (3, 12)'
```

For a non-actionable preflight, skip this step and do not run the engine.

- [ ] **Step 2: Generate the named-topic research plan**

Only with an actionable X backend, write a temporary JSON plan for `topic_20260901_03` containing the topic title, its central question, its thesis, an X lane using the configured account/session, and the required non-X lanes. Do not put cookies or API keys in the JSON plan. Skip this step when P1-A is blocked by preflight.

- [ ] **Step 3: Run the engine with the plan and native search**

Only with an actionable X backend, run the engine with the generated plan, `--emit=json`, `--save-dir="$LAST30DAYS_MEMORY_DIR"`, and `LAST30DAYS_NATIVE_SEARCH=1` because Brave Search is available. Use the normal source preflight flags required by the engine. Do not use `--mock`, WebSearch-only synthesis, or any mutating X operation. If preflight is non-actionable, do not run the engine and do not create a receipt.

- [ ] **Step 4: Capture only safe results**

When the engine ran, record in the report:

```text
status: confirmed | partial | blocked
x_source_status: <engine status>
x_evidence_count: <integer>
other_source_statuses: <names and statuses only>
route: read_only
mutations: none
limitations: <short factual statement>
```

When preflight blocked the run, record the sanitized doctor status instead, with `status: blocked`, `route: read_only`, `mutations: none`, and a factual limitation explaining that no engine receipt was produced. Do not copy raw cookies, authorization headers, private profile data or complete raw payloads into the report.

---

### Task 3: Close P1-A and update the roadmap

**Files:**
- Modify: `research/briefs/p1-a-x-validation-2026-09-06.md`
- Modify: `docs/roadmap.md`

**Interfaces:**
- Consumes: doctor output and, when the backend is actionable, the real engine receipt from Task 2.
- Produces: final P1-A status and a single actionable next step.

- [ ] **Step 1: Apply the outcome rule**

Mark `confirmed` only when the actionable preflight was followed by a successful X source run that returned at least one usable, current evidence item. Mark `partial` for incomplete but non-empty coverage after an actionable preflight. Mark `blocked` for non-actionable preflight states (`unconfigured`, `auth-failed`, `rate-limited`, `timeout` or other errors), or for zero usable X evidence after an engine run. A blocked preflight is valid without an engine receipt.

- [ ] **Step 2: Update the roadmap from evidence**

Change only the P1-A line in `docs/roadmap.md`:

```text
[x] Confirmar o backend X em uma pesquisa real: ...
```

only for `confirmed`; otherwise use `[~]` or `[!]` and include the exact next action. Do not mark X complete based only on cookies found by setup. For a blocked preflight, the next action must address the reported doctor status; do not imply that the engine ran or that X was validated.

- [ ] **Step 3: Verify no secrets or mutations were recorded**

Run:

```bash
git diff --check
git status --short
```

Review the report and staged diff for tokens, cookies, authorization headers, private profile data, or claims unsupported by the receipt. For a blocked preflight, verify that the report contains no claim of an engine run or engine receipt.

- [ ] **Step 4: Commit the durable report and roadmap change**

```bash
git add research/briefs/p1-a-x-validation-2026-09-06.md docs/roadmap.md
git commit -m "research: validate X source for P1"
```

Do not commit the raw `${LAST30DAYS_MEMORY_DIR}` output unless the repository policy explicitly requires that artifact and it has been scrubbed.

## Acceptance criteria

- The selected topic is `topic_20260901_03` or a newer first eligible topic, recorded by id.
- When the preflight provides an actionable X backend, the engine runs exactly once with a named-topic plan and produces a receipt, not WebSearch-only. When the doctor reports X `unconfigured`, `auth-failed`, `rate-limited`, `timeout` or another non-actionable state, `blocked` is valid with no engine run and no engine receipt; the exception is `doctor live + report sanitizado + roadmap bloqueado`.
- X outcome is classified from the engine receipt when the engine ran, or from the sanitized live doctor status for a blocked preflight; it is never inferred from setup messages.
- The operation was read-only and made no LinkedIn/X mutations.
- The report contains no secrets or private session data.
- The roadmap has one accurate P1-A status and one concrete next action.
