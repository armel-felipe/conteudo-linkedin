"""Editorial workflow operations that keep research, ideas, and drafts linked."""

from pathlib import Path

from content_ops.db import Database
from content_ops.markdown import write_post_record


def create_idea(
    database: Database, research_path: str, pillar: str, angle: str
) -> dict[str, object]:
    """Create an idea only when its research and pillar are eligible."""
    if not database.pillar_is_approved(pillar):
        raise ValueError(f"Pillar {pillar!r} is not approved")
    if not database.research_report_exists(research_path):
        raise ValueError(f"Research report {research_path!r} does not exist")

    idea_id = database.create_idea(angle, pillar, research_path)
    return {"id": idea_id, "research_path": research_path, "pillar": pillar, "angle": angle}


def create_draft(
    database: Database, idea: dict[str, object], pillar: str, path: str | Path
) -> Path:
    """Create a non-approved Markdown draft that retains its research source."""
    persisted_idea = database.create_draft_for_idea(int(idea["id"]), pillar)
    draft_path = Path(path)
    draft_path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "approved": False,
        "idea_id": persisted_idea["id"],
        "image_url": None,
        "objective": "authority_and_job_opportunities",
        "pillar": pillar,
        "research_path": persisted_idea["research_path"],
        "status": "draft",
        "zernio_post_id": None,
    }
    metadata["post_id"] = persisted_idea["post_id"]
    idea["post_id"] = persisted_idea["post_id"]
    write_post_record(draft_path, metadata, f"Ângulo: {persisted_idea['angle']}")
    return draft_path
