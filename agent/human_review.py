"""Human approval path (the "Approve" box in the case study).

This is called ONLY from the Staff review screen. It is NOT a tool the model can call
(see agent/tools.py), so no prompt, document or customer message can reach it.

Approval workflow (decision D-02, docs/02_rules_and_assumptions.md):
* The agent never issues an equivalency decision. Its last possible action is to SUBMIT a complete, paid request
  (every rule passed) or to ESCALATE one the rules cannot decide.
* An officer decides both kinds: a submitted case is a ready-to-decide case (all automated checks passed), an
  escalated case needs the officer to resolve what the rules flagged (P-01). Both decisions are logged here.
"""
from __future__ import annotations

import re
from pathlib import Path

from .audit import AuditLog
from .config import LOG_DIR
from .mocks import CaseStore
from .models import CaseRecord, CaseStatus
from .redact import redact_text

STAFF_ID = re.compile(r"^STAFF-[A-Z0-9]{2,10}$")


class ReviewError(Exception):
    """A decision that cannot be recorded. `code` lets the screen say it in the officer's language."""

    def __init__(self, message: str, code: str = "other"):
        super().__init__(message)
        self.code = code


def decide(store: CaseStore, case_ref: str, reviewer_id: str, decision: str, note: str,
           log_dir: Path = LOG_DIR) -> CaseRecord:
    if not STAFF_ID.match(reviewer_id or ""):
        raise ReviewError("reviewer ID must look like STAFF-XXXX (synthetic staff accounts only)", "staff_id")
    if decision not in ("approve", "reject"):
        raise ReviewError("decision must be 'approve' or 'reject'")
    if not (note or "").strip():
        raise ReviewError("a note explaining the decision is required", "note")
    rec = store.get(case_ref)
    if rec is None:
        raise ReviewError(f"case {case_ref} not found")
    if rec.status not in (CaseStatus.PENDING_HUMAN_REVIEW, CaseStatus.SUBMITTED):
        raise ReviewError(f"case {case_ref} is {rec.status.value}: already decided, nothing to decide", "decided")
    basis = ("P-01 human decision on an escalated case" if rec.status == CaseStatus.PENDING_HUMAN_REVIEW
             else "P-16 official equivalency decision by an officer (all automated checks passed)")
    new_status = CaseStatus.HUMAN_APPROVED if decision == "approve" else CaseStatus.HUMAN_REJECTED
    updated = store.update(case_ref, status=new_status, reviewer_id=reviewer_id,
                           reviewer_note=redact_text(note.strip()))
    AuditLog(rec.session_id, log_dir).log("human", "human_decision", basis=basis,
                                          case_ref=case_ref, reviewer_id=reviewer_id, previous=rec.status.value,
                                          decision=decision, note=note.strip())
    return updated
