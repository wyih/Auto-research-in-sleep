"""Resolve and validate the Office author identity without a maintainer default."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path


OFFICE_AUTHOR_ENV = "ARIS_OFFICE_AUTHOR"
OFFICE_AUTHOR_FILE_ENV = "ARIS_OFFICE_AUTHOR_FILE"


class OfficeAuthorError(ValueError):
    """Raised when an Office author identity is absent or unsafe."""


def validate_office_author(value: str) -> str:
    """Return a normalized author string suitable for OOXML metadata."""
    author = value.strip()
    if not author:
        raise OfficeAuthorError("Office author identity must not be empty")
    if len(author) > 200:
        raise OfficeAuthorError("Office author identity must be 200 characters or fewer")
    if any(ord(character) < 32 or ord(character) == 127 for character in author):
        raise OfficeAuthorError("Office author identity must not contain control characters")
    return author


def resolve_office_author(
    explicit: str | None,
    *,
    environ: Mapping[str, str] | None = None,
) -> str:
    """Resolve explicit, environment, then installer-created user identity."""
    if explicit is not None:
        return validate_office_author(explicit)

    environment = os.environ if environ is None else environ
    configured = environment.get(OFFICE_AUTHOR_ENV)
    if configured is not None:
        return validate_office_author(configured)

    configured_path = environment.get(OFFICE_AUTHOR_FILE_ENV)
    path = (
        Path(configured_path).expanduser()
        if configured_path
        else Path.home() / ".aris" / "office-author"
    )
    try:
        if path.is_file():
            return validate_office_author(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as error:
        raise OfficeAuthorError(
            f"Could not read the user-local Office author configuration: {path}"
        ) from error

    raise OfficeAuthorError(
        f"Office author identity is required; pass --author, set {OFFICE_AUTHOR_ENV}, "
        "or install with --office-author/-OfficeAuthor"
    )
