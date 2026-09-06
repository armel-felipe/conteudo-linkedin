# P1-C — Scoring e clustering automatizados: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar dois scripts determinísticos que recalculam scores e agrupam signals em artefatos persistentes sem escrever briefs ou posts.

**Architecture:** `score_opportunities.py` será responsável somente por validar pesos/critérios e calcular scores de topics. `cluster_signals.py` será responsável somente por agrupar signals por pilar e termos de debate. Ambos terão funções puras testáveis, CLI com caminhos explícitos e escrita atômica para não corromper artefatos existentes.

**Tech Stack:** Python 3.12+, standard library, PyYAML já usado pelo projeto, pytest.

## Global Constraints

- Pesos são lidos de `config/scoring.yaml`; não ficam duplicados no código.
- Cada critério é validado no intervalo 0–10.
- A soma dos pesos deve ser 1.0.
- Score final é `sum(critério × peso) × 10`, arredondado de forma determinística.
- Clusters preservam ids, pilares, títulos e evidências sem inventar fatos ou fontes.
- Nenhum script produz brief, draft ou post.
- Entradas vazias produzem saída vazia válida.
- Entradas duplicadas ou inválidas produzem erro explícito e não sobrescrevem artefatos existentes.
- Artefatos reais só são escritos depois de todos os testes passarem.

---

### Task 1: Implementar funções de scoring e CLI

**Files:**
- Create: `score_opportunities.py`
- Test: `tests/test_score_opportunities.py`

**Interfaces:**
- `load_scoring_config(path: Path) -> dict[str, Any]`
- `score_topic(topic: dict[str, Any], weights: dict[str, float]) -> dict[str, Any]`
- `score_topics(topics: list[dict[str, Any]], weights: dict[str, float]) -> list[dict[str, Any]]`
- CLI: `python3 score_opportunities.py --input research/topics/topics_2026-09-01.yaml --config config/scoring.yaml --output research/topics/topics_scored_2026-09-06.yaml`

- [ ] **Step 1: Write failing tests**

```python
import pytest
from score_opportunities import load_scoring_config, score_topic, score_topics


def test_scores_topic_from_configured_weights():
    topic = {"id": "topic_a", "scores": {"freshness": 8, "relevance": 10}}
    weights = {"freshness": 0.5, "relevance": 0.5}
    result = score_topic(topic, weights)
    assert result["scores"]["total"] == 90.0


def test_rejects_missing_or_out_of_range_criteria():
    with pytest.raises(ValueError, match="criteria"):
        score_topic({"id": "topic_a", "scores": {"freshness": 11}}, {"freshness": 1.0})


def test_rejects_weights_that_do_not_sum_to_one(tmp_path):
    config = tmp_path / "scoring.yaml"
    config.write_text("weights:\n  freshness: 0.5\n", encoding="utf-8")
    with pytest.raises(ValueError, match="weights"):
        load_scoring_config(config)


def test_empty_topics_produce_empty_output():
    assert score_topics([], {"freshness": 1.0}) == []
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python3 -m pytest tests/test_score_opportunities.py -q`

Expected: FAIL because `score_opportunities.py` does not exist.

- [ ] **Step 3: Implement validation and scoring**

Load YAML with UTF-8, require a `weights` mapping, reject negative weights and sums outside `1.0 ± 1e-9`, require every configured criterion on every topic, reject non-numeric values or values outside 0–10, preserve all original topic fields, and write `scores.total = round(sum(score * weight) * 10, 2)`. Exclude any pre-existing `scores.total` from the weighted calculation.

- [ ] **Step 4: Implement safe CLI output**

Require `--input`, `--config` and `--output`. Validate the complete input before writing. Reject duplicate topic ids. Write to `<output>.tmp` in the same directory, replace the destination only after serialization succeeds, and never write a brief/draft/post.

- [ ] **Step 5: Run focused tests**

Run: `python3 -m pytest tests/test_score_opportunities.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add score_opportunities.py tests/test_score_opportunities.py
git commit -m "feat: add deterministic opportunity scoring"
```

---

### Task 2: Implementar clustering determinístico e CLI

**Files:**
- Create: `cluster_signals.py`
- Test: `tests/test_cluster_signals.py`

**Interfaces:**
- `load_signals(path: Path) -> list[dict[str, Any]]`
- `cluster_signals(signals: list[dict[str, Any]]) -> list[dict[str, Any]]`
- CLI: `python3 cluster_signals.py --input research/signals/signals_2026-09-01.yaml --output research/topics/clusters_2026-09-06.yaml`

- [ ] **Step 1: Write failing tests**

