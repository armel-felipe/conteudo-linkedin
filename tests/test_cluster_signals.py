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
