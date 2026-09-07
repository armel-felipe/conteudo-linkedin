# P2.3 Scoring e Fontes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Auditar fontes e scoring editorial e produzir uma recomendação reproduzível, sem alterar pesos ativos automaticamente.

**Architecture:** A auditoria somente leitura congela uma amostra de signals/topics, classifica fontes em YAML e compara o ranking atual com uma proposta alternativa em um artefato separado. A decisão final permanece humana e é registrada no roadmap; os arquivos originais de signals, topics e configuração ativa não são sobrescritos durante a análise.

**Tech Stack:** Python 3.12, PyYAML, `score_opportunities.py`, YAML persistente, pytest.

## Global Constraints

- Não coletar métricas do LinkedIn nem depender de engajamento.
- Não inventar notas para dados ausentes; usar `inconclusive` quando a amostra não sustentar conclusão.
- Uma fonte comercial ou painel não prova automaticamente adoção, escala ou resultado operacional.
- O scoring atual e o alternativo usam o mesmo conjunto congelado de topics, a mesma escala e os mesmos dados.
- Nenhum peso ativo é substituído sem aprovação humana e registro da decisão.
- Cada artefato deve registrar data, entradas, fingerprint, limitações e conclusão.

---

### Task 1: Inventariar fórmula e amostra congelada

**Files:**
- Read: `config/scoring.yaml`
- Read: `score_opportunities.py`
- Read: `research/topics/topics_scored_2026-09-06.yaml`
- Read: `research/signals/signals_2026-09-01.yaml`
- Create: `research/audits/scoring-inventory-2026-09-06.yaml`
- Test: `tests/test_p2_3_audits.py`

**Interfaces:**
- Consumes: configuração ativa, script de scoring e arquivos YAML existentes.
- Produces: inventário com `formula_path`, `criteria`, `weights`, `sample_paths`, `sample_fingerprint` e `limitations`.

- [ ] **Step 1: Write the failing test**

```python
def test_scoring_inventory_has_formula_weights_and_fingerprint():
    inventory = load_yaml("research/audits/scoring-inventory-2026-09-06.yaml")
    assert inventory["formula_path"] in {"config/scoring.yaml", "score_opportunities.py"}
    assert inventory["weights"]
    assert inventory["sample_paths"]
    assert inventory["sample_fingerprint"].startswith("sha256:")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. pytest -q tests/test_p2_3_audits.py::test_scoring_inventory_has_formula_weights_and_fingerprint`
Expected: FAIL because the inventory artifact does not exist.

- [ ] **Step 3: Write the inventory artifact**