```python
import pytest
from cluster_signals import cluster_signals


def signal(signal_id, title, pillar, side_a, side_b):
    return {
        "id": signal_id,
        "title": title,
        "pillars": [pillar],
        "debate": {"side_a": side_a, "side_b": side_b},
        "evidence": ["source evidence"],
    }


def test_groups_signals_by_pillar_and_preserves_fields():
    clusters = cluster_signals([
        signal("s1", "ERP e workflow", "ia_aplicada", "integrar", "substituir"),
        signal("s2", "Agentes e workflow", "ia_aplicada", "integrar", "substituir"),
    ])
    assert len(clusters) == 1
    assert clusters[0]["signal_ids"] == ["s1", "s2"]
    assert clusters[0]["pillars"] == ["ia_aplicada"]
    assert clusters[0]["signals"][0]["evidence"] == ["source evidence"]


def test_empty_input_is_valid_and_duplicate_ids_fail():
    assert cluster_signals([]) == []
    item = signal("s1", "title", "pillar", "a", "b")
    with pytest.raises(ValueError, match="duplicate"):
        cluster_signals([item, item])


def test_missing_required_signal_fields_fail():
    with pytest.raises(ValueError, match="required"):
        cluster_signals([{"id": "s1", "title": "missing fields"}])
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python3 -m pytest tests/test_cluster_signals.py -q`

Expected: FAIL because `cluster_signals.py` does not exist.

- [ ] **Step 3: Implement deterministic grouping**

Require unique `id`, non-empty `title`, list `pillars`, `debate.side_a`, `debate.side_b` and list `evidence`. Group by normalized pillar and shared normalized debate terms (lowercase, accents removed, stopwords removed); use stable sorted ids and stable cluster ids derived from the first signal id. Preserve original signal dictionaries inside each cluster and do not create claims, sources or prose beyond deterministic metadata.

- [ ] **Step 4: Implement safe CLI output**

Require explicit `--input` and `--output`, validate all signals before writing, use the same atomic temporary-file replacement as scoring, and produce a YAML object with `clusters`. Empty input produces `clusters: []`.

- [ ] **Step 5: Run focused tests**

Run: `python3 -m pytest tests/test_cluster_signals.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add cluster_signals.py tests/test_cluster_signals.py
git commit -m "feat: add deterministic signal clustering"
```

---

### Task 3: Gerar artefatos reais e fechar P1-C

**Files:**
- Create: `research/topics/topics_scored_2026-09-06.yaml`
- Create: `research/topics/clusters_2026-09-06.yaml`
- Modify: `docs/roadmap.md`
- Test: `tests/test_score_opportunities.py`
- Test: `tests/test_cluster_signals.py`

**Interfaces:**
- Consumes: CLIs das Tasks 1 e 2.
- Produces: dois artefatos YAML persistentes, sem briefs/drafts/posts.

- [ ] **Step 1: Run the complete focused suite before real generation**

Run: `python3 -m pytest tests/test_score_opportunities.py tests/test_cluster_signals.py -q`

Expected: all focused tests pass.

- [ ] **Step 2: Generate the scoring artifact**

Run:

```bash
python3 score_opportunities.py --input research/topics/topics_2026-09-01.yaml --config config/scoring.yaml --output research/topics/topics_scored_2026-09-06.yaml
```

Expected: one YAML artifact with all topics and recalculated totals.

- [ ] **Step 3: Generate the clustering artifact**

Run:

```bash
python3 cluster_signals.py --input research/signals/signals_2026-09-01.yaml --output research/topics/clusters_2026-09-06.yaml
```

Expected: one YAML artifact with deterministic clusters and preserved signal ids/evidence.

- [ ] **Step 4: Validate reproducibility and scope**

Run both CLIs again into temporary outputs and compare their parsed YAML values with the committed artifacts. Confirm no file was created under `research/briefs/`, `content/drafts/` or `content/approved/` by either script.

- [ ] **Step 5: Update the roadmap**

Change only the P1-C line to `[x]`, linking the two generated artifacts and recording the test command/result. Do not mark P1-D complete.

- [ ] **Step 6: Run full verification**

Run: `python3 -m pytest tests -q && python3 -m compileall -q *.py && git diff --check`

Expected: all tests pass, compileall succeeds and diff check produces no output.

- [ ] **Step 7: Inspect and commit**

Confirm no credentials, raw browser logs, briefs or posts are staged, then run:

```bash
git add score_opportunities.py cluster_signals.py tests/test_score_opportunities.py tests/test_cluster_signals.py research/topics/topics_scored_2026-09-06.yaml research/topics/clusters_2026-09-06.yaml docs/roadmap.md
git commit -m "feat: complete P1 scoring and clustering"
```

## Plan self-review

- Config-driven weighted scoring: Task 1.
- Deterministic clustering with preserved evidence: Task 2.
- Empty/duplicate/invalid input coverage: Tasks 1–2.
- Persistent real artifacts only after tests: Task 3.
- Separation from briefs/drafts/posts: all tasks.
- Roadmap update and full verification: Task 3.
