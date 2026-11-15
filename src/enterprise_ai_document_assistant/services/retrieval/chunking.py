"""Structure-aware, deterministic text chunking (Milestone 2).

Splits a document's extracted text into chunks for indexing. Design goals (per the Milestone 2
requirements):

- Preserve page boundaries: a chunk never spans two pages; each chunk carries the page it starts on.
- Preserve paragraph boundaries where possible (split on blank lines before falling back to a size
  limit).
- Never split a word arbitrarily: when a size limit forces a split, it happens at a whitespace
  boundary.
- Configurable target chunk size and overlap (in tokens, approximated by whitespace-delimited
  words — see :func:`approx_token_count`). This avoids a tokenizer dependency while remaining
  deterministic and portable.
- Deterministic: identical input + configuration yields identical chunks (stable ids, order, and
  text) across repeated runs.
- Handles empty/whitespace-only content (returns no chunks) and multi-page documents.

The chunker does not pretend structure was extracted when it was not: it works from the per-page
text produced by the extraction pipeline. Headings are not separately parsed (the extraction
pipeline does not expose them); paragraph and page structure is what is reliably available.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from enterprise_ai_document_assistant.services.documents.extraction import PageText
from enterprise_ai_document_assistant.services.retrieval.models import Chunk

logger = logging.getLogger(__name__)

#: A paragraph break is one or more blank lines.
_PARAGRAPH_BREAK = re.compile(r"\n\s*\n")


@dataclass(frozen=True)
class ChunkingConfig:
    """Configuration for the chunker.

    ``target_size_tokens`` and ``overlap_tokens`` are approximate token budgets. They are measured
    in whitespace-delimited words (a deterministic, dependency-free approximation of tokens).
    """

    target_size_tokens: int = 400
    overlap_tokens: int = 60

    def __post_init__(self) -> None:
        if self.target_size_tokens < 1:
            raise ValueError("target_size_tokens must be >= 1")
        if self.overlap_tokens < 0:
            raise ValueError("overlap_tokens must be >= 0")
        if self.overlap_tokens >= self.target_size_tokens:
            raise ValueError("overlap_tokens must be < target_size_tokens")


def approx_token_count(text: str) -> int:
    """Approximate token count as the number of whitespace-delimited words.

    Deterministic and dependency-free. Empty/whitespace-only text yields 0.
    """
    return len(text.split())


def _split_paragraphs(text: str) -> list[str]:
    """Split text into non-empty paragraphs (preserving their internal text)."""
    return [p.strip() for p in _PARAGRAPH_BREAK.split(text) if p.strip()]


def _pack_paragraphs(paragraphs: list[str], target: int) -> list[str]:
    """Group paragraphs into blocks of at most ``target`` words.

    A single paragraph longer than ``target`` is hard-split at word boundaries into pieces of at
    most ``target`` words (never splitting a word).
    """
    blocks: list[str] = []
    current: list[str] = []
    current_len = 0

    def flush() -> None:
        nonlocal current, current_len
        if current:
            blocks.append(" ".join(current))
            current = []
            current_len = 0

    for para in paragraphs:
        words = para.split()
        if not words:
            continue
        para_len = len(words)
        # If the paragraph alone exceeds the target, split it into word-boundary pieces.
        if para_len > target:
            flush()
            for i in range(0, para_len, target):
                blocks.append(" ".join(words[i : i + target]))
            continue
        # If adding this paragraph would exceed the target, start a new block.
        if current and current_len + para_len > target:
            flush()
        current.append(para)
        current_len += para_len
    flush()
    return blocks


def _apply_overlap(blocks: list[str], overlap: int) -> list[str]:
    """Return blocks with ``overlap`` words carried from the end of the previous block.

    The overlap is taken from the tail of the previous block and prepended to the next, so context
    is preserved across chunk boundaries without duplicating whole paragraphs.
    """
    if overlap <= 0 or len(blocks) <= 1:
        return blocks
    result = [blocks[0]]
    for i in range(1, len(blocks)):
        prev_words = blocks[i - 1].split()
        tail = prev_words[-overlap:] if overlap < len(prev_words) else prev_words
        result.append(" ".join(tail + blocks[i].split()))
    return result


def chunk_pages(
    pages: list[PageText],
    document_id: str,
    filename: str,
    created_at: str,
    config: ChunkingConfig | None = None,
) -> list[Chunk]:
    """Chunk per-page extracted text into :class:`Chunk` objects.

    Each chunk is confined to a single page (accurate page attribution). Chunks are numbered
    sequentially across the whole document (``chunk_index``), and ``id`` is
    ``f"{document_id}:{chunk_index}"``. ``char_start``/``char_end`` are offsets within the chunk's
    page text. Empty/whitespace-only pages produce no chunks.
    """
    cfg = config or ChunkingConfig()
    chunks: list[Chunk] = []
    index = 0
    for page in pages:
        page_text = page.text.strip()
        if not page_text:
            continue
        blocks = _pack_paragraphs(_split_paragraphs(page_text), cfg.target_size_tokens)
        blocks = _apply_overlap(blocks, cfg.overlap_tokens)
        for block in blocks:
            # char_start/char_end are offsets within the page text (documented limitation: per-page,
            # not global, because chunks never cross page boundaries).
            start = page_text.find(block)
            end = start + len(block) if start >= 0 else len(block)
            chunks.append(
                Chunk(
                    id=f"{document_id}:{index}",
                    document_id=document_id,
                    filename=filename,
                    page=page.page,
                    chunk_index=index,
                    text=block,
                    char_start=max(start, 0),
                    char_end=max(end, 0),
                    created_at=created_at,
                )
            )
            index += 1
    logger.info("Chunked document %s into %d chunk(s)", document_id, len(chunks))
    return chunks


def chunk_text(
    text: str,
    document_id: str,
    filename: str,
    created_at: str,
    config: ChunkingConfig | None = None,
    page: int = 1,
) -> list[Chunk]:
    """Chunk a single block of text (treated as one page) into :class:`Chunk` objects.

    Convenience for callers that have a single text string rather than per-page text (e.g. tests).
    All chunks are attributed to ``page``.
    """
    return chunk_pages(
        [PageText(page=page, text=text)],
        document_id=document_id,
        filename=filename,
        created_at=created_at,
        config=config,
    )
