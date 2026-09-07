import hashlib
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_yaml(relative_path: str):
    return yaml.safe_load((ROOT / relative_path).read_text(encoding="utf-8"))


def test_scoring_inventory_has_formula_weights_and_fingerprint():
    inventory = load_yaml("research/audits/scoring-inventory-2026-09-06.yaml")
    assert inventory["date"] == "2026-09-06"
    assert inventory["formula_path"] == "score_opportunities.py"
    assert inventory["formula_reference"] == "score_opportunities.py:39-55 (score_topic)"
    assert inventory["weights_source"] == "config/scoring.yaml"
    assert inventory["inputs"] == [
        "config/scoring.yaml",
        "score_opportunities.py",
        "research/topics/topics_scored_2026-09-06.yaml",
        "research/signals/signals_2026-09-01.yaml",
    ]
    assert inventory["weights"] == {
        "freshness": 0.15,
        "relevance": 0.20,
        "debate": 0.15,
        "evidence": 0.10,
        "author_fit": 0.20,
        "originality": 0.10,
        "linkedin_fit": 0.10,
    }
    assert inventory["sample_paths"] == inventory["inputs"][2:]
    assert all((ROOT / path).is_file() for path in inventory["sample_paths"])

    digest = hashlib.sha256()
    for path in inventory["sample_paths"]:
        digest.update((ROOT / path).read_bytes())
    assert inventory["sample_fingerprint"] == f"sha256:{digest.hexdigest()}"
    assert inventory["reproduction"]
    assert inventory["conclusion"]


def test_source_audit_classifies_every_sampled_signal():
    signals = load_yaml("research/signals/signals_2026-09-01.yaml")["signals"]
    signal_by_id = {signal["id"]: signal for signal in signals}
    topics = load_yaml("research/topics/topics_2026-09-01.yaml")["topics"]
    topic = next(item for item in topics if item["id"] == "topic_20260901_04")
    audit = load_yaml("research/audits/source-quality-2026-09-06.yaml")

    assert audit["status"] in {"complete", "inconclusive"}
    assert audit["sources"]
    topic_source_ids = {
        "signal_20260901_002",
        "signal_20260901_006",
        "signal_20260901_016",
        "signal_20260901_017",
    }
    representative_source_ids = {
        "signal_20260901_001",
        "signal_20260901_003",
        "signal_20260901_009",
        "signal_20260901_013",
        "signal_20260901_020",
    }
    assert set(topic["signals"]) == topic_source_ids
    assert set(audit["scope"]["topic_sources"]) == topic_source_ids
    assert set(audit["scope"]["representative_sample"]) == representative_source_ids

    source_ids = [item["source_id"] for item in audit["sources"]]
    assert len(source_ids) == len(set(source_ids))
    assert set(source_ids) == topic_source_ids | representative_source_ids

    required = {
        "source_id",
        "type",
        "independence",
        "recency",
        "verifiability",
        "quality",
        "limitations",
        "inference_risk",
    }
    assert all(required <= set(item) for item in audit["sources"])

    for item in audit["sources"]:
        signal = signal_by_id[item["source_id"]]
        assert item["verification"] == {
            "title": signal["title"],
            "url": signal["source"]["url"],
            "date": signal["source"]["published_at"],
        }

    for source_id in {"signal_20260901_006", "signal_20260901_017"}:
        item = next(item for item in audit["sources"] if item["source_id"] == source_id)
        assert item["topic_connection"] == "indirect_limited"
        assert "conexao com manufatura e indireta e limitada" in item["justification"]


def test_scoring_comparison_is_frozen_and_labels_uncertainty():
    comparison = load_yaml("research/audits/scoring-comparison-2026-09-06.yaml")
    allowed_statuses = {
        "discovered",
        "clustered",
        "candidate",
        "ready_for_research",
        "researched",
        "drafted",
        "approved",
        "published",
        "archived",
        "blocked",
    }
    allowed_classifications = {"false_positive", "false_negative", "inconclusive"}

    assert comparison["status"] in {"complete", "inconclusive"}
    assert comparison["sample_paths"]
    assert all((ROOT / path).is_file() for path in comparison["sample_paths"])

    digest = hashlib.sha256()
    for path in comparison["sample_paths"]:
        digest.update((ROOT / path).read_bytes())
    assert comparison["sample_fingerprint"] == f"sha256:{digest.hexdigest()}"

    assert comparison["topics"]
    required_fields = {
        "id",
        "score_predicted",
        "editorial_decision",
        "score_status",
        "backlog_status",
        "quality_observed",
        "classification",
        "reason",
        "evidence_refs",
    }
    for item in comparison["topics"]:
        assert required_fields <= set(item)
        assert set(item) <= required_fields
        assert item["score_status"] in allowed_statuses
        assert item["backlog_status"] in allowed_statuses
        assert item["classification"] in allowed_classifications
        assert item["reason"].strip()
        assert item["evidence_refs"]
        assert all(isinstance(ref, str) and ref.strip() for ref in item["evidence_refs"])
        assert item["editorial_decision"] in allowed_statuses | {"inconclusive"}
        assert item["editorial_decision"] == (
            item["score_status"]
            if item["score_status"] == item["backlog_status"]
            else "inconclusive"
        )
        for ref in item["evidence_refs"]:
            if "://" not in ref:
                referenced_path = ref.split(":", 1)[0]
                assert (ROOT / referenced_path).is_file()
        if item["classification"] == "inconclusive":
            has_brief_or_audit = any(
                ref.split(":", 1)[0].startswith(("research/briefs/", "research/audits/"))
                for ref in item["evidence_refs"]
            )
            assert (
                item["score_status"] != item["backlog_status"]
                or item["quality_observed"] == "not_observed"
                or not has_brief_or_audit
            )
        assert "engagement" not in item

    topic_ids = {item["id"] for item in comparison["topics"]}
    for classification in allowed_classifications:
        summary_ids = set(comparison["summary"][f"{classification}_topics"])
        assert summary_ids == {
            item["id"]
            for item in comparison["topics"]
            if item["classification"] == classification
        }
        assert summary_ids <= topic_ids


def test_scoring_decision_records_evidence_and_non_changes():
    text = Path("research/audits/scoring-decision-2026-09-06.md").read_text()
    assert "## Decisão" in text
    assert "## Evidências" in text
    assert "## O que não mudou" in text
    assert "aprovação humana" in text.lower()
