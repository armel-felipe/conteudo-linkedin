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
    ideas = commands.add_parser("ideas", help="Create research-backed content ideas")
    idea_commands = ideas.add_subparsers(dest="ideas_command")
    idea_creation = idea_commands.add_parser("create", help="Create an idea from captured research")
    idea_creation.add_argument("--research", required=True)
    idea_creation.add_argument("--pillar", required=True)
    idea_creation.add_argument("--angle", required=True)
    draft = commands.add_parser("draft", help="Create non-approved Markdown drafts")
    draft_commands = draft.add_subparsers(dest="draft_command")
    draft_creation = draft_commands.add_parser("create", help="Create a draft from an idea")
    draft_creation.add_argument("idea_id", type=int)
    review = commands.add_parser("review", help="Record an explicit draft approval")
    review_commands = review.add_subparsers(dest="review_command")
    review_approval = review_commands.add_parser("approve", help="Approve a post in review")
    review_approval.add_argument("post_id", type=int)
    schedule = commands.add_parser("schedule", help="Schedule an explicitly approved post")
    schedule.add_argument("post_id", type=int)
    schedule.add_argument("--at", required=True, dest="scheduled_for")
    schedule.add_argument("--confirm", action="store_true")
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


def main(argv: Sequence[str] | None = None) -> None:
    repository_root = Path(__file__).resolve().parents[2]
    load_env(repository_root / ".env")
    parser = build_parser()
    arguments = parser.parse_args(argv)

    if arguments.command == "schedule" and not arguments.confirm:
        parser.error("--confirm is required")

    if arguments.command in {"review", "schedule"}:
        from content_ops.db import Database
        from content_ops.workflow import (
            SchedulingError,
            SchedulingValidationError,
            approve_draft,
            schedule_post,
        )

        database = Database(repository_root / "data" / "content.db")
        database.initialize()
        try:
            markdown_path = _find_post_markdown(repository_root, arguments.post_id)
            if arguments.command == "review":
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

            zernio_post_id = schedule_post(
                arguments.post_id,
                markdown_path,
                arguments.scheduled_for,
                arguments.confirm,
                ZernioClient(os.environ["ZERNIO_API_KEY"]),
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

        if (arguments.command, arguments.research_command) == ("research", "discover"):
            command = os.environ.get("LAST30DAYS_COMMAND")
            if not command:
                parser.error("Missing required configuration: LAST30DAYS_COMMAND")
            relative_path = Path("research") / _research_filename(arguments.topic)
            try:
                capture_research(arguments.topic, command, repository_root / relative_path)
                database.create_research_report(arguments.topic, str(relative_path))
            except (RuntimeError, ValueError) as error:
                parser.error(str(error))
            print(f"Captured research in {relative_path}.")
            return

        if (arguments.command, arguments.ideas_command) == ("ideas", "create"):
            try:
                idea = create_idea(
                    database, arguments.research, arguments.pillar, arguments.angle
                )
            except ValueError as error:
                parser.error(str(error))
            print(f"Created idea {idea['id']}.")
            return

        if (arguments.command, arguments.draft_command) == ("draft", "create"):
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

    if arguments.command == "pillars":
        from content_ops.db import Database
        from content_ops.pillars import approve_pillar, write_pillar_proposals

        database = Database(repository_root / "data" / "content.db")
        database.initialize()
        document_path = repository_root / "docs" / "pillars.md"
        if arguments.pillars_command == "propose":
            proposals = write_pillar_proposals(
                document_path, database, database.list_published_posts()
            )
            print(f"Proposed {len(proposals)} pillars in {document_path.relative_to(repository_root)}.")
        elif arguments.pillars_command == "approve":
            try:
                approve_pillar(document_path, database, arguments.name)
            except ValueError as error:
                parser.error(str(error))
            print(f"Approved pillar: {arguments.name}")
        return

    if (arguments.command, arguments.history_command) != ("history", "import"):
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