Record the exact formula path and weights found in `config/scoring.yaml` or
`score_opportunities.py`, list the frozen signal/topic files, calculate one
SHA-256 over their ordered bytes, and record any missing criteria or data.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. pytest -q tests/test_p2_3_audits.py::test_scoring_inventory_has_formula_weights_and_fingerprint`
Expected: PASS.

### Task 2: Audit source quality

**Files:**
- Read: `research/signals/signals_2026-09-01.yaml`
- Read: `research/topics/topics_2026-09-01.yaml`
- Create: `research/audits/source-quality-2026-09-06.yaml`
- Modify: `tests/test_p2_3_audits.py`

**Interfaces:**
- Consumes: signals referenced by `topic_20260901_04` and a representative sample from the frozen signal file.
- Produces: one audit record per source with `source_id`, `type`, `independence`, `recency`, `verifiability`, `topic_connection`, `quality`, `justification`, `limitations` and `inference_risk`.

- [ ] **Step 1: Write the failing test**

```python
def test_source_audit_classifies_every_sampled_signal():
    audit = load_yaml("research/audits/source-quality-2026-09-06.yaml")
    assert audit["status"] in {"complete", "inconclusive"}
    assert audit["sources"]
    required = {"source_id", "type", "independence", "recency", "verifiability", "quality", "limitations", "inference_risk"}
    assert all(required <= set(item) for item in audit["sources"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. pytest -q tests/test_p2_3_audits.py::test_source_audit_classifies_every_sampled_signal`
Expected: FAIL because the source audit does not exist.

- [ ] **Step 3: Write the audit artifact**

Classify primary research separately from panels, vendor marketing, secondary
reporting and community discussion. Use the signal URL/title/date as the
verification record. Mark missing methodology, baseline, sample or transcript
as limitations rather than inferring quality.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. pytest -q tests/test_p2_3_audits.py::test_source_audit_classifies_every_sampled_signal`
Expected: PASS.

### Task 3: Compare scores with editorial decisions

**Files:**
- Read: `content/backlog.md`
- Read: `research/topics/topics_*.yaml`
- Read: `research/briefs/topic_20260901_03.md`
- Read: `research/briefs/topic_20260901_04.md`
- Create: `research/audits/scoring-comparison-2026-09-06.yaml`
- Modify: `tests/test_p2_3_audits.py`

**Interfaces:**
- Consumes: frozen topic scores, topic statuses, briefs and source audit.
- Produces: per-topic `score_predicted`, `editorial_decision`, `quality_observed`, `classification`, `reason` and `evidence_refs`; top-level `status` is `complete` or `inconclusive`.

- [ ] **Step 1: Write the failing test**

```python
def test_scoring_comparison_is_frozen_and_labels_uncertainty():
    comparison = load_yaml("research/audits/scoring-comparison-2026-09-06.yaml")
    assert comparison["sample_fingerprint"].startswith("sha256:")
    assert comparison["status"] in {"complete", "inconclusive"}
    assert comparison["topics"]
    assert all("classification" in item and "reason" in item for item in comparison["topics"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. pytest -q tests/test_p2_3_audits.py::test_scoring_comparison_is_frozen_and_labels_uncertainty`
Expected: FAIL because the comparison artifact does not exist.

- [ ] **Step 3: Write the comparison artifact**

Use `selected`, `discarded`, `blocked`, `researched`, `approved` and `published`
as editorial decisions only when persisted in source files. Label a high-score
topic with weak evidence as `false_positive`, a low-score topic with strong
verified evidence as `false_negative`, and unresolved cases as `inconclusive`.
Do not use LinkedIn engagement as a proxy.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. pytest -q tests/test_p2_3_audits.py::test_scoring_comparison_is_frozen_and_labels_uncertainty`
Expected: PASS.

### Task 4: Add parallel scoring comparison

**Files:**
- Modify: `score_opportunities.py`
- Create: `research/audits/scoring-parallel-2026-09-06.yaml`
- Modify: `tests/test_score_opportunities.py`

**Interfaces:**
- Consumes: the frozen topic sample and two explicit weight maps.
- Produces: `run_scoring(topics, weights) -> list[dict]` with stable ordering and a report containing current/alternative rankings and movements.

- [ ] **Step 1: Write the failing test**

```python
def test_parallel_scoring_uses_same_topics_and_reports_movements():
    report = load_yaml("research/audits/scoring-parallel-2026-09-06.yaml")
    assert report["same_sample"] is True
    assert report["current_ranking"]
    assert report["alternative_ranking"]
    assert "movements" in report
    assert report["recommendation"] in {"keep_current", "test_alternative", "reject_alternative", "inconclusive"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. pytest -q tests/test_score_opportunities.py::test_parallel_scoring_uses_same_topics_and_reports_movements`
Expected: FAIL because the parallel report and interface do not exist.

- [ ] **Step 3: Implement the minimal comparison interface**

Extract the existing pure scoring calculation without changing its active
weights. Accept an explicit weight map for the alternative run, preserve the
same topic IDs and input values, and write ranking movements plus criteria that
caused each movement.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. pytest -q tests/test_score_opportunities.py::test_parallel_scoring_uses_same_topics_and_reports_movements`
Expected: PASS.

### Task 5: Record recommendation and roadmap learning

**Files:**
- Create: `research/audits/scoring-decision-2026-09-06.md`
- Modify: `docs/roadmap.md`
- Modify: `tests/test_p2_3_audits.py`

**Interfaces:**
- Consumes: inventory, source audit, comparison and parallel scoring report.
- Produces: a human-readable decision stating `keep_current`, `test_alternative`, `reject_alternative` or `inconclusive`, with evidence and explicit non-changes.

- [ ] **Step 1: Write the failing test**

```python
def test_scoring_decision_records_evidence_and_non_changes():
    text = Path("research/audits/scoring-decision-2026-09-06.md").read_text()
    assert "## Decisão" in text
    assert "## Evidências" in text
    assert "## O que não mudou" in text
    assert "aprovação humana" in text.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. pytest -q tests/test_p2_3_audits.py::test_scoring_decision_records_evidence_and_non_changes`
Expected: FAIL because the decision artifact does not exist.

- [ ] **Step 3: Write the decision and update the roadmap**

State whether the evidence supports changing weights. If the sample is weak,
choose `inconclusive` and keep the active configuration unchanged. Add the
date, artifact paths, evidence references, limitations, recommendation and
what was deliberately maintained to the roadmap.

- [ ] **Step 4: Run the focused test suite**

Run: `PYTHONPATH=. pytest -q tests/test_p2_3_audits.py tests/test_score_opportunities.py`
Expected: all focused tests pass and the active weights remain byte-for-byte unchanged.

## Final Verification

Run: `PYTHONPATH=. pytest -q`

Expected: the full suite passes, all new audit artifacts parse as YAML, no
LinkedIn browser action is invoked, and `git diff --check` reports no errors.
