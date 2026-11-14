"""Helpers for building synthetic PDFs in tests.

These helpers produce minimal, valid PDF byte strings without any external PDF generator, so tests
run offline and deterministically. They are test-only and live in the Agent 2-owned test directory.
"""

from __future__ import annotations


def _build(objects: list[str], root_id: int, size: int, extra_trailer: str = "") -> bytes:
    """Assemble a PDF from object bodies with a correct xref table."""
    header = b"%PDF-1.4\n"
    parts = [o.encode("latin-1", "replace") for o in objects]
    body = b"".join(parts)

    offsets: dict[int, int] = {}
    search_from = 0
    for o in objects:
        objnum = int(o.split(" ", 1)[0])
        idx = body.find(o.encode("latin-1", "replace"), search_from)
        offsets[objnum] = len(header) + idx
        search_from = idx + len(o)

    xref_lines = [f"xref\n0 {size}\n", "0000000000 65535 f \n"]
    for i in range(1, size):
        if i in offsets:
            xref_lines.append(f"{offsets[i]:010d} 00000 n \n")
        else:
            xref_lines.append("0000000000 65535 f \n")
    xref_bytes = "".join(xref_lines).encode("latin-1")
    xref_offset = len(header) + len(body)
    trailer = (
        f"trailer\n<< /Size {size} /Root {root_id} 0 R {extra_trailer} >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode("latin-1")
    return header + body + xref_bytes + trailer


def make_pdf_bytes(page_count: int = 1) -> bytes:
    """Return bytes for a minimal valid PDF with ``page_count`` text pages.

    Layout: 1=catalog, 2=pages tree, 3=font, then for each page a page object and a content
    object. This is a standard structure that ``pypdf`` parses and extracts text from.
    """
    n = max(1, page_count)
    objects: list[str] = []
    objects.append("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    objects.append("3 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")

    page_ids = [4 + 2 * i for i in range(n)]
    content_ids = [5 + 2 * i for i in range(n)]
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects.append(f"2 0 obj\n<< /Type /Pages /Kids [{kids}] /Count {n} >>\nendobj\n")

    for i in range(n):
        pid = page_ids[i]
        cid = content_ids[i]
        text = f"Page {i + 1} synthetic content"
        stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("latin-1", "replace")
        objects.append(
            f"{pid} 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {cid} 0 R >>\nendobj\n"
        )
        objects.append(
            f"{cid} 0 obj\n<< /Length {len(stream)} >>\nstream\n"
            f"{stream.decode('latin-1')}\nendstream\nendobj\n"
        )

    size = 3 + 2 * n + 1
    return _build(objects, root_id=1, size=size)


def make_empty_pdf_bytes() -> bytes:
    """Return an empty byte string (to simulate an empty upload)."""
    return b""


def make_non_pdf_bytes() -> bytes:
    """Return bytes that are not a PDF (missing the %PDF header)."""
    return b"this is not a pdf file at all"


def make_encrypted_pdf_bytes() -> bytes:
    """Return bytes for a password-protected (encrypted) PDF.

    The trailer declares an ``/Encrypt`` dictionary whose owner/user hashes do not match an empty
    password, so ``pypdf`` reports the PDF as encrypted and empty-password decryption fails. This
    is a synthetic, deterministic fixture (no real secret).
    """
    objects: list[str] = []
    objects.append("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    objects.append("2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    objects.append(
        "3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n"
    )
    stream = b"BT /F1 12 Tf 72 720 Td (secret) Tj ET"
    objects.append(
        f"4 0 obj\n<< /Length {len(stream)} >>\nstream\n"
        f"{stream.decode('latin-1')}\nendstream\nendobj\n"
    )
    objects.append(
        "5 0 obj\n<< /Filter /Standard /V 1 /R 2 /Length 40 "
        "/O <00000000000000000000000000000000> "
        "/U <11111111111111111111111111111111> "
        "/P -3904 >>\nendobj\n"
    )
    return _build(objects, root_id=1, size=6, extra_trailer="/Encrypt 5 0 R")
