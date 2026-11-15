"""Tests for structure-aware chunking (Milestone 2).

Covers single/multi-page documents, empty content, paragraph boundaries, word-boundary safety,
overlap, deterministic ids, and accurate page attribution. No network, no models.
"""

from __future__ import annotations

import pytest

from enterprise_ai_document_assistant.services.documents.extraction import PageText
from enterprise_ai_document_assistant.services.retrieval.chunking import (
    ChunkingConfig,
    approx_token_count,
    chunk_pages,
    chunk_text,
)


def _pages(*texts: str) -> list[PageText]:
    return [PageText(page=i + 1, text=t) for i, t in enumerate(texts)]


def test_single_page_single_chunk() -> None:
    chunks = chunk_pages(
        _pages("A short single paragraph."),
        document_id="d1",
        filename="a.pdf",
        created_at="2026-11-15T00:00:00+00:00",
    )
    assert len(chunks) == 1
    assert chunks[0].page == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].id == "d1:0"
    assert chunks[0].text == "A short single paragraph."


def test_multi_page_preserves_page_boundaries() -> None:
    chunks = chunk_pages(
        _pages("First page text.", "Second page text.", "Third page text."),
        document_id="d1",
        filename="a.pdf",
        created_at="2026-11-15T00:00:00+00:00",
    )
    assert [c.page for c in chunks] == [1, 2, 3]
    # chunk_index is sequential across the whole document.
    assert [c.chunk_index for c in chunks] == [0, 1, 2]
    # No chunk spans two pages.
    assert all(
        c.text in ("First page text.", "Second page text.", "Third page text.") for c in chunks
    )


def test_empty_pages_produce_no_chunks() -> None:
    chunks = chunk_pages(
        _pages("", "   ", "\n\n"),
        document_id="d1",
        filename="a.pdf",
        created_at="2026-11-15T00:00:00+00:00",
    )
    assert chunks == []


def test_mixed_empty_and_content_pages() -> None:
    chunks = chunk_pages(
        _pages("", "Real content here.", ""),
        document_id="d1",
        filename="a.pdf",
        created_at="2026-11-15T00:00:00+00:00",
    )
    assert len(chunks) == 1
    assert chunks[0].page == 2
    assert chunks[0].chunk_index == 0


def test_paragraph_boundaries_are_preserved() -> None:
    """Paragraphs are never split mid-paragraph; they may be packed into a chunk together."""
    text = "First paragraph about refunds.\n\nSecond paragraph about shipping.\n\nThird paragraph."
    chunks = chunk_text(text, "d1", "a.pdf", "2026-11-15T00:00:00+00:00")
    # All three paragraphs are present in the chunk text (none lost).
    combined = " ".join(c.text for c in chunks)
    assert "First paragraph about refunds." in combined
    assert "Second paragraph about shipping." in combined
    assert "Third paragraph." in combined
    # No paragraph is split across chunks: each paragraph appears wholly within one chunk.
    for para in (
        "First paragraph about refunds.",
        "Second paragraph about shipping.",
        "Third paragraph.",
    ):
        assert any(para in c.text for c in chunks)


def test_paragraphs_split_into_separate_chunks_when_oversized() -> None:
    """With a small target size, each paragraph becomes its own chunk."""
    text = "First paragraph about refunds.\n\nSecond paragraph about shipping.\n\nThird paragraph."
    cfg = ChunkingConfig(target_size_tokens=5, overlap_tokens=0)
    chunks = chunk_text(text, "d1", "a.pdf", "2026-11-15T00:00:00+00:00", config=cfg)
    # Each paragraph (4-5 words) exceeds the 5-word target only when combined, so they separate.
    assert len(chunks) >= 3


def test_large_paragraph_split_at_word_boundary() -> None:
    # A single paragraph far larger than the target size is split at word boundaries.
    words = " ".join(f"w{i}" for i in range(200))
    cfg = ChunkingConfig(target_size_tokens=50, overlap_tokens=0)
    chunks = chunk_text(words, "d1", "a.pdf", "2026-11-15T00:00:00+00:00", config=cfg)
    assert len(chunks) == 4  # 200 words / 50 per chunk
    # No word is split: every token in every chunk is a full word.
    for c in chunks:
        for token in c.text.split():
            assert token.startswith("w") and token[1:].isdigit()
    # All original words are present (reconstruction).
    assert " ".join(t for c in chunks for t in c.text.split()) == words


def test_overlap_carries_context_between_chunks() -> None:
    words = " ".join(f"w{i}" for i in range(120))
    cfg = ChunkingConfig(target_size_tokens=50, overlap_tokens=10)
    chunks = chunk_text(words, "d1", "a.pdf", "2026-11-15T00:00:00+00:00", config=cfg)
    assert len(chunks) == 3
    # The second chunk starts with the tail of the first chunk (overlap).
    first_tail = chunks[0].text.split()[-10:]
    assert chunks[1].text.split()[:10] == first_tail


def test_chunk_ids_are_deterministic() -> None:
    pages = _pages("Alpha beta gamma.", "Delta epsilon zeta.")
    a = chunk_pages(pages, "d1", "a.pdf", "2026-11-15T00:00:00+00:00")
    b = chunk_pages(pages, "d1", "a.pdf", "2026-11-15T00:00:00+00:00")
    assert [c.id for c in a] == [c.id for c in b]
    assert [c.text for c in a] == [c.text for c in b]
    assert [c.page for c in a] == [c.page for c in b]


def test_chunk_ids_unique_across_documents() -> None:
    pages = _pages("Same text on page one.")
    a = chunk_pages(pages, "doc-a", "a.pdf", "2026-11-15T00:00:00+00:00")
    b = chunk_pages(pages, "doc-b", "b.pdf", "2026-11-15T00:00:00+00:00")
    ids = [c.id for c in a] + [c.id for c in b]
    assert len(ids) == len(set(ids))
    assert a[0].id == "doc-a:0"
    assert b[0].id == "doc-b:0"


def test_char_offsets_within_page() -> None:
    text = "Hello world. This is a test."
    chunks = chunk_text(text, "d1", "a.pdf", "2026-11-15T00:00:00+00:00")
    assert len(chunks) == 1
    c = chunks[0]
    assert c.char_start == 0
    assert c.char_end == len(text)
    assert text[c.char_start : c.char_end] == c.text


def test_approx_token_count() -> None:
    assert approx_token_count("") == 0
    assert approx_token_count("   ") == 0
    assert approx_token_count("one two three") == 3


def test_invalid_config_rejected() -> None:
    with pytest.raises(ValueError):
        ChunkingConfig(target_size_tokens=0)
    with pytest.raises(ValueError):
        ChunkingConfig(target_size_tokens=10, overlap_tokens=10)
    with pytest.raises(ValueError):
        ChunkingConfig(target_size_tokens=10, overlap_tokens=-1)
