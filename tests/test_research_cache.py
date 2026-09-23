from research_cache import build_research_cache_key, cache_is_reusable


def test_cache_key_is_stable_and_changes_with_inputs():
    args = ("topic_1", "2026-09-01", "2026-09-22", "3.14", "sources-hash")
    assert build_research_cache_key(*args) == build_research_cache_key(*args)
    assert build_research_cache_key(*args) != build_research_cache_key(*args[:-1], "other-sources")


def test_degraded_cache_is_not_reusable_by_default():
    metadata = {
        "cache_key": "sha256:x", "artifact_path": "research/briefs/topic_1.md",
        "created_at": "2026-09-22T00:00:00Z", "status": "complete", "degraded": True,
    }
    assert cache_is_reusable(metadata) is False
    assert cache_is_reusable(metadata, degraded=True) is True


def test_incomplete_cache_is_not_reusable():
    assert cache_is_reusable({"cache_key": "sha256:x"}) is False
