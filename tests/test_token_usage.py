from token_usage import summarize_token_usage


def test_summarizes_totals_and_dimensions_deterministically():
    result = summarize_token_usage([
        {"run_id": "run-b", "stage": "write", "model": "m2", "input_tokens": 10, "output_tokens": 3},
        {"run_id": "run-a", "stage": "research", "model": "m1", "input_tokens": 20, "output_tokens": 5, "cached_input_tokens": 8},
    ])
    assert result["totals"] == {"calls": 2, "input_tokens": 30, "output_tokens": 8, "cached_input_tokens": 8}
    assert list(result["by_stage"]) == ["research", "write"]
    assert result["by_model"]["m1"]["input_tokens"] == 20


def test_legacy_records_are_counted_without_inventing_usage():
    result = summarize_token_usage([{"run_id": "old", "stage": "browser"}])
    assert result["totals"] == {"calls": 1, "input_tokens": 0, "output_tokens": 0, "cached_input_tokens": 0}
