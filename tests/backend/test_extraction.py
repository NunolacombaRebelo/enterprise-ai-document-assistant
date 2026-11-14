"""Unit tests for PDF text extraction (Milestone 1).

Covers successful extraction, encrypted PDFs, and malformed PDFs. No network, no credentials.
"""

from __future__ import annotations

import pytest

from enterprise_ai_document_assistant.services.documents.extraction import (
    EncryptedPdfError,
    MalformedPdfError,
    extract_pdf,
)

from .pdf_factory import make_encrypted_pdf_bytes, make_pdf_bytes


def test_extract_page_count_and_text() -> None:
    result = extract_pdf(make_pdf_bytes(3))
    assert result.page_count == 3
    assert "Page 1" in result.text
    assert "Page 3" in result.text


def test_extract_single_page() -> None:
    result = extract_pdf(make_pdf_bytes(1))
    assert result.page_count == 1
    assert "Page 1" in result.text


def test_encrypted_pdf_raises() -> None:
    with pytest.raises(EncryptedPdfError):
        extract_pdf(make_encrypted_pdf_bytes())


def test_malformed_pdf_raises() -> None:
    # A %PDF header followed by garbage is not a parseable PDF.
    with pytest.raises(MalformedPdfError):
        extract_pdf(b"%PDF-1.4\nthis is not a real pdf body")
