from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_SPLIT_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def normalize_text(text: object) -> str:
    return str(text or "").lower()


def tokenize(text: object) -> list[str]:
    """Deterministic tokenizer for tool names, descriptions, and schema fields."""
    raw = str(text or "")
    expanded = _SPLIT_BOUNDARY_RE.sub(" ", raw).replace("_", " ").replace("-", " ")
    return [match.group(0).lower() for match in _TOKEN_RE.finditer(expanded)]


def tokens_with_exact_identifier(identifier: object) -> list[str]:
    raw = str(identifier or "").strip().lower()
    parts = tokenize(raw)
    if raw and raw not in parts:
        return [raw, *parts]
    return parts
