"""Command-line entry point for local content operations."""

import argparse
import os
import re
import unicodedata
from datetime import date
from pathlib import Path
from typing import Sequence


def load_env(path: Path) -> None:
    """Load simple KEY=VALUE entries without replacing existing environment values."""
    if not path.is_file():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key:
            os.environ.setdefault(key, value.strip())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="contentctl")
    commands = parser.add_subparsers(dest="command")
    history = commands.add_parser("history", help="Import local history from Zernio")
    history.add_subparsers(dest="history_command").add_parser(
        "import", help="Import external posts without publishing"
    )
    blocks = commands.add_parser("bloco-ok", help="Register a reviewer's block validation")
    blocks.add_argument("bloco")
    blocks.add_argument("artefato")
    blocks.add_argument("--round", dest="round_id", type=int)
    blocks.add_argument("--cycle", type=int)
    cycle_start = commands.add_parser("workflow-cycle-start", help="Start a workflow block cycle")
    cycle_start.add_argument("round_id", type=int)
    cycle_start.add_argument("block")
    cycle_start.add_argument("artifact")
    workflow_review = commands.add_parser("workflow-review", help="Persist a structured reviewer receipt")
    workflow_review.add_argument("round_id", type=int)
    workflow_review.add_argument("block")
    workflow_review.add_argument("artifact")
    workflow_review.add_argument("cycle", type=int)
    workflow_review.add_argument("reviewer")
    workflow_review.add_argument("result")
    block_complete = commands.add_parser("workflow-block-complete", help="Complete an approved workflow block")
    block_complete.add_argument("round_id", type=int)
    block_complete.add_argument("block")
    block_complete.add_argument("artifact")
    block_complete.add_argument("cycle", type=int)
    pillars = commands.add_parser("pillars", help="Propose and approve editorial pillars")
    pillar_commands = pillars.add_subparsers(dest="pillars_command")
    pillar_commands.add_parser("propose", help="Propose pillars from published history")
    approval = pillar_commands.add_parser("approve", help="Approve one proposed pillar")
    approval.add_argument("name")
    research = commands.add_parser("research", help="Capture recent research")
    research_commands = research.add_subparsers(dest="research_command")
    discovery = research_commands.add_parser(
        "discover", help="Capture configured Last30days output without creating ideas"
    )
    discovery.add_argument("topic")
    discovery.add_argument(
        "--pillar", help="Optional editorial theme this research belongs to"
    )
    ideas = commands.add_parser("ideas", help="Create research-backed content ideas")
    idea_commands = ideas.add_subparsers(dest="ideas_command")
    idea_creation = idea_commands.add_parser("create", help="Create an idea from captured research")
    idea_creation.add_argument("--research", required=True)
    idea_creation.add_argument("--pillar", required=True)
    idea_creation.add_argument("--angle", required=True)
    idea_creation.add_argument(
        "--sources",
        help="Comma-separated research paths that sustain this idea (multi-pesquisa)",
    )
    draft = commands.add_parser("draft", help="Create non-approved Markdown drafts")
    draft_commands = draft.add_subparsers(dest="draft_command")
    draft_creation = draft_commands.add_parser("create", help="Create a draft from an idea")
    draft_creation.add_argument("idea_id", type=int)
    review = commands.add_parser("review", help="Record an explicit draft approval")
    review_commands = review.add_subparsers(dest="review_command")
    review_submission = review_commands.add_parser(
        "submit", help="Submit a draft for human review"
    )
    review_submission.add_argument("post_id", type=int)
    review_approval = review_commands.add_parser("approve", help="Approve a post in review")
    review_approval.add_argument("post_id", type=int)
    schedule = commands.add_parser("schedule", help="Schedule an explicitly approved post")
    schedule.add_argument("post_id")
    schedule.add_argument("reconcile_post_id", nargs="?")
    schedule.add_argument("--at", dest="scheduled_for")
    schedule.add_argument("--confirm", action="store_true")
    publish = commands.add_parser(
        "publish-complete", help="Move an approved post to content/published/"
    )
    publish.add_argument("post_id", type=int)
    publish.add_argument("url")
    report = commands.add_parser("report", help="Inspect local operational metrics")
    report_commands = report.add_subparsers(dest="report_command")
    weekly = report_commands.add_parser("weekly", help="Show one Monday-to-Sunday report")
    weekly.add_argument("--week", required=True, help="Monday date in YYYY-MM-DD format")
    posts = commands.add_parser("posts", help="Synchronize published post state")
    post_commands = posts.add_subparsers(dest="posts_command")
    post_sync = post_commands.add_parser("sync", help="Read one Zernio post without publishing")
    post_sync.add_argument("post_id", type=int)
    return parser


