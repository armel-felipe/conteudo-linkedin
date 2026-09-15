from pathlib import Path
import subprocess
import sys

import pytest
import yaml

from linkedin_scheduling import (
    complete_receipt,
    move_after_confirmation,
    prepare_run,
    validate_scheduling_request,
)


def make_post(tmp_path: Path, approved: bool = True, scheduled: bool = False) -> Path:
    text = [
        "## Título",
        "**Negrito** #tag",
        "",
        "## Fontes",
        "- Fonte — https://example.com — 2026-09-15",
    ]
    if approved:
        text.insert(0, "<!-- approved -->")
    if scheduled:
        text.insert(0, "<!-- agendado: 2026-09-20T10:00 America/Sao_Paulo -->")
    drafts = tmp_path / "content" / "drafts"
    drafts.mkdir(parents=True, exist_ok=True)
    path = drafts / "topic_20260915_01.md"
    path.write_text("\n".join(text) + "\n", encoding="utf-8")
    return path


def test_validate_rejects_post_outside_drafts(tmp_path):
    post = make_post(tmp_path)
    post.unlink()
    post = tmp_path / "content" / "published" / "post.md"
    post.parent.mkdir()
    post.write_text("Texto\n\n## Fontes\n- Fonte\n")
    with pytest.raises(ValueError, match="content/drafts"):
        validate_scheduling_request(post, "2026-09-20T10:00 America/Sao_Paulo", approved=True)


def test_validate_rejects_post_without_approval(tmp_path):
    post = make_post(tmp_path, approved=False)
    with pytest.raises(ValueError, match="approved"):
        validate_scheduling_request(post, "2026-09-20T10:00 America/Sao_Paulo", approved=False)


def test_validate_rejects_post_without_sources(tmp_path):
    post = make_post(tmp_path)
    post.write_text("Texto\n")
    with pytest.raises(ValueError, match="Fontes"):
        validate_scheduling_request(post, "2026-09-20T10:00 America/Sao_Paulo", approved=True)


def test_validate_rejects_invalid_timestamp(tmp_path):
    post = make_post(tmp_path)
    with pytest.raises(ValueError, match="timestamp"):
        validate_scheduling_request(post, "not-a-date", approved=True)


def test_validate_rejects_already_scheduled_marker(tmp_path):
    post = make_post(tmp_path, scheduled=True)
    with pytest.raises(ValueError, match="agendado"):
        validate_scheduling_request(post, "2026-09-20T10:00 America/Sao_Paulo", approved=True)


def test_validate_converts_markdown_without_cru_markup(tmp_path):
    post = make_post(tmp_path)
    request = validate_scheduling_request(
        post,
        "2026-09-20T10:00 America/Sao_Paulo",
        approved=True,
        now="2026-09-15T18:00:00-03:00",
    )
    assert request["linkedin_text"].startswith("Título\nNegrito #tag\n\n")
    assert request["checks"]["approved_file"] is True
    assert request["checks"]["markdown_converted"] is True


def test_prepare_run_persists_all_gates_as_not_run(tmp_path):
    post = make_post(tmp_path)
    request = validate_scheduling_request(
        post,
        "2026-09-20T10:00 America/Sao_Paulo",
        approved=True,
        now="2026-09-15T18:00:00-03:00",
    )
    receipt_path = prepare_run(request, run_id="run-1", runs_dir=tmp_path / "runs")
    receipt = yaml.safe_load(receipt_path.read_text())
    assert receipt["topic_id"] == "topic_20260915_01"
    assert receipt["requested_timestamp"] == "2026-09-20T10:00 America/Sao_Paulo"
    assert receipt["route"] == "browser_native"
    assert receipt["browser_attempted"] is False
    for field in ("date_selected", "time_selected", "summary", "preview"):
        assert receipt[field] == "not_run"


def test_complete_receipt_fails_without_scheduled_list(tmp_path):
    post = make_post(tmp_path)
    request = validate_scheduling_request(
        post,
        "2026-09-20T10:00 America/Sao_Paulo",
        approved=True,
        now="2026-09-15T18:00:00-03:00",
    )
    receipt_path = prepare_run(request, run_id="run-1", runs_dir=tmp_path / "runs")
    with pytest.raises(ValueError, match="scheduled_list"):
        complete_receipt(
            receipt_path,
            displayed_timestamp="2026-09-20T10:00 America/Sao_Paulo",
            browser_state={"scheduled_list": "not confirmed"},
            events=schedule_events(),
        )


def test_move_after_confirmation_moves_to_published(tmp_path):
    post = make_post(tmp_path)
    (post.parent.parent / "published").mkdir(exist_ok=True)
    request = validate_scheduling_request(
        post,
        "2026-09-20T10:00 America/Sao_Paulo",
        approved=True,
        now="2026-09-15T18:00:00-03:00",
    )
    receipt_path = prepare_run(request, run_id="run-1", runs_dir=tmp_path / "runs")
    complete_receipt(
        receipt_path,
        displayed_timestamp="2026-09-20T10:00 America/Sao_Paulo",
        browser_state={
            "scheduled_list": "confirmed",
            "screenshot_evidence": "visual",
            "post_identity_evidence": "topic_20260915_01",
            "scheduled_list_evidence": "list confirmed",
        },
        events=schedule_events(),
    )
    moved = move_after_confirmation(
        post,
        receipt_path,
        destination=tmp_path / "content" / "published",
    )
    assert moved == tmp_path / "content" / "published" / "topic_20260915_01.md"
    assert moved.is_file()
    assert not post.exists()
    assert "<!-- agendado: 2026-09-20T10:00 America/Sao_Paulo -->" in moved.read_text(encoding="utf-8")


def test_cli_exposes_validate_and_prepare_commands(tmp_path):
    post = make_post(tmp_path)
    env = {"PYTHONPATH": str(Path(__file__).parents[1])}
    validate = subprocess.run(
        [sys.executable, "linkedin_scheduling.py", "validate", str(post),
         "2026-09-20T10:00 America/Sao_Paulo", "--approved", "--now",
         "2026-09-15T18:00:00-03:00"],
        capture_output=True, text=True, env=env, check=False,
    )
    assert validate.returncode == 0
    assert "topic_20260915_01" in validate.stdout

    prepare = subprocess.run(
        [sys.executable, "linkedin_scheduling.py", "prepare", str(post),
         "2026-09-20T10:00 America/Sao_Paulo", "--approved", "--now",
         "2026-09-15T18:00:00-03:00", "--run-id", "run-cli",
         "--runs-dir", str(tmp_path / "runs")],
        capture_output=True, text=True, env=env, check=False,
    )
    assert prepare.returncode == 0
    assert (tmp_path / "runs" / "run-cli" / "receipt.yaml").is_file()


def schedule_events():
    return [
        "approved_file",
        "markdown_converted",
        "browser_attempt",
        "screenshot",
        "visual_route",
        "date_selected",
        "time_selected",
        "summary_confirmed",
        "advance",
        "final_preview_confirmed",
        "schedule",
        "confirmation",
        "scheduled_list_confirmed",
        "timestamp_registered",
    ]
