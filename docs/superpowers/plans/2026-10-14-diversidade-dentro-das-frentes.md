# Diversidade Dentro das Frentes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar diversidade semântica ao Bloco 1 para variar os assuntos dentro de cada frente, penalizando repetição e misturando queries exploratórias às keywords atuais.

**Architecture:** Um módulo puro `diversity.py` fará normalização, validação, distância e diagnóstico de concentração. `score_opportunities.py` usará esse diagnóstico de forma opcional e determinística, preservando o scoring legado quando a dimensão não estiver disponível. `config/frentes.yaml` fornecerá perguntas exploratórias; `generate_topics_html.py` exibirá a distribuição da leva.

**Tech Stack:** Python 3, PyYAML, pytest, YAML de configuração e HTML gerado por Python.

## Global Constraints

- O gate de novidade (`new`, `revisited`, `duplicate`) permanece obrigatório e independente.
- Signals antigos sem `diversity` continuam legíveis e recebem `unknown` para fins de diversidade.
- Se o histórico não estiver disponível, o bônus de diversidade falha fechado; não se inventa distância.
- A diversidade não pode substituir rastreabilidade, evidência, `author_fit` ou relevância.
- Nenhum bloco posterior ao Bloco 1 será chamado automaticamente.
- Não publicar, agendar, mover ou alterar o draft aprovado durante esta implementação.

---

### Task 1: Criar o núcleo de diversidade semântica

**Files:**
- Create: `diversity.py`
- Test: `tests/test_diversity.py`

**Interfaces:**
- `DIMENSIONS = ("context", "mechanism", "actor", "change_type")`
- `normalize_diversity(value: object) -> dict[str, list[str]]`
- `classify_topic(topic: dict[str, object]) -> dict[str, list[str]]`
- `topic_distance(candidate: dict[str, object], recent: list[dict[str, object]]) -> dict[str, object]`
- `concentration_report(topics: list[dict[str, object]]) -> dict[str, object]`

- [ ] **Step 1: Write the failing tests**

```python
def test_normalize_diversity_fills_unknown_dimensions():
    assert normalize_diversity({"mechanism": ["custo"]}) == {
        "context": ["unknown"],
        "mechanism": ["custo"],
        "actor": ["unknown"],
        "change_type": ["unknown"],
    }

def test_distance_penalizes_same_mechanism_and_context():
    candidate = {"id": "new", "diversity": {
        "context": ["varejo"], "mechanism": ["custo"],
        "actor": ["gestor"], "change_type": ["adocao"],
    }}
    recent = [{"id": "old", "diversity": {
        "context": ["varejo"], "mechanism": ["custo"],
        "actor": ["cliente"], "change_type": ["falha"],
    }}]
    result = topic_distance(candidate, recent)
    assert result["distance_from_recent_topics"] < 5
    assert result["closest_topics"] == ["old"]

def test_distance_rewards_two_changed_dimensions():
    candidate = {"id": "new", "diversity": {
        "context": ["educacao"], "mechanism": ["autoridade"],
        "actor": ["regulador"], "change_type": ["conflito"],
    }}
    recent = [{"id": "old", "diversity": {
        "context": ["varejo"], "mechanism": ["custo"],
        "actor": ["gestor"], "change_type": ["adocao"],
    }}]
    assert topic_distance(candidate, recent)["distance_from_recent_topics"] >= 8

def test_concentration_report_counts_mechanisms_and_unknowns():
    report = concentration_report([
        {"diversity": {"mechanism": ["custo"]}},
        {"diversity": {"mechanism": ["custo"]}},
        {"diversity": {"mechanism": ["confianca"]}},
    ])
    assert report["by_mechanism"] == {"confianca": 1, "custo": 2}
    assert report["unknown_count"] == 0
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `pytest tests/test_diversity.py -q`

Expected: FAIL because `diversity.py` does not exist.

- [ ] **Step 3: Implement the minimal deterministic module**

Implement `DIMENSIONS`, normalize each dimension to sorted unique strings, return `unknown` for absent/invalid dimensions, compare the closest historical topic by overlap across the four dimensions, and map overlap to a 0-10 distance score. Include `closest_topics`, `overlap`, and a human-readable `explanation` in the result. Count each declared value once in `concentration_report`; expose `unknown_count` and `total_topics`.

- [ ] **Step 4: Run the focused tests**

Run: `pytest tests/test_diversity.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the isolated module**

