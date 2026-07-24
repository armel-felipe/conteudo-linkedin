"""Read and write Markdown editorial records with JSON metadata."""

import json
import os
import tempfile
from pathlib import Path


OPENING_DELIMITER = "---json\n"
CLOSING_DELIMITER = "\n---\n"


def write_post_record(path, metadata, body):
    """Atomically write a Markdown record with deterministic JSON metadata."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    content = (
        OPENING_DELIMITER
        + json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n---\n\n"
        + body.strip()
        + "\n"
    )
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, target)
        temporary_path = None
        directory_fd = os.open(target.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


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
