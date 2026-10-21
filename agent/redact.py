"""Masking of sensitive data before it reaches logs, the model, or replies (policy P-08).

Two layers:
  1. Pattern masking: document numbers (mock and real formats), emails, phone numbers.
  2. Known values: names and numbers we know belong to this case are replaced.
"""
import re
from typing import Any, Iterable

# Mock identifiers used by the synthetic data, plus real-world formats as a safety net.
_PATTERNS = [
    # MOCK-P-IND-4801371, MOCK-EID-0001-01, MOCK-V-201-2025-0000001 -> keep prefix and last 2 chars
    (re.compile(r"\bMOCK-(P|EID|V)-([A-Z0-9-]+)\b"),
     lambda m: f"MOCK-{m.group(1)}-****{m.group(2)[-2:]}"),
    # Real Emirates ID format 784-YYYY-NNNNNNN-N (never present in our data, masked anyway)
    (re.compile(r"\b784-?\d{4}-?\d{7}-?\d\b"), lambda m: "[EMIRATES-ID]"),
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b"), lambda m: "[EMAIL]"),
    (re.compile(r"(?<!\d)(?:\+?971|00971|0)[\s-]?5\d[\s-]?\d{3}[\s-]?\d{4}(?!\d)"), lambda m: "[PHONE]"),
]


def mask_number(number: str | None) -> str | None:
    if not number:
        return number
    return redact_text(number)


def redact_text(text: str, known_terms: Iterable[str] = ()) -> str:
    if not isinstance(text, str) or not text:
        return text
    out = text
    for pattern, repl in _PATTERNS:
        out = pattern.sub(repl, out)
    for term in sorted({t for t in known_terms if t and len(t) >= 3}, key=len, reverse=True):
        out = re.sub(re.escape(term), "[NAME]", out, flags=re.IGNORECASE)
    return out


def redact_obj(obj: Any, known_terms: Iterable[str] = ()) -> Any:
    """Recursively redact every string inside dicts / lists."""
    terms = list(known_terms)
    if isinstance(obj, str):
        return redact_text(obj, terms)
    if isinstance(obj, dict):
        return {k: redact_obj(v, terms) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [redact_obj(v, terms) for v in obj]
    return obj


def contains_sensitive(text: str, sensitive_values: Iterable[str]) -> list[str]:
    """Used by tests: which of the given raw values appear in the text."""
    return [v for v in sensitive_values if v and v.lower() in (text or "").lower()]
