"""Unit tests for local document storage (Milestone 1).

Uses a temporary directory (pytest ``tmp_path``) so no runtime data is written into the repo.
"""

from __future__ import annotations

import pytest

from enterprise_ai_document_assistant.services.documents.models import DocumentStatus
from enterprise_ai_document_assistant.services.documents.storage import (
    DocumentNotFoundError,
    DocumentStore,
    build_metadata,
)


def test_save_and_get_roundtrip(tmp_path) -> None:
    store = DocumentStore(tmp_path)
    meta = build_metadata("doc-1", "a.pdf", DocumentStatus.PROCESSED, page_count=2)
    store.save("doc-1", b"%PDF-1.4 fake", meta)

    loaded = store.get("doc-1")
    assert loaded.id == "doc-1"
    assert loaded.filename == "a.pdf"
    assert loaded.status == DocumentStatus.PROCESSED
    assert loaded.page_count == 2
    assert (tmp_path / "doc-1.pdf").exists()
    assert (tmp_path / "doc-1.json").exists()


def test_get_missing_raises(tmp_path) -> None:
    store = DocumentStore(tmp_path)
    with pytest.raises(DocumentNotFoundError):
        store.get("does-not-exist")


def test_list_returns_most_recent_first(tmp_path) -> None:
    store = DocumentStore(tmp_path)
    older = build_metadata("old", "old.pdf", DocumentStatus.PROCESSED, page_count=1)
    newer = build_metadata("new", "new.pdf", DocumentStatus.PROCESSED, page_count=1)
    # Force an ordering by adjusting created_at.
    older.created_at = older.created_at.replace(microsecond=0)
    newer.created_at = newer.created_at.replace(microsecond=999999)
    store.save("old", b"%PDF-1.4 a", older)
    store.save("new", b"%PDF-1.4 b", newer)

    docs = store.list()
    assert [d.id for d in docs] == ["new", "old"]


def test_delete_removes_files(tmp_path) -> None:
    store = DocumentStore(tmp_path)
    meta = build_metadata("doc-1", "a.pdf", DocumentStatus.PROCESSED, page_count=1)
    store.save("doc-1", b"%PDF-1.4", meta)
    store.delete("doc-1")
    assert not (tmp_path / "doc-1.pdf").exists()
    assert not (tmp_path / "doc-1.json").exists()


def test_list_skips_corrupt_metadata(tmp_path) -> None:
    store = DocumentStore(tmp_path)
    meta = build_metadata("ok", "ok.pdf", DocumentStatus.PROCESSED, page_count=1)
    store.save("ok", b"%PDF-1.4", meta)
    (tmp_path / "bad.json").write_text("not valid json", encoding="utf-8")

    docs = store.list()
    assert [d.id for d in docs] == ["ok"]
