from dataclasses import dataclass
from pathlib import Path
import re
from typing import Optional

import docx
import pymupdf as fitz


@dataclass
class ExtractedSegment:
    """Extracted text segment preserving page number and section heading when available."""

    text: str
    page_number: Optional[int] = None
    section_heading: Optional[str] = None


@dataclass
class ExtractionResult:
    """Full document extraction output."""

    segments: list[ExtractedSegment]
    page_count: Optional[int]
    full_text_preview: str


class DocumentExtractionError(ValueError):
    """Raised when a file cannot be safely validated or extracted."""


def validate_upload_bytes(
    filename: str,
    content: bytes,
    allowed_extensions: set[str],
    max_size_bytes: int,
) -> str:
    """Validate file extension, non-empty size, max size, and basic format signature."""
    ext = Path(filename).suffix.lower()
    if ext not in allowed_extensions:
        raise DocumentExtractionError(
            f"Unsupported file extension '{ext}'. Allowed: {sorted(allowed_extensions)}"
        )
    if not content:
        raise DocumentExtractionError("Uploaded file is empty.")
    if len(content) > max_size_bytes:
        max_mb = max_size_bytes // (1024 * 1024)
        raise DocumentExtractionError(f"File exceeds maximum allowed size of {max_mb} MB.")

    # Basic magic byte verification for binary containers
    if ext == ".pdf" and not content.lstrip().startswith(b"%PDF"):
        raise DocumentExtractionError("Invalid PDF signature.")
    if ext == ".docx" and not content.startswith(b"PK"):
        raise DocumentExtractionError("Invalid DOCX archive signature.")

    return ext


def extract_document(file_path: Path, extension: str) -> ExtractionResult:
    """Extract text segments with metadata from PDF, DOCX, TXT, or MD files."""
    ext = extension.lower()
    if ext == ".pdf":
        return _extract_pdf(file_path)
    if ext == ".docx":
        return _extract_docx(file_path)
    if ext in {".txt", ".md"}:
        return _extract_text_or_markdown(file_path, is_markdown=(ext == ".md"))
    raise DocumentExtractionError(f"Unsupported extension '{ext}'.")


def _extract_pdf(file_path: Path) -> ExtractionResult:
    segments: list[ExtractedSegment] = []
    try:
        with fitz.open(file_path) as pdf_doc:
            page_count = len(pdf_doc)
            for idx, page in enumerate(pdf_doc, start=1):
                text = page.get_text("text") or ""
                if text.strip():
                    segments.append(
                        ExtractedSegment(
                            text=text,
                            page_number=idx,
                            section_heading=_infer_first_heading(text),
                        )
                    )
    except Exception as exc:
        raise DocumentExtractionError(f"Failed to extract PDF content: {exc}") from exc

    if not segments:
        raise DocumentExtractionError("No extractable text found in PDF.")

    preview = "\n\n".join(s.text for s in segments[:2])[:1500]
    return ExtractionResult(segments=segments, page_count=page_count, full_text_preview=preview)


def _extract_docx(file_path: Path) -> ExtractionResult:
    segments: list[ExtractedSegment] = []
    try:
        document = docx.Document(str(file_path))
        current_heading: Optional[str] = None
        buffer: list[str] = []

        for para in document.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            style_name = (para.style.name or "").lower() if para.style else ""
            if "heading" in style_name:
                if buffer:
                    segments.append(
                        ExtractedSegment(
                            text="\n".join(buffer),
                            page_number=None,
                            section_heading=current_heading,
                        )
                    )
                    buffer = []
                current_heading = text[:200]
                buffer.append(text)
            else:
                buffer.append(text)

        # Include tables so troubleshooting matrices are captured
        for table in document.tables:
            rows = []
            for row in table.rows:
                cells = [c.text.strip().replace("\n", " ") for c in row.cells]
                if any(cells):
                    rows.append(" | ".join(cells))
            if rows:
                buffer.append("\n".join(rows))

        if buffer:
            segments.append(
                ExtractedSegment(
                    text="\n".join(buffer),
                    page_number=None,
                    section_heading=current_heading,
                )
            )
    except Exception as exc:
        raise DocumentExtractionError(f"Failed to extract DOCX content: {exc}") from exc

    if not segments:
        raise DocumentExtractionError("No extractable text found in DOCX.")

    preview = "\n\n".join(s.text for s in segments)[:1500]
    return ExtractionResult(segments=segments, page_count=None, full_text_preview=preview)


def _extract_text_or_markdown(file_path: Path, is_markdown: bool) -> ExtractionResult:
    try:
        raw = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        raise DocumentExtractionError(f"Failed to read text file: {exc}") from exc

    if not raw.strip():
        raise DocumentExtractionError("Text file contains no readable content.")

    if not is_markdown:
        return ExtractionResult(
            segments=[ExtractedSegment(text=raw, page_number=None, section_heading=None)],
            page_count=None,
            full_text_preview=raw[:1500],
        )

    # Split Markdown by top-level/second-level headings while preserving heading text
    segments: list[ExtractedSegment] = []
    current_heading: Optional[str] = None
    buffer: list[str] = []

    for line in raw.splitlines():
        heading_match = re.match(r"^(#{1,3})\s+(.+)$", line.strip())
        if heading_match:
            if buffer:
                segments.append(
                    ExtractedSegment(
                        text="\n".join(buffer),
                        page_number=None,
                        section_heading=current_heading,
                    )
                )
                buffer = []
            current_heading = heading_match.group(2).strip()[:200]
            buffer.append(line)
        else:
            buffer.append(line)

    if buffer:
        segments.append(
            ExtractedSegment(
                text="\n".join(buffer),
                page_number=None,
                section_heading=current_heading,
            )
        )

    return ExtractionResult(
        segments=segments,
        page_count=None,
        full_text_preview=raw[:1500],
    )


def _infer_first_heading(text: str) -> Optional[str]:
    for line in text.splitlines():
        stripped = line.strip()
        if 4 <= len(stripped) <= 120 and not stripped.endswith("."):
            return stripped
    return None
