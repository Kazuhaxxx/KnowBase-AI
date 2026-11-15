import re
from typing import Tuple

_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(your\s+)?(system|safety|security)\s+prompt", re.IGNORECASE),
    re.compile(r"reveal\s+(the\s+)?(system\s+prompt|api\s*key|secret|password)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(in\s+)?(developer|admin|unrestricted)\s+mode", re.IGNORECASE),
    re.compile(r"<\s*/?\s*system\s*>", re.IGNORECASE),
]


def clean_text(text: str) -> str:
    """Normalize extracted text while keeping troubleshooting structure and code blocks intact."""
    if not text:
        return ""
    # Remove null bytes and non-printable control characters except tab/newline
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Normalize Windows/Mac line endings
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse excessive horizontal whitespace on each line
    lines = [re.sub(r"[ \t]+", " ", line).rstrip() for line in cleaned.split("\n")]
    # Collapse >2 consecutive blank lines
    normalized = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))
    return normalized.strip()


def inspect_prompt_injection(text: str) -> Tuple[bool, list[str]]:
    """Detect suspicious prompt-injection directives embedded inside uploaded documents."""
    matched: list[str] = []
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            matched.append(pattern.pattern)
    return (len(matched) > 0, matched)

