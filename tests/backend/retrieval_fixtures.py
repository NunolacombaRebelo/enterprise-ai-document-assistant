"""Deterministic retrieval evaluation fixtures (Milestone 2).

A small, stable corpus of synthetic documents with known relevant passages, used to evaluate
retrieval quality (Recall@K, MRR) and to exercise chunking/indexing/retrieval deterministically.
No network, no models. Kept separate from test implementation details so it can be reused.
"""

from __future__ import annotations

from dataclasses import dataclass

from enterprise_ai_document_assistant.services.documents.extraction import PageText


@dataclass(frozen=True)
class EvalDocument:
    """A synthetic document with per-page text and a set of expected-relevant chunk keywords."""

    document_id: str
    filename: str
    pages: tuple[PageText, ...]


def _pages(*texts: str) -> tuple[PageText, ...]:
    return tuple(PageText(page=i + 1, text=t) for i, t in enumerate(texts))


#: A small, deterministic corpus. Each document has distinct topic keywords so BM25 can rank
#: relevant passages above irrelevant ones.
EVAL_CORPUS: list[EvalDocument] = [
    EvalDocument(
        document_id="doc-refund",
        filename="refund-policy.pdf",
        pages=_pages(
            "Our refund policy allows customers to return items within thirty days of purchase. "
            "Refunds are issued to the original payment method after inspection.",
            "To start a refund, contact support with your order number. International returns "
            "may incur additional shipping costs.",
        ),
    ),
    EvalDocument(
        document_id="doc-shipping",
        filename="shipping-guide.pdf",
        pages=_pages(
            "Standard shipping takes five to seven business days. Express shipping is available "
            "for an additional fee and arrives within two business days.",
            "Free shipping is offered on orders over fifty dollars. Tracking numbers are emailed "
            "once the package is dispatched.",
        ),
    ),
    EvalDocument(
        document_id="doc-password",
        filename="account-faq.pdf",
        pages=_pages(
            "To reset your password, use the link on the login page. The reset link expires after "
            "one hour for security reasons.",
            "If you are locked out, contact support to verify your identity and restore access to "
            "your account.",
        ),
    ),
]


#: Query -> expected relevant document id(s), for Recall@K / MRR evaluation.
EVAL_QUERIES: dict[str, list[str]] = {
    "refund return policy": ["doc-refund"],
    "express shipping delivery": ["doc-shipping"],
    "reset password login": ["doc-password"],
}


def corpus_chunks() -> list:
    """Chunk the whole eval corpus into :class:`Chunk` objects (deterministic)."""
    from enterprise_ai_document_assistant.services.retrieval.chunking import chunk_pages

    chunks = []
    for doc in EVAL_CORPUS:
        chunks.extend(
            chunk_pages(
                list(doc.pages),
                document_id=doc.document_id,
                filename=doc.filename,
                created_at="2026-11-15T00:00:00+00:00",
            )
        )
    return chunks
