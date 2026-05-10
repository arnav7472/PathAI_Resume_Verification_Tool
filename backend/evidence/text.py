from __future__ import annotations

import re


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def phrase_pattern(phrase: str) -> re.Pattern[str]:
    escaped = re.escape(phrase).replace(r"\ ", r"[\s\-/]+")
    return re.compile(rf"(?<![a-z0-9+#]){escaped}(?![a-z0-9+#])", re.IGNORECASE)


def contains_phrase(text: str, phrase: str) -> bool:
    return bool(phrase_pattern(phrase).search(text))


def truncate_snippet(text: str, max_len: int = 240) -> str:
    t = normalize_whitespace(text)
    if len(t) <= max_len:
        return t
    return t[: max_len - 1].rstrip() + "…"


def snippet_signature(text: str) -> str:
    return normalize_whitespace(text).lower()


def split_sentences(text: str) -> list[str]:
    compact = re.sub(r"\s+", " ", text or "").strip()
    if not compact:
        return []
    pieces = re.split(r"(?<=[.!?])\s+|(?:\s*[•*]\s*)|\n+", compact)
    return [piece.strip(" -–—\t") for piece in pieces if len(piece.strip()) > 2]
