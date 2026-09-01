from pathlib import Path


DOCS = [Path("README.md"), Path("mapa.md"), Path("AGENTS.md")]
RUNBOOKS = [
    Path("README.md"),
    Path(".agents/skills/run-editorial-batch/SKILL.md"),
    Path(".agents/skills/gauntlet-loop/SKILL.md"),
    Path("docs/roadmap.md"),
]


def test_docs_reference_same_batch_and_gauntlet_names():
    text = "\n".join(path.read_text() for path in DOCS)
    assert "run-editorial-batch" in text
    assert "gauntlet-loop" in text
    assert "escrita-humana" in text


def test_runbooks_document_resumable_events_and_metrics():
    text = "\n".join(path.read_text() for path in RUNBOOKS)
    for term in (
        "checkpoint",
        "retom",
        "events",
        "queue size",
        "completed",
        "blocked",
        "cycles per stage",
        "reviewer coverage",
        "human-writing conformity",
        "time-to-approval",
    ):
        assert term in text


def test_runbooks_preserve_approved_gates_and_separate_scheduling():
    text = "\n".join(path.read_text() for path in RUNBOOKS)
    assert "coverage > 0.99" in text
    assert ">=9/10" in text
    assert "hard_failures" in text
    assert "Never rerun an approved topic automatically" in text
    assert "scheduling" in text.lower()
    assert "publicar-linkedin" in text
