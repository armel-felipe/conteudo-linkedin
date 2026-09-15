"""Validation, receipt, and file-transition primitives for LinkedIn scheduling."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml

from scheduling_contract import validate_dry_run_events, validate_receipt, validate_schedule_events

ROOT = Path(__file__).resolve().parent
APPROVED_MARKER_RE = re.compile(r"<!--\s*approved\s*-->", re.IGNORECASE)
SCHEDULED_MARKER_RE = re.compile(r"<!--\s*agendado:[^>]*-->", re.IGNORECASE)
PUBLISHED_MARKER_RE = re.compile(r"<!--\s*publicado:[^>]*-->", re.IGNORECASE)
TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?:\s+[A-Za-z_/]+)?$")
SCHEDULE_EVENTS = (
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
)


def convert_markdown_to_linkedin(text: str) -> str:
    lines = []
    for raw in text.splitlines():
        line = raw
        if re.match(r"^#{1,6}\s+", line):
            line = re.sub(r"^#{1,6}\s+", "", line)
        line = re.sub(r"<!--\s*(?:approved|agendado:)[^>]*-->", "", line)
        line = re.sub(r"<!--\s*(?:approved|agendado:)[^>]*-->", "", line)
        line = re.sub(r"\*\*(.+?)\*\*", r"\1", line, flags=re.DOTALL)
        line = re.sub(r"__(.+?)__", r"\1", line, flags=re.DOTALL)
        line = re.sub(r"(?<!\w)\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"\1", line)
        line = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", line)
        lines.append(line)
    converted = "\n".join(line for line in lines)
    converted = re.sub(r"<!--\s*(?:approved|agendado:)[^>]*-->", "", converted)
    return "\n".join(part.strip() for part in converted.splitlines()).strip()


def _validate_timestamp(value: str) -> datetime:
    if not isinstance(value, str) or not TS_RE.match(value):
        raise ValueError("invalid timestamp")
    normalized = value.split(" ", 1)[0] + ":00"
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as error:
        raise ValueError("invalid timestamp") from error


def _marker_counts(text: str) -> dict[str, int]:
    return {
        "approved": len(APPROVED_MARKER_RE.findall(text)),
        "agendado": len(SCHEDULED_MARKER_RE.findall(text)),
        "publicado": len(PUBLISHED_MARKER_RE.findall(text)),
    }


def validate_scheduling_request(
    file_path: str | Path,
    requested_timestamp: str,
    *,
    approved: bool,
    now: str | None = None,
) -> dict[str, Any]:
    path = Path(file_path).resolve()
    if path.parent.name != "drafts" or path.parent.parent.name != "content":
        raise ValueError("post must be in content/drafts")
    text = path.read_text(encoding="utf-8")
    if "## Fontes" not in text:
        raise ValueError("post must end with ## Fontes")
    if not approved or not APPROVED_MARKER_RE.search(text):
        raise ValueError("post is not approved")
    if SCHEDULED_MARKER_RE.search(text):
        raise ValueError("post already has an agendado marker")
    observed = _validate_timestamp(requested_timestamp)
    now_dt = datetime.fromisoformat(now) if now else datetime.now().astimezone()
    if observed.date() < now_dt.date():
        raise ValueError("timestamp is in the past")
    linkedin_text = convert_markdown_to_linkedin(text)
    return {
        "file": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
        "topic_id": path.stem,
        "requested_timestamp": requested_timestamp,
        "markdown": text,
        "linkedin_text": linkedin_text,
        "markers": _marker_counts(text),
        "checks": {
            "approved_file": True,
            "markdown_converted": True,
            "scheduled_list_confirmed": False,
            "timestamp_registered": False,
        },
    }


AUDIT_RECEIPT_FIELDS = (
    "evidence_status",
    "route",
    "fallback",
    "requested_timestamp",
    "displayed_timestamp",
    "date_selected",
    "time_selected",
    "summary",
    "preview",
    "confirmation",
    "scheduled_list",
    "timestamp_registered",
    "duplicate_created",
    "route_attempted",
    "browser_attempted",
    "route_reasons",
    "observed_state",
    "verification_evidence",
    "post_action_confirmation",
)


def _initial_receipt(request: dict[str, Any], run_id: str) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "topic_id": request["topic_id"],
        "requested_timestamp": request["requested_timestamp"],
        "displayed_timestamp": "",
        "route": "browser_native",
        "fallback": "none",
        "route_attempted": [],
        "browser_attempted": False,
        "date_selected": "not_run",
        "time_selected": "not_run",
        "summary": "not_run",
        "preview": "not_run",
        "confirmation": "not_run",
        "scheduled_list": "not_run",
        "timestamp_registered": False,
        "duplicate_created": False,
        "failure_state": None,
    }


def prepare_run(
    request: dict[str, Any],
    *,
    run_id: str | None = None,
    runs_dir: str | Path = ROOT / "runs" / "scheduling",
) -> Path:
    selected = run_id or f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{uuid4().hex[:8]}"
    runs_dir = Path(runs_dir)
    runs_dir.mkdir(parents=True, exist_ok=True)
    path = runs_dir / selected / "receipt.yaml"
    if path.exists():
        raise ValueError("receipt already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    receipt = _initial_receipt(request, selected)
    path.write_text(yaml.safe_dump(receipt, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def load_receipt(path: str | Path) -> dict[str, Any]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def complete_receipt(
    receipt_path: str | Path,
    *,
    displayed_timestamp: str,
    browser_state: dict[str, Any],
    events: list[str],
) -> dict[str, Any]:
    path = Path(receipt_path)
    receipt = load_receipt(path)
    requested = receipt["requested_timestamp"]
    if displayed_timestamp != requested:
        raise ValueError("displayed_timestamp diverges")
    if browser_state.get("scheduled_list") != "confirmed":
        raise ValueError("scheduled_list was not confirmed")
    if tuple(events) != SCHEDULE_EVENTS:
        raise ValueError("invalid scheduling event sequence")
    if not browser_state.get("screenshot_evidence"):
        raise ValueError("screenshot_evidence is required")
    if not browser_state.get("post_identity_evidence"):
        raise ValueError("post_identity_evidence is required")
    receipt.update(
        {
            "displayed_timestamp": displayed_timestamp,
            "route_attempted": ["browser_native"],
            "browser_attempted": True,
            "route_reasons": {"browser_native": "visual route confirmed"},
            "evidence_status": "real_existing_post",
            "date_selected": "pass",
            "time_selected": "pass",
            "summary": "pass",
            "preview": "pass",
            "confirmation": "pass",
            "scheduled_list": "pass",
            "timestamp_registered": True,
            "timestamp_registered_state": "pass",
            "duplicate_created": False,
            "post_action_confirmation": "confirmed independently in scheduled list",
            "observed_state": browser_state,
            "verification_evidence": str(browser_state.get("scheduled_list_evidence", "")),
        }
    )
    audit_receipt = {field: receipt[field] for field in AUDIT_RECEIPT_FIELDS}
    audit_receipt = {field: receipt[field] for field in AUDIT_RECEIPT_FIELDS if field != "timestamp_registered"}
    audit_receipt["timestamp_registered"] = "pass"
    validate_receipt(audit_receipt)
    receipt_path.with_name("audit-receipt.yaml").write_text(
        yaml.safe_dump(audit_receipt, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    if not receipt["verification_evidence"].strip():
        raise ValueError("scheduled list evidence is required")
    path.write_text(yaml.safe_dump(receipt, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return receipt


def _git_mv(source: Path, target: Path) -> None:
    try:
        subprocess.run(
            ["git", "mv", str(source), str(target)],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        shutil.move(str(source), str(target))


def move_after_confirmation(
    file_path: str | Path,
    receipt_path: str | Path,
    *,
    destination: str | Path = ROOT / "content" / "published",
) -> Path:
    receipt_path = Path(receipt_path)
    receipt = load_receipt(receipt_path)
    validate_receipt(load_receipt(receipt_path.with_name("audit-receipt.yaml")))
    if receipt.get("evidence_status") != "real_existing_post":
        raise ValueError("receipt is not a confirmed real scheduling")
    source = Path(file_path)
    if source.parent.name != "drafts" or source.parent.parent.name != "content":
        raise ValueError("post must be in content/drafts")
    if source.stem != receipt.get("topic_id"):
        raise ValueError("receipt does not match post")
    text = source.read_text(encoding="utf-8")
    marker = f"<!-- agendado: {receipt['requested_timestamp']} -->"
    if SCHEDULED_MARKER_RE.search(text):
        raise ValueError("post already has an agendado marker")
    source.write_text(text.rstrip() + "\n\n" + marker + "\n", encoding="utf-8")
    target_dir = Path(destination)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / source.name
    if target.exists():
        raise ValueError("target already exists")
    _git_mv(source, target)
    return target


def cli_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LinkedIn scheduling validation and receipts")
    commands = parser.add_subparsers(dest="command", required=True)

    def add_request_args(command):
        command.add_argument("file")
        command.add_argument("timestamp")
        command.add_argument("--approved", action="store_true")
        command.add_argument("--now")

    validate = commands.add_parser("validate", help="validate a draft and print the request")
    add_request_args(validate)

    prepare = commands.add_parser("prepare", help="validate a draft and persist an initial receipt")
    add_request_args(prepare)
    prepare.add_argument("--run-id")
    prepare.add_argument("--runs-dir", default=str(ROOT / "runs" / "scheduling"))

    receipt = commands.add_parser("receipt", help="complete a receipt from verified browser evidence")
    receipt.add_argument("path")
    receipt.add_argument("--displayed-timestamp", required=True)
    receipt.add_argument("--browser-state-json", required=True)
    receipt.add_argument("--events-json", required=True)

    reconcile = commands.add_parser("reconcile", help="reconcile local content state")
    reconcile.add_argument("--content", default=str(ROOT / "content"))
    reconcile.add_argument("--topics", action="append", default=[])
    reconcile.add_argument("--output", default=str(ROOT / "runs" / "scheduling-reconciliation.yaml"))

    args = parser.parse_args(argv)
    try:
        if args.command in {"validate", "prepare"}:
            request = validate_scheduling_request(
                args.file, args.timestamp, approved=args.approved, now=args.now
            )
            if args.command == "validate":
                print(yaml.safe_dump(request, sort_keys=False, allow_unicode=True), end="")
            else:
                path = prepare_run(request, run_id=args.run_id, runs_dir=args.runs_dir)
                print(path)
            return 0
        if args.command == "receipt":
            result = complete_receipt(
                args.path,
                displayed_timestamp=args.displayed_timestamp,
                browser_state=json.loads(args.browser_state_json),
                events=json.loads(args.events_json),
            )
            print(yaml.safe_dump(result, sort_keys=False, allow_unicode=True), end="")
            return 0
        if args.command == "reconcile":
            from scheduling_reconciliation import cli_reconcile

            topic_paths = [ROOT / "research" / "topics" / name for name in args.topics]
            return cli_reconcile(
                ["--content", args.content, "--output", args.output]
                + sum((["--topics", name] for name in args.topics), []),
                topic_files=topic_paths,
            )
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"scheduling blocked: {error}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(cli_main())
