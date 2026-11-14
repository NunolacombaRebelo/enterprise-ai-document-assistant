"""Unit tests for upload validation (Milestone 1).

Covers type, size, empty, and filename/path-traversal handling. No network, no credentials.
"""

from __future__ import annotations

import pytest

from enterprise_ai_document_assistant.services.documents.validation import (
    UploadValidationError,
    sanitize_filename,
    validate_pdf_upload,
)

from .pdf_factory import make_non_pdf_bytes, make_pdf_bytes


def test_valid_pdf_passes() -> None:
    result = validate_pdf_upload("report.pdf", make_pdf_bytes(2), max_bytes=1024 * 1024)
    assert result.filename == "report.pdf"
    assert result.data.startswith(b"%PDF")


def test_empty_upload_rejected() -> None:
    with pytest.raises(UploadValidationError):
        validate_pdf_upload("empty.pdf", b"", max_bytes=1024)


def test_non_pdf_rejected() -> None:
    with pytest.raises(UploadValidationError):
        validate_pdf_upload("notes.txt", make_non_pdf_bytes(), max_bytes=1024)


def test_oversized_upload_rejected() -> None:
    big = make_pdf_bytes(1) + b"x" * 1000
    with pytest.raises(UploadValidationError):
        validate_pdf_upload("big.pdf", big, max_bytes=100)


def test_sanitize_strips_path_traversal() -> None:
    assert ".." not in sanitize_filename("../../etc/passwd.pdf")
    assert "/" not in sanitize_filename("a/b/c.pdf")
    assert "\\" not in sanitize_filename("a\\b\\c.pdf")


def test_sanitize_removes_unsafe_chars() -> None:
    assert '"' not in sanitize_filename('bad"name?.pdf')
    assert "<" not in sanitize_filename("<script>.pdf")


def test_sanitize_falls_back_to_default_when_empty() -> None:
    assert sanitize_filename("") == "document.pdf"
    assert sanitize_filename(None) == "document.pdf"
    assert sanitize_filename("///") == "document.pdf"


def test_sanitize_preserves_normal_name() -> None:
    assert sanitize_filename("  My Report 2026.pdf ") == "My Report 2026.pdf"


def test_sanitize_limits_length() -> None:
    long_name = "a" * 500 + ".pdf"
    result = sanitize_filename(long_name)
    assert len(result) <= 200
    assert result.endswith(".pdf")