def _research_filename(topic: str) -> str:
    normalized = unicodedata.normalize("NFKD", topic).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-") or "research"
    return f"{date.today().isoformat()}--{slug}.md"


def _find_post_markdown(repository_root: Path, post_id: int) -> Path:
    """Locate the one editorial record whose metadata belongs to ``post_id``."""
    from content_ops.markdown import read_post_record

    matches: list[Path] = []
    for path in (repository_root / "content").rglob("*.md"):
        try:
            metadata, _ = read_post_record(path)
        except (OSError, ValueError):
            continue
        if metadata.get("post_id") == post_id:
            matches.append(path)
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one Markdown record for post {post_id}")
    return matches[0]


def main(
    argv: Sequence[str] | None = None,
    *,
    repository_root: Path | None = None,
) -> None:
    repository_root = (
        Path(__file__).resolve().parents[2]
        if repository_root is None
        else Path(repository_root)
    )
    load_env(repository_root / ".env")
    parser = build_parser()
    arguments = parser.parse_args(argv)

    if arguments.command in {"workflow-cycle-start", "workflow-review", "workflow-block-complete"}:
        from content_ops.db import Database
        from content_ops.orchestration import (
            InvalidReviewResult,
            WorkflowBlocked,
            complete_block,
            record_review,
            start_block_cycle,
        )

        database = Database(repository_root / "data" / "content.db")
        database.initialize()
        try:
            if arguments.command == "workflow-cycle-start":
                print(start_block_cycle(database, arguments.round_id, arguments.block, arguments.artifact))
                return
            if arguments.command == "workflow-review":
                record_review(database, arguments.round_id, arguments.block, arguments.artifact,
                              arguments.cycle, arguments.reviewer, arguments.result)
                print(f"Recorded review for {arguments.block} cycle {arguments.cycle}.")
                return
            complete_block(database, arguments.round_id, arguments.block, arguments.artifact, arguments.cycle)
            print(f"Completed {arguments.block}.")
            return
        except (InvalidReviewResult, WorkflowBlocked, ValueError) as error:
            parser.error(str(error))

    is_reconcile = (
        arguments.command == "schedule" and arguments.post_id == "reconcile"
    )
    if arguments.command == "schedule":
        if is_reconcile:
            if arguments.reconcile_post_id is None:
                parser.error("schedule reconcile requires a post ID")
            try:
                arguments.post_id = int(arguments.reconcile_post_id)
            except ValueError:
                parser.error("post ID must be an integer")
        else:
            if arguments.reconcile_post_id is not None:
                parser.error("schedule accepts one post ID")
            try:
                arguments.post_id = int(arguments.post_id)
            except ValueError:
                parser.error("post ID must be an integer")
            if not arguments.confirm:
                parser.error("--confirm is required")
            if not arguments.scheduled_for:
                parser.error("--at is required")

    if (arguments.command, getattr(arguments, "report_command", None)) == ("report", "weekly"):
        from content_ops.db import Database
        from content_ops.reporting import weekly_report

        try:
            week_start = date.fromisoformat(arguments.week)
            database = Database(repository_root / "data" / "content.db")
            database.initialize()
            print(weekly_report(database, week_start))
        except ValueError as error:
            parser.error(str(error))
        return

    if (arguments.command, getattr(arguments, "posts_command", None)) == ("posts", "sync"):
        required = ("ZERNIO_API_KEY",)
        missing = [name for name in required if not os.environ.get(name)]
        if missing:
            parser.error(f"Missing required configuration: {', '.join(missing)}")
        from content_ops.db import Database
        from content_ops.reporting import sync_published_post
        from content_ops.zernio import ZernioClient, ZernioError

        database = Database(repository_root / "data" / "content.db")
        database.initialize()
        try:
            markdown_path = _find_post_markdown(
                repository_root, arguments.post_id
            )
            sync_published_post(
                ZernioClient(os.environ["ZERNIO_API_KEY"]),
                database,
                arguments.post_id,
                markdown_path,
            )
        except (ValueError, ZernioError) as error:
            parser.error(str(error))
        status = database.post_status(arguments.post_id).value
        messages = {
            "scheduled": f"Post {arguments.post_id} remains scheduled.",
            "published": f"Post {arguments.post_id} is published.",
            "failed": f"Post {arguments.post_id} failed.",
        }
        print(messages[status])
        return

    if arguments.command == "publish-complete":
        from content_ops.db import Database
        from content_ops.workflow import (
            SchedulingValidationError,
            publish_complete,
        )

        database = Database(repository_root / "data" / "content.db")
        database.initialize()
        try:
            markdown_path = _find_post_markdown(repository_root, arguments.post_id)
            published_path = publish_complete(
                arguments.post_id,
                arguments.url,
                markdown_path,
                database,
            )
        except (SchedulingValidationError, ValueError) as error:
            parser.error(str(error))
        print(f"Published post {arguments.post_id} -> {published_path.relative_to(repository_root)}.")
        return

    if arguments.command in {"review", "schedule"}:
        from content_ops.db import Database
        from content_ops.workflow import (
            SchedulingError,
            SchedulingValidationError,
            approve_draft,
            reconcile_schedule,
            schedule_post,
            submit_draft_for_review,
        )

        database = Database(repository_root / "data" / "content.db")
        database.initialize()
        try:
            markdown_path = _find_post_markdown(repository_root, arguments.post_id)
            if arguments.command == "review":
                if arguments.review_command == "submit":
                    submit_draft_for_review(
                        arguments.post_id, markdown_path, database=database
                    )
                    print(f"Submitted post {arguments.post_id} for review.")
                    return
                if arguments.review_command != "approve":
                    parser.error("A review action is required")
                approve_draft(arguments.post_id, markdown_path, database=database)
                print(f"Approved post {arguments.post_id}.")
                return

            required = ("ZERNIO_API_KEY", "ZERNIO_ACCOUNT_ID")
            missing = [name for name in required if not os.environ.get(name)]
            if missing:
                parser.error(f"Missing required configuration: {', '.join(missing)}")
            from content_ops.zernio import ZernioClient

            client = ZernioClient(os.environ["ZERNIO_API_KEY"])
            if is_reconcile:
                zernio_post_id = reconcile_schedule(
                    arguments.post_id,
                    markdown_path,
                    client,
                    database=database,
                    account_id=os.environ["ZERNIO_ACCOUNT_ID"],
                )
            else:
                zernio_post_id = schedule_post(
                    arguments.post_id,
                    markdown_path,
                    arguments.scheduled_for,
                    arguments.confirm,
                    client,
                    database=database,
                    account_id=os.environ["ZERNIO_ACCOUNT_ID"],
                )
        except (SchedulingValidationError, SchedulingError, ValueError) as error:
            parser.error(str(error))
        print(f"Scheduled post {arguments.post_id} as {zernio_post_id}.")
        return

    if arguments.command in {"research", "ideas", "draft"}:
        from content_ops.db import Database
        from content_ops.research import capture_research
        from content_ops.workflow import create_draft, create_idea

        database = Database(repository_root / "data" / "content.db")
        database.initialize()

        if (arguments.command, getattr(arguments, "research_command", None)) == (
            "research",
            "discover",
        ):
            command = os.environ.get("LAST30DAYS_COMMAND")
            if not command:
                parser.error("Missing required configuration: LAST30DAYS_COMMAND")
            relative_path = Path("research") / _research_filename(arguments.topic)
            try:
                capture_research(arguments.topic, command, repository_root / relative_path)
                database.create_research_report(
                    arguments.topic,
                    str(relative_path),
                    pillar=arguments.pillar,
                )
            except (RuntimeError, ValueError) as error:
                parser.error(str(error))
            print(f"Captured research in {relative_path}.")
            return

        if (arguments.command, getattr(arguments, "ideas_command", None)) == (
            "ideas",
            "create",
        ):
            sources = None
            if arguments.sources:
                sources = [s.strip() for s in arguments.sources.split(",") if s.strip()]
            try:
                idea = create_idea(
                    database,
                    arguments.research,
                    arguments.pillar,
                    arguments.angle,
                    ideas_directory=repository_root / "content" / "ideas",
                    sources=sources,
                )
            except ValueError as error:
                parser.error(str(error))
            print(f"Created idea {idea['id']}.")
            return

        if (arguments.command, getattr(arguments, "draft_command", None)) == (
            "draft",
            "create",
        ):
            try:
                idea = database.get_idea(arguments.idea_id)
                pillar = str(idea["pillar"])
                path = create_draft(
                    database,
                    idea,
                    pillar,
                    repository_root / "content" / "drafts" / f"idea-{idea['id']}.md",
                )
            except ValueError as error:
                parser.error(str(error))
            print(f"Created draft {path.relative_to(repository_root)} (post {idea['post_id']}).")
            return

        return

    if arguments.command == "bloco-ok":
        from content_ops.db import Database

        database = Database(repository_root / "data" / "content.db")
        database.initialize()
        if arguments.round_id is None or arguments.cycle is None:
            parser.error("bloco-ok requires --round and --cycle; use workflow-block-complete")
        from content_ops.orchestration import complete_block
        try:
            complete_block(database, arguments.round_id, arguments.bloco, arguments.artefato, arguments.cycle)
        except ValueError as error:
            parser.error(str(error))
        print(f"Registered validation for {arguments.bloco}.")
        return

    if arguments.command == "pillars":
        from content_ops.db import Database
        from content_ops.pillars import (
            approve_pillar,
            write_pillar_proposals_from_research,
        )

        database = Database(repository_root / "data" / "content.db")
        database.initialize()
        document_path = repository_root / "docs" / "pillars.md"
        if arguments.pillars_command == "propose":
            proposals = write_pillar_proposals_from_research(
                document_path, database
            )
            print(f"Proposed {len(proposals)} pillars in {document_path.relative_to(repository_root)}.")
        elif arguments.pillars_command == "approve":
            try:
                approve_pillar(document_path, database, arguments.name)
            except ValueError as error:
                parser.error(str(error))
            print(f"Approved pillar: {arguments.name}")
        return

    if (arguments.command, getattr(arguments, "history_command", None)) != (
        "history",
        "import",
    ):
        return

    required = ("ZERNIO_API_KEY", "ZERNIO_ACCOUNT_ID")
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        parser.error(f"Missing required configuration: {', '.join(missing)}")

    from content_ops.db import Database
    from content_ops.history import import_history
    from content_ops.zernio import ZernioClient

    database = Database(repository_root / "data" / "content.db")
    database.initialize()
    imported = import_history(
        ZernioClient(os.environ["ZERNIO_API_KEY"]),
        database,
        os.environ["ZERNIO_ACCOUNT_ID"],
        repository_root / "data" / "imports",
    )
    print(f"Imported {imported} posts.")


if __name__ == "__main__":
    main()
