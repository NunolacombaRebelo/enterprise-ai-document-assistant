"""Tests for the frontend data models and response parsing (``frontend/api/models.py``)."""

from __future__ import annotations

import pytest
from frontend.api.models import Document, DocumentStatus, parse_document, parse_document_list


class TestParseDocument:
    def test_parses_full_document(self) -> None:
        doc = parse_document(
            {
                "id": "d1",
                "filename": "report.pdf",
                "status": "processed",
                "page_count": 10,
                "created_at": "2026-11-14T10:00:00Z",
            }
        )
        assert doc.id == "d1"
        assert doc.filename == "report.pdf"
        assert doc.status == "processed"
        assert doc.page_count == 10
        assert doc.created_at is not None
        assert doc.error is None

    def test_parses_error_document(self) -> None:
        doc = parse_document(
            {
                "id": "d1",
                "filename": "scan.pdf",
                "status": "error",
                "page_count": None,
                "created_at": "2026-11-14T10:00:00Z",
                "error": "No extractable text (scanned PDF).",
            }
        )
        assert doc.status == "error"
        assert doc.is_error
        assert doc.error == "No extractable text (scanned PDF)."
        assert doc.page_count is None

    def test_parses_minimal_document(self) -> None:
        doc = parse_document({"id": "d1", "filename": "a.pdf", "status": "processed"})
        assert doc.page_count is None
        assert doc.created_at is None
        assert doc.error is None

    def test_missing_id_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_document({"filename": "a.pdf", "status": "processed"})

    def test_missing_filename_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_document({"id": "d1", "status": "processed"})

    def test_missing_status_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_document({"id": "d1", "filename": "a.pdf"})

    def test_non_mapping_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_document(["not", "a", "dict"])

    def test_invalid_page_count_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_document(
                {"id": "d1", "filename": "a.pdf", "status": "processed", "page_count": "many"}
            )

    def test_invalid_error_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_document({"id": "d1", "filename": "a.pdf", "status": "error", "error": 123})

    def test_invalid_created_at_is_none(self) -> None:
        doc = parse_document(
            {"id": "d1", "filename": "a.pdf", "status": "processed", "created_at": "not-a-date"}
        )
        assert doc.created_at is None


class TestParseDocumentList:
    def test_parses_list(self) -> None:
        docs = parse_document_list(
            {
                "documents": [
                    {"id": "d1", "filename": "a.pdf", "status": "processed"},
                    {"id": "d2", "filename": "b.pdf", "status": "error", "error": "bad pdf"},
                ]
            }
        )
        assert len(docs) == 2
        assert docs[1].is_error
        assert docs[1].error == "bad pdf"

    def test_empty_list(self) -> None:
        assert parse_document_list({"documents": []}) == []

    def test_missing_documents_key_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_document_list({})

    def test_non_mapping_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_document_list("not a dict")

    def test_non_list_documents_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_document_list({"documents": "nope"})


class TestDocumentStatus:
    def test_no_active_statuses_in_milestone_1(self) -> None:
        # Processing is synchronous on the backend, so no document is "in flight" when returned.
        assert not Document(id="d1", filename="a.pdf", status="processed").is_active
        assert not Document(id="d1", filename="a.pdf", status="error").is_active

    def test_is_error(self) -> None:
        assert Document(id="d1", filename="a.pdf", status="error").is_error
        assert not Document(id="d1", filename="a.pdf", status="processed").is_error

    def test_known_status_constants(self) -> None:
        assert DocumentStatus.PROCESSED == "processed"
        assert DocumentStatus.ERROR == "error"
