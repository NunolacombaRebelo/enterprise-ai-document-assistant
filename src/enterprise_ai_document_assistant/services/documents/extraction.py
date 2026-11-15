"""PDF text extraction for document management (Milestone 1).

Wraps ``pypdf`` behind a small, explicit interface so the rest of the code does not depend on the
library directly. Extraction failures are surfaced as typed exceptions so the service layer can
decide whether a document is stored as ``error`` or rejected outright.

Extraction never executes uploaded content; it only parses the PDF structure.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass

from pypdf import PdfReader
from pypdf.errors import PdfReadError

logger = logging.getLogger(__name__)


class ExtractionError(Exception):
    """Base class for PDF extraction failures."""


class EncryptedPdfError(ExtractionError):
    """Raised when the PDF is encrypted and cannot be read without a password."""


class MalformedPdfError(ExtractionError):
    """Raised when the PDF structure is corrupt or unreadable."""


@dataclass(frozen=True)
class ExtractedDocument:
    """Result of a successful extraction."""

    page_count: int
    text: str


@dataclass(frozen=True)
class PageText:
    """Text for a single page (1-based ``page``).

    Used by the retrieval chunker to preserve accurate page attribution. ``text`` may be empty for
    pages with no extractable text (e.g. scanned/image-only pages).
    """

    page: int
    text: str


def extract_pdf(data: bytes) -> ExtractedDocument:
    """Extract text and page count from PDF bytes.

    Raises :class:`EncryptedPdfError` for encrypted PDFs and :class:`MalformedPdfError` for corrupt
    or unreadable PDFs. A PDF with zero extractable text (e.g. a scanned image-only document) is
    returned successfully with empty text; the caller decides how to classify it.
    """
    reader = _open_reader(data)
    page_count = len(reader.pages)
    parts: list[str] = []
    for page in reader.pages:
        parts.append(_extract_page_text(page))
    text = "\n".join(parts).strip()
    logger.info("Extracted %d page(s), %d character(s) of text", page_count, len(text))
    return ExtractedDocument(page_count=page_count, text=text)


def extract_pdf_pages(data: bytes) -> list[PageText]:
    """Extract text per page from PDF bytes (1-based page numbers).

    Returns one :class:`PageText` per page, preserving page boundaries so downstream chunking can
    attribute chunks to the correct page. Raises the same :class:`ExtractionError` subtypes as
    :func:`extract_pdf`.
    """
    reader = _open_reader(data)
    pages: list[PageText] = []
    for index, page in enumerate(reader.pages, start=1):
        pages.append(PageText(page=index, text=_extract_page_text(page)))
    logger.info("Extracted %d page(s) of per-page text", len(pages))
    return pages


def _open_reader(data: bytes) -> PdfReader:
    """Open a PDF reader, raising typed errors for malformed/encrypted input."""
    try:
        reader = PdfReader(io.BytesIO(data))
    except PdfReadError as exc:
        logger.warning("Malformed PDF rejected during parse: %s", exc)
        raise MalformedPdfError("The PDF is malformed or unreadable.") from exc

    if reader.is_encrypted:
        # Attempt an empty-password decrypt; if it fails, the PDF is password-protected.
        try:
            if not reader.decrypt(""):
                raise EncryptedPdfError("The PDF is encrypted and cannot be processed.")
        except Exception as exc:
            logger.warning("Encrypted PDF rejected: %s", exc)
            raise EncryptedPdfError("The PDF is encrypted and cannot be processed.") from exc
    return reader


def _extract_page_text(page) -> str:
    """Extract text from a single page, returning an empty string on per-page failure."""
    try:
        return page.extract_text() or ""
    except Exception as exc:
        logger.warning("Page extraction failed: %s", exc)
        return ""