```bash
git add diversity.py tests/test_diversity.py
git commit -m "feat: add semantic diversity diagnostics"
```

### Task 2: Integrar distância ao scoring sem quebrar o legado

**Files:**
- Modify: `config/scoring.yaml`
- Modify: `score_opportunities.py`
- Modify: `research/audits/scoring-parallel-2026-09-06.yaml`
- Test: `tests/test_score_opportunities.py`

**Interfaces:**
- `score_topics(topics, weights, recent_topics=None) -> list[dict]`
- CLI extension: repeatable `--recent-topics PATH` loads one or more YAML files with a `topics` list.
- New output fields: `topic["diversity_score"]` and `topic["scores"]["distance_from_recent_topics"]` when `recent_topics` is supplied.

- [ ] **Step 1: Write failing tests**

```python
def test_scoring_adds_distance_when_history_is_supplied():
    topic = {"id": "new", "diversity": {
        "context": ["educacao"], "mechanism": ["autoridade"],
        "actor": ["regulador"], "change_type": ["conflito"],
    }, "scores": {
        "freshness": 8, "relevance": 8, "debate": 8, "evidence": 8,
        "author_fit": 8, "originality": 8, "linkedin_fit": 8,
        "distance_from_recent_topics": 0,
    }}
    result = score_topics([topic], load_scoring_config(ROOT / "config/scoring.yaml"),
                          recent_topics=[{"id": "old", "diversity": {
                              "context": ["varejo"], "mechanism": ["custo"],
                              "actor": ["gestor"], "change_type": ["adocao"],
                          }}])
    assert result[0]["scores"]["distance_from_recent_topics"] >= 8
    assert result[0]["diversity_score"]["closest_topics"] == ["old"]

def test_legacy_scoring_without_history_keeps_existing_criteria():
    topic = {"id": "legacy", "scores": {
        "freshness": 8, "relevance": 8, "debate": 8, "evidence": 8,
        "author_fit": 8, "originality": 8, "linkedin_fit": 8,
    }}
    result = score_topics([topic], load_scoring_config(ROOT / "config/scoring.yaml"))
    assert "distance_from_recent_topics" not in result[0]["scores"]
```

- [ ] **Step 2: Run the focused tests and verify the first test fails**

Run: `pytest tests/test_score_opportunities.py -q`

Expected: the new distance integration test fails; existing scoring tests remain green.

- [ ] **Step 3: Update the scoring configuration and implementation**

Add `distance_from_recent_topics: 0.15` to `config/scoring.yaml` and use these exact weights so the total remains 1.0: `freshness: 0.15`, `relevance: 0.15`, `debate: 0.15`, `evidence: 0.10`, `author_fit: 0.15`, `originality: 0.10`, `linkedin_fit: 0.05`, `distance_from_recent_topics: 0.15`. Update `score_topics` to accept optional `recent_topics`; when supplied, compute distance before validating/scoring and inject the criterion. When omitted, preserve the current criteria exactly for backward compatibility.

- [ ] **Step 4: Run scoring tests and config validation**

Run: `pytest tests/test_score_opportunities.py -q`

Expected: PASS, including weight-sum validation and the historical scoring audit tests after updating `current_weights`, `current_ranking`, and `config_sha256` in `research/audits/scoring-parallel-2026-09-06.yaml` to the deterministic values produced by the new configuration.

- [ ] **Step 5: Commit the scoring change**

```bash
git add config/scoring.yaml score_opportunities.py tests/test_score_opportunities.py
git commit -m "feat: score distance from recent topics"
```

### Task 3: Adicionar perguntas exploratórias por frente

**Files:**
- Modify: `config/frentes.yaml`
- Test: `tests/test_diversity.py`

**Interfaces:**
- Every front gets `exploratory_questions: list[str]`.
- `load_exploratory_questions(path: Path) -> dict[str, list[str]]` is added to `diversity.py`.

- [ ] **Step 1: Write the failing configuration test**

