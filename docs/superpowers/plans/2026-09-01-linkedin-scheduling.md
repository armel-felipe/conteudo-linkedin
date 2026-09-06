# LinkedIn Scheduling Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tornar o agendamento e reagendamento do LinkedIn verificáveis, usando Playwright primeiro e fallback visual seguro quando houver ausência ou dificuldade.

**Architecture:** A skill separada recebe somente arquivos em `content/approved/`. Ela converte o Markdown, controla a sessão já autenticada, valida cada estado visual e registra o horário somente depois de confirmar a publicação em “Publicações agendadas”. Reagendamento altera a publicação existente por `... → Alterar agenda`, sem criar duplicata.

**Tech Stack:** OpenCode skills, Playwright quando disponível, browser/CDP do OpenWork como fallback operacional, screenshots, visão nativa e `image-analyzer` com `reason: native_failed`.

## Global Constraints

- Usar somente sessão já autenticada; nunca ler ou armazenar credenciais.
- Validar arquivo em `content/approved/` antes de qualquer ação.
- Tentar Playwright como primeira rota de visualização/controle.
- Se Playwright estiver ausente ou difícil, capturar screenshot e usar visão nativa primeiro.
- Se a visão nativa falhar, usar `image-analyzer` com `reason: native_failed`.
- Nunca inferir estado sem evidência visual.
- Confirmar exatamente data e hora antes de avançar.
- Ao reagendar, selecionar novamente data e horário, mesmo que o horário seja igual.
- Confirmar a publicação em “Publicações agendadas” antes do registro local.
- Nunca criar uma segunda publicação para corrigir horário.

---

### Task 1: Atualizar o contrato da skill

**Files:**
- Modify: `.agents/skills/publicar-linkedin/SKILL.md`
- Modify: `mapa.md`
- Modify: `README.md`
- Test: `tests/test_scheduling_skill.py`

**Interfaces:**
- Consumes: `content/approved/<file>.md` and requested date/time.
- Produces: verified LinkedIn scheduling and timestamp comment in the approved file.

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

def test_scheduling_skill_contains_visual_and_reschedule_contract():
    text = Path(".agents/skills/publicar-linkedin/SKILL.md").read_text()
    for phrase in ["Playwright", "image-analyzer", "Alterar agenda", "selecionar novamente", "Publicações agendadas"]:
        assert phrase in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_scheduling_skill.py -q`
Expected: FAIL because Playwright-first and repeat-selection rules are not fully documented.

- [ ] **Step 3: Add the route order**

Document this exact order:

```text
Playwright → screenshot + visão nativa → image-analyzer(native_failed) → stop
```

The fallback must not be described as a substitute for visual evidence.

- [ ] **Step 4: Add scheduling and rescheduling rules**

Require explicit selection of date and time, including re-selecting the time after changing the date. Require visual confirmation of the summary before “Avançar”, visual confirmation of the final preview before “Agendar”, and verification in the scheduled-post list.

For existing scheduled posts, require `... → Alterar agenda`, then repeat date and time selection. Never open a fresh composer to correct an existing post.

- [ ] **Step 5: Update README and mapa**

Document Playwright as the first attempt, fallback routing and the distinction between editorial approval and operational scheduling.

- [ ] **Step 6: Run test to verify it passes**

Run: `python3 -m pytest tests/test_scheduling_skill.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add .agents/skills/publicar-linkedin/SKILL.md mapa.md README.md tests/test_scheduling_skill.py
git commit -m "feat: harden LinkedIn scheduling verification"
```

---

### Task 2: Add deterministic scheduling checklist

**Files:**
- Create: `docs/schemas/linkedin-scheduling-checklist.yaml`
- Modify: `.agents/skills/publicar-linkedin/SKILL.md`
- Test: `tests/test_scheduling_checklist.py`

**Interfaces:**
- Produces a checklist consumed by the scheduling skill before timestamp registration.

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path
import yaml

def test_checklist_has_required_verification_steps():
    data = yaml.safe_load(Path("docs/schemas/linkedin-scheduling-checklist.yaml").read_text())
    required = {"approved_file", "content_converted", "date_time_confirmed", "final_preview_confirmed", "scheduled_list_confirmed"}
    assert required <= set(data)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_scheduling_checklist.py -q`
Expected: FAIL because the checklist does not exist.

- [ ] **Step 3: Create the checklist**

Use this structure:

```yaml
approved_file: false
content_converted: false
browser_route: playwright
fallback_used: none
date_time_confirmed: false
final_preview_confirmed: false
scheduled_list_confirmed: false
reschedule_existing_post: false
timestamp_registered: false
```

The skill must prohibit `timestamp_registered: true` unless `scheduled_list_confirmed: true`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_scheduling_checklist.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docs/schemas/linkedin-scheduling-checklist.yaml .agents/skills/publicar-linkedin/SKILL.md tests/test_scheduling_checklist.py
git commit -m "feat: add LinkedIn scheduling verification checklist"
```

---

### Task 3: Verify the real workflow manually

**Files:**
- Modify: `docs/roadmap.md`
- Test: `tests/test_scheduling_skill.py`

**Interfaces:**
- Consumes the updated skill and an approved test post.
- Produces a documented manual verification receipt without storing private session data.

- [ ] **Step 1: Add the manual test matrix**

Test these cases in the logged-in OpenWork browser:

```text
new schedule with different date and time
new schedule for today with explicit date and time
reschedule existing post with same time and different date
wrong summary detected before Avançar
scheduled post missing from the scheduled list
```

- [ ] **Step 2: Verify the date/time repeat-selection rule**

For the rescheduling case, select the new date, select the time again, verify the summary, advance, verify the preview, schedule, and confirm the item in the list.

- [ ] **Step 3: Verify failure behavior**

If summary and requested date/time differ, do not advance. If confirmation or list verification fails, do not write the timestamp comment and report the exact failed check.

- [ ] **Step 4: Record only non-sensitive evidence**

Record route used, fallback route, requested timestamp, displayed timestamp and pass/fail. Do not record cookies, account identifiers or private page contents.

- [ ] **Step 5: Run tests**

Run: `python3 -m pytest tests -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add docs/roadmap.md tests
git commit -m "test: verify LinkedIn scheduling and rescheduling flow"
```

## Plan self-review

- Playwright-first routing and visual fallback: Tasks 1 and 3.
- Native vision before image analyzer: Task 1.
- Repeat date and time selection on reschedule: Tasks 1 and 3.
- Existing-post `Alterar agenda` path: Task 1.
- Visual confirmation before advancing and scheduling: Tasks 1 and 3.
- Scheduled-list verification before local registration: Tasks 1 and 2.
- No duplicate publication correction: Task 1.
- No placeholders remain; every task has files, tests, commands and expected results.
