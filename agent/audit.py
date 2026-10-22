"""Audit trail (policy P-08).

Every action is written as one JSON line to logs/audit_<session_id>.jsonl.
Each event records WHO acted (actor), WHAT happened (event), and WHY (basis):
the customer input, rule ID, or policy ID that triggered it.
All values are masked by agent/redact.py before they are written.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import LOG_DIR
from .redact import redact_obj

ACTORS = {"customer", "model", "guard", "tool", "rules", "policy", "human", "system"}


class AuditLog:
    def __init__(self, session_id: str, log_dir: Path = LOG_DIR):
        self.session_id = session_id
        self.path = Path(log_dir) / f"audit_{session_id}.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.events: list[dict] = []
        self._known_terms: set[str] = set()
        # continue numbering if this session's log already exists (e.g. a staff decision later)
        self._seq = sum(1 for _ in self.path.open(encoding="utf-8")) if self.path.exists() else 0

    def add_known_terms(self, *terms: str) -> None:
        """Names and other values that must never appear in the log."""
        self._known_terms.update(t for t in terms if t)

    @property
    def known_terms(self) -> set[str]:
        """The same names, for masking what the model is given (P-14)."""
        return set(self._known_terms)

    def log(self, actor: str, event: str, basis: str = "", **detail: Any) -> dict:
        if actor not in ACTORS:                      # a real check (an assert disappears with python -O)
            raise ValueError(f"unknown actor {actor}")
        self._seq += 1
        record = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "session_id": self.session_id,
            "seq": self._seq,
            "actor": actor,
            "event": event,
            "basis": basis,
            "detail": redact_obj(detail, self._known_terms),
        }
        self.events.append(record)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        return record

    def read_all_text(self) -> str:
        return self.path.read_text(encoding="utf-8") if self.path.exists() else ""
