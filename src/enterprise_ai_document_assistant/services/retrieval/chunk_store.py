"""Chunk persistence (Milestone 2).

Persists the indexed chunks as the single source of truth for the retrieval index. The BM25 index is
rebuilt from these chunks on startup (it is not separately persisted), and the Chroma collection is
a derived representation of the same chunks (for future vector search).

Storage layout under ``chunks_dir`` (default ``.data/chunks``, git-ignored):
- ``<document_id>.json`` — the list of chunks for one document (JSON array of chunk dicts).

This keeps runtime data out of version control and makes reindexing/rebuild deterministic.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from enterprise_ai_document_assistant.services.retrieval.models import Chunk

logger = logging.getLogger(__name__)


class ChunkStore:
    """Filesystem-backed store for indexed chunks, keyed by document id."""

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    @property
    def root(self) -> Path:
        return self._root

    def _path(self, document_id: str) -> Path:
        return self._root / f"{document_id}.json"

    def save_document(self, document_id: str, chunks: list[Chunk]) -> None:
        """Persist (replace) the chunks for a document. Empty list removes the document."""
        path = self._path(document_id)
        if not chunks:
            if path.exists():
                path.unlink()
            return
        payload = [self._chunk_to_dict(c) for c in chunks]
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Persisted %d chunk(s) for document %s", len(chunks), document_id)

    def get_document(self, document_id: str) -> list[Chunk]:
        """Return the chunks for a document, or ``[]`` if none are stored."""
        path = self._path(document_id)
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("Skipping unreadable chunk file %s: %s", path.name, exc)
            return []
        return [self._dict_to_chunk(item) for item in data]

    def all_documents(self) -> dict[str, list[Chunk]]:
        """Return all stored chunks as ``{document_id: [Chunk, ...]}``."""
        result: dict[str, list[Chunk]] = {}
        for path in self._root.glob("*.json"):
            document_id = path.stem
            chunks = self.get_document(document_id)
            if chunks:
                result[document_id] = chunks
        return result

    def all_chunks(self) -> list[Chunk]:
        """Return every stored chunk across all documents (deterministic order by id)."""
        chunks: list[Chunk] = []
        for document_chunks in self.all_documents().values():
            chunks.extend(document_chunks)
        chunks.sort(key=lambda c: c.id)
        return chunks

    def delete_document(self, document_id: str) -> None:
        """Remove a document's stored chunks (best-effort)."""
        path = self._path(document_id)
        if path.exists():
            path.unlink()
            logger.info("Deleted stored chunks for document %s", document_id)

    @staticmethod
    def _chunk_to_dict(chunk: Chunk) -> dict:
        return {
            "id": chunk.id,
            "document_id": chunk.document_id,
            "filename": chunk.filename,
            "page": chunk.page,
            "chunk_index": chunk.chunk_index,
            "text": chunk.text,
            "char_start": chunk.char_start,
            "char_end": chunk.char_end,
            "created_at": chunk.created_at,
            # Embeddings are not persisted in the chunk store in Milestone 2 (lexical-only). They
            # live in Chroma when present (Milestone 3+).
            "embedding": chunk.embedding,
        }

    @staticmethod
    def _dict_to_chunk(item: dict) -> Chunk:
        return Chunk(
            id=item["id"],
            document_id=item["document_id"],
            filename=item["filename"],
            page=int(item["page"]),
            chunk_index=int(item["chunk_index"]),
            text=item["text"],
            char_start=int(item["char_start"]),
            char_end=int(item["char_end"]),
            created_at=item["created_at"],
            embedding=item.get("embedding"),
        )
