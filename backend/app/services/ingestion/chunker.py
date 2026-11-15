from dataclasses import dataclass
import re
from typing import Any, Optional

from app.services.ingestion.cleaner import clean_text, inspect_prompt_injection
from app.services.ingestion.extractors import ExtractedSegment


@dataclass
class ChunkPayload:
    chunk_index: int
    content: str
    cleaned_content: str
    page_number: Optional[int]
    section_heading: Optional[str]
    token_count: int
    char_count: int
    metadata_json: dict[str, Any]


def chunk_segments(
    segments: list[ExtractedSegment],
    chunk_size: int = 650,
    chunk_overlap: int = 120,
    base_metadata: Optional[dict[str, Any]] = None,
) -> list[ChunkPayload]:
    """
    Structure-aware chunker that preserves page numbers, section headings,
    and avoids splitting numbered troubleshooting steps unnecessarily.
    """
    if chunk_size < 100:
        raise ValueError("chunk_size must be at least 100 characters.")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size.")

    base_meta = dict(base_metadata or {})
    chunks: list[ChunkPayload] = []
    chunk_counter = 0

    for segment in segments:
        cleaned = clean_text(segment.text)
        if not cleaned:
            continue

        blocks = _split_preserving_blocks(cleaned)
        current_parts: list[str] = []
        current_len = 0

        for block in blocks:
            block_len = len(block)

            # If a single block exceeds chunk_size, sub-split gracefully by sentences/lines
            if block_len > chunk_size:
                if current_parts:
                    chunks.append(
                        _make_chunk(
                            chunk_counter,
                            "\n\n".join(current_parts),
                            segment.page_number,
                            segment.section_heading,
                            base_meta,
                        )
                    )
                    chunk_counter += 1
                    current_parts = []
                    current_len = 0

                for piece in _split_long_block(block, chunk_size, chunk_overlap):
                    chunks.append(
                        _make_chunk(
                            chunk_counter,
                            piece,
                            segment.page_number,
                            segment.section_heading,
                            base_meta,
                        )
                    )
                    chunk_counter += 1
                continue

            projected = current_len + (2 if current_parts else 0) + block_len
            if projected > chunk_size and current_parts:
                assembled = "\n\n".join(current_parts)
                chunks.append(
                    _make_chunk(
                        chunk_counter,
                        assembled,
                        segment.page_number,
                        segment.section_heading,
                        base_meta,
                    )
                )
                chunk_counter += 1

                # Build overlap tail from trailing text
                overlap_text = assembled[-chunk_overlap:].strip() if chunk_overlap > 0 else ""
                # Snap overlap to a clean word boundary
                if overlap_text and " " in overlap_text:
                    overlap_text = overlap_text.split(" ", 1)[1]
                current_parts = [overlap_text] if overlap_text else []
                current_len = len(overlap_text)

            current_parts.append(block)
            current_len += (2 if len(current_parts) > 1 else 0) + block_len

        if current_parts:
            chunks.append(
                _make_chunk(
                    chunk_counter,
                    "\n\n".join(current_parts),
                    segment.page_number,
                    segment.section_heading,
                    base_meta,
                )
            )
            chunk_counter += 1

    return chunks


def _split_preserving_blocks(text: str) -> list[str]:
    """
    Split text into semantic paragraphs while keeping numbered lists or code blocks
    grouped when they are reasonably sized.
    """
    raw_blocks = re.split(r"\n{2,}", text)
    merged: list[str] = []
    for block in raw_blocks:
        stripped = block.strip()
        if not stripped:
            continue
        # Keep short numbered step consecutive lines together if separated by blank lines
        if (
            merged
            and re.match(r"^\d+[\.\)]\s+", stripped)
            and re.search(r"(^|\n)\d+[\.\)]\s+", merged[-1])
            and len(merged[-1]) + len(stripped) < 420
        ):
            merged[-1] = f"{merged[-1]}\n{stripped}"
        else:
            merged.append(stripped)
    return merged


def _split_long_block(block: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+|\n", block)
    pieces: list[str] = []
    current = ""

    for sentence in sentences:
        s = sentence.strip()
        if not s:
            continue
        if len(s) > chunk_size:
            if current:
                pieces.append(current)
                current = ""
            # Hard window split as last resort
            step = max(1, chunk_size - chunk_overlap)
            for start in range(0, len(s), step):
                pieces.append(s[start : start + chunk_size])
            continue

        candidate = f"{current} {s}".strip() if current else s
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                pieces.append(current)
            tail = current[-chunk_overlap:].strip() if (current and chunk_overlap > 0) else ""
            if tail and " " in tail:
                tail = tail.split(" ", 1)[1]
            current = f"{tail} {s}".strip() if tail else s

    if current:
        pieces.append(current)
    return pieces


def _make_chunk(
    chunk_index: int,
    content: str,
    page_number: Optional[int],
    section_heading: Optional[str],
    base_meta: dict[str, Any],
) -> ChunkPayload:
    cleaned = clean_text(content)
    has_injection_signal, matched = inspect_prompt_injection(cleaned)
    meta = {
        **base_meta,
        "page_number": page_number,
        "section_heading": section_heading,
        "chunk_index": chunk_index,
        "untrusted_instruction_flagged": has_injection_signal,
    }
    if matched:
        meta["flagged_pattern_count"] = len(matched)

    token_estimate = max(1, len(cleaned.split()))
    return ChunkPayload(
        chunk_index=chunk_index,
        content=content,
        cleaned_content=cleaned,
        page_number=page_number,
        section_heading=section_heading,
        token_count=token_estimate,
        char_count=len(cleaned),
        metadata_json=meta,
    )

