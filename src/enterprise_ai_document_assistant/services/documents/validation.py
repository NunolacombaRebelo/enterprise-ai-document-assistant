"""Upload validation for document management (Milestone 1).

Uploaded files are treated as untrusted input. This module enforces, before any processing:

- file type (PDF extension and ``%PDF`` magic bytes),
- size (against ``settings.max_upload_bytes``),
- non-empty content,
- a safe, sanitized filename (no path separators, no traversal, bounded length),
- a safe storage key (UUID-based, so the stored file can never escape the documents directory).

It never executes uploaded content and never logs file contents.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass

logger = logging.getLogger(__name__)

#: Magic bytes that begin every PDF file.
PDF_MAGIC = b"%PDF"

#: Maximum length of a sanitized filename (characters).
MAX_FILENAME_LENGTH = 200

#: Characters that are never allowed in a stored filename.
_UNSAFE_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


class UploadValidationError(Exception):
    """Raised when an uploaded file fails a pre-processing validation check.

    Mapped to HTTP 400 by the API layer.
    """


@dataclass(frozen=True)
class ValidatedUpload:
    """Result of a successful validation: the safe filename and the raw bytes to process."""

    filename: str
    data: bytes


def sanitize_filename(raw_name: str | None) -> str:
    """Return a safe, portable filename derived from the uploaded name.

    - Strips any directory components (Windows and POSIX separators).
    - Removes path-traversal sequences (``..``) and unsafe characters.
    - Collapses whitespace, trims, and falls back to a default when empty.
    - Enforces a maximum length.

    The result is used only for display/metadata; the on-disk name is a separate UUID key.
    """
    name = (raw_name or "").strip()
    # Take only the final path component regardless of separator style.
    name = name.replace("\\", "/").rsplit("/", 1)[-1]
    # Strip traversal sequences.
    name = name.replace("..", "")
    # Remove unsafe characters (control chars, separators, shell/OS metacharacters).
    name = _UNSAFE_FILENAME_CHARS.sub("", name)
    # Normalize unicode to a stable form and collapse internal whitespace.
    name = unicodedata.normalize("NFC", name)
    name = re.sub(r"\s+", " ", name).strip()
    if not name:
        name = "document.pdf"
    if len(name) > MAX_FILENAME_LENGTH:
        stem, dot, ext = name.rpartition(".")
        if dot and len(ext) <= 8:
            name = stem[: MAX_FILENAME_LENGTH - len(ext) - 1] + "." + ext
        else:
            name = name[:MAX_FILENAME_LENGTH]
    return name


def validate_pdf_upload(filename: str | None, data: bytes, max_bytes: int) -> ValidatedUpload:
    """Validate an uploaded PDF and return a :class:`ValidatedUpload`.

    Raises :class:`UploadValidationError` (HTTP 400) on any failure.
    """
    safe_name = sanitize_filename(filename)

    if not data:
        logger.warning("Rejected empty upload (filename=%s)", safe_name)
        raise UploadValidationError("The uploaded file is empty.")

    if len(data) > max_bytes:
        # Do not log the size in a way that could leak; the limit is a fixed config value.
        logger.warning(
            "Rejected oversized upload (filename=%s, limit_bytes=%d)", safe_name, max_bytes
        )
        raise UploadValidationError(
            f"The uploaded file exceeds the maximum size of {max_bytes} bytes."
        )

    if not data.startswith(PDF_MAGIC):
        logger.warning("Rejected non-PDF upload (filename=%s)", safe_name)
        raise UploadValidationError("The uploaded file is not a valid PDF (missing %PDF header).")

    return ValidatedUpload(filename=safe_name, data=data)
