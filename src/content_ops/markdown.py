"""Read and write Markdown editorial records with JSON metadata."""

import json
from pathlib import Path


OPENING_DELIMITER = "---json\n"
CLOSING_DELIMITER = "\n---\n"


def write_post_record(path, metadata, body):
    """Write a Markdown record containing JSON metadata and a trimmed body."""
    Path(path).write_text(
        OPENING_DELIMITER
        + json.dumps(metadata, ensure_ascii=False, indent=2)
        + "\n---\n\n"
        + body.strip()
        + "\n",
        encoding="utf-8",
    )


def read_post_record(path) -> tuple[dict, str]:
    """Return metadata and body from a delimited Markdown editorial record."""
    content = Path(path).read_text(encoding="utf-8")
    if not content.startswith(OPENING_DELIMITER):
        raise ValueError("Markdown record is missing the opening delimiter")

    metadata_and_body = content[len(OPENING_DELIMITER) :]
    if CLOSING_DELIMITER not in metadata_and_body:
        raise ValueError("Markdown record is missing the closing delimiter")

    metadata_text, body = metadata_and_body.split(CLOSING_DELIMITER, maxsplit=1)
    metadata = json.loads(metadata_text)
    if not isinstance(metadata, dict):
        raise ValueError("Markdown record metadata must be a JSON object")

    body = body.strip()
    if not body:
        raise ValueError("Markdown record body cannot be empty")

    return metadata, body