```python
def test_each_front_has_exploratory_questions():
    questions = load_exploratory_questions(ROOT / "config/frentes.yaml")
    assert questions
    assert all(len(items) >= 4 for items in questions.values())
    assert all(all(item.endswith("?") for item in items) for items in questions.values())
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `pytest tests/test_diversity.py::test_each_front_has_exploratory_questions -q`

Expected: FAIL because the configuration has no `exploratory_questions` field.

- [ ] **Step 3: Add four or more non-evergreen questions to every front**

Questions must cover change, conflict, consequence, behavior, power, or counterintuitive practice. Keep existing keywords unchanged and add only the new field.

- [ ] **Step 4: Implement and test the loader**

`load_exploratory_questions` must reject malformed front entries, require a non-empty list of strings, and return a mapping keyed by front id.

Run: `pytest tests/test_diversity.py::test_each_front_has_exploratory_questions -q`

Expected: PASS.

- [ ] **Step 5: Commit configuration and loader**

```bash
git add config/frentes.yaml diversity.py tests/test_diversity.py
git commit -m "feat: add exploratory questions by front"
```

### Task 4: Exibir concentração no HTML de topics

**Files:**
- Modify: `scripts/generate_topics_html.py`
- Test: `tests/test_topics_html_contract.py`

**Interfaces:**
- `render_diversity_summary(topics: list[dict]) -> str`
- The generated HTML contains a visible section with `by_mechanism`, `by_context`, `by_actor`, `distance_average`, and concentration alerts.

- [ ] **Step 1: Write the failing HTML contract test**

```python
import subprocess

def test_html_includes_diversity_summary(tmp_path):
    source = tmp_path / "topics.yaml"
    source.write_text("topics:\n- id: t1\n  title: T\n  status: candidate\n  pillars: [ia_aplicada]\n  scores: {total: 80}\n  diversity:\n    context: [varejo]\n    mechanism: [custo]\n    actor: [gestor]\n    change_type: [falha]\n", encoding="utf-8")
    subprocess.run([
        "python", "scripts/generate_topics_html.py", str(source),
    ], cwd=ROOT, check=True)
    output = source.with_suffix(".html")
    html = output.read_text(encoding="utf-8")
    assert "Diversidade da leva" in html
    assert "custo" in html
    assert "contexto" in html.lower()
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `pytest tests/test_topics_html_contract.py -q`

Expected: FAIL because the generated HTML has no diversity section.

- [ ] **Step 3: Implement the summary renderer and insert it into the page**

Use `concentration_report` and the stored `diversity_score` values. Render counts and a warning when a mechanism exceeds 50% of the topics or fewer than three mechanisms exist while at least three topics are present. Escape all values through the existing HTML escaping helper.

- [ ] **Step 4: Run HTML tests and regenerate the current artifact**

Run: `pytest tests/test_topics_html_contract.py -q` and `python scripts/generate_topics_html.py research/topics/topics_2026-10-13.yaml`

Expected: PASS and the current HTML remains valid with the new summary, including the all-archived current batch.

- [ ] **Step 5: Commit the HTML change**

```bash
git add scripts/generate_topics_html.py tests/test_topics_html_contract.py research/topics/topics_2026-10-13.html
git commit -m "feat: show topic diversity summary"
```

### Task 5: End-to-end validation and documentation consistency

**Files:**
- Modify: `.agents/skills/discover-signals/SKILL.md`
- Modify: `docs/fluxo-operacao.md`
- Test: existing `tests/test_editorial_gates.py`, `tests/test_topics_html_contract.py`, `tests/test_score_opportunities.py`, `tests/test_cluster_signals.py`.

- [ ] **Step 1: Document the opt-in diversity mode**

Add the exact behavior: the discovery skill reads `exploratory_questions` from `config/frentes.yaml`, runs approximately half keyword queries and half exploratory questions in diversity mode, and persists the dimensions on each signal when supported. State that semantic distance is a scoring signal, not a replacement for novelty, and that the HTML reports concentration.

- [ ] **Step 2: Run the full relevant test set**

Run: `pytest tests/test_diversity.py tests/test_score_opportunities.py tests/test_cluster_signals.py tests/test_topics_html_contract.py tests/test_editorial_gates.py -q`

Expected: PASS.

- [ ] **Step 3: Run repository consistency tests**

Run: `pytest -q`

Expected: PASS, or a documented failure caused by pre-existing unrelated worktree changes; do not overwrite those changes.

- [ ] **Step 4: Verify gates and generated artifacts**

Run: `python scripts/sync_backlog.py --check` and `python scripts/generate_topics_html.py research/topics/topics_2026-10-13.yaml`.

Expected: backlog has no divergence and the HTML file is regenerated successfully.

- [ ] **Step 5: Review the final diff**

Run: `git diff --check` and `git status --short`.

Expected: only the intended implementation files and pre-existing user changes are present; no published or approved content has been changed.

