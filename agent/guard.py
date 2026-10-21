"""The guard: checks every tool call BEFORE it runs (policy P-02).

Three checks, in order:
  1. Allow list   : the tool must exist in agent/tools.py (there is no approve tool, P-01)
  2. Contract     : the arguments must match the tool's parameter model exactly
  3. Prerequisites: the case must be in a state where this action is permitted
                    (e.g. R-12: no submission before the fee is paid)

The guard does not use the language model. Whatever the model was told or tricked into,
a call that fails these checks is blocked and logged.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from pydantic import BaseModel, ValidationError

from .executor import AgentContext
from .models import Outcome, RuleStatus


@dataclass
class GuardDecision:
    allowed: bool
    policy: str
    reason: str = ""
    args: Optional[BaseModel] = None


READ_ONLY = {"get_service_requirements", "list_uploaded_documents", "get_case_status"}


def _block(policy: str, reason: str) -> GuardDecision:
    return GuardDecision(False, policy, reason)


def _rules_fresh_and(ctx: AgentContext, outcome: Outcome) -> bool:
    r = ctx.state.rule_report
    return r is not None and not ctx.state.rules_stale and r.outcome == outcome


def check(ctx: AgentContext, name: str, raw_args: Any) -> GuardDecision:
    from .tools import TOOLS
    s = ctx.state

    # 1. allow list
    if name not in TOOLS:
        return _block("P-01", f"'{name}' is not an authorised tool. Approvals are made only by the "
                              f"rules engine or a human reviewer.")

    # 2. contract
    if raw_args in (None, ""):
        raw_args = {}
    if not isinstance(raw_args, dict):
        return _block("P-02", "arguments must be a JSON object")
    try:
        args = TOOLS[name].args_model.model_validate(raw_args)
    except ValidationError as e:
        return _block("P-02", f"arguments do not match the contract: {e.errors()[0]['msg']}")

    # 3. prerequisites
    if name in READ_ONLY:
        return GuardDecision(True, "P-02", args=args)
    if s.is_closed():
        return _block("P-02", f"case is already {s.status.value}; no further actions are permitted")

    if name == "get_applicant_profile":
        pass
    elif name == "verify_documents":
        if not s.uploads:
            return _block("P-02", "no documents uploaded yet; ask the customer to upload them")
        unknown = set(args.doc_ids or []) - s.upload_ids()
        if unknown:
            # Found live (S2-AR): the model guessed an ID ("uae_visa"); tell it the real ones so it can recover
            return _block("P-02", f"doc_ids not uploaded in this session: {sorted(unknown)}. Uploaded doc_ids are "
                                  f"{sorted(s.upload_ids())}; call verify_documents with no doc_ids to verify every "
                                  f"document not yet verified.")
    elif name == "evaluate_rules":
        if s.profile is None:
            return _block("P-02", "load the applicant profile first (get_applicant_profile)")
        if s.unverified_ids():
            return _block("P-02", f"verify these documents first: {s.unverified_ids()}")
        if s.failed_verifications:
            return _block("P-03", "verification failed for some documents; escalate with "
                                  "reason_code=system_unavailable instead of evaluating")
    elif name == "request_payment":
        if s.receipt is not None:
            return _block("P-02", "fee already paid")
        if s.payment_request is not None:
            return _block("P-02", "the payment window is already open; ask the customer to complete the payment there")
        if not (_rules_fresh_and(ctx, Outcome.ELIGIBLE) or _rules_fresh_and(ctx, Outcome.HUMAN_REVIEW)):
            return _block("R-12", "payment is only requested after the rules return ELIGIBLE (or HUMAN_REVIEW, "
                                  "D-06: paid before the officer reviews) on the latest documents")
    elif name == "submit_application":
        if not _rules_fresh_and(ctx, Outcome.ELIGIBLE):
            return _block("P-01", "submission requires a current ELIGIBLE rules outcome")
        if s.receipt is None:
            return _block("R-12", "the AED 50 fee must be paid before submission")
    elif name == "escalate_to_human":
        problem = _escalation_grounds_missing(ctx, args.reason_code)
        if problem:
            return _block("P-09", problem + " Do not escalate; continue with the suggested next step.")
    return GuardDecision(True, "P-02", args=args)


def _escalation_grounds_missing(ctx: AgentContext, reason: str) -> str:
    """P-09: an escalation must trace to a customer input or a rule result, like every other action."""
    s = ctx.state
    fresh = s.rule_report is not None and not s.rules_stale
    review = {r.rule_id for r in s.rule_report.by_status(RuleStatus.REVIEW)} if fresh else set()
    if reason == "customer_request":
        # P-09: a request for a person is answered with the toll-free number by code; it never creates a case
        return ("reason 'customer_request' is not used: give the Ministry toll-free number instead "
                "(cases reach an officer only for rules or system failures).")
    elif reason == "name_mismatch":
        if "R-14" not in review:
            return "reason 'name_mismatch' is not supported: rule R-14 did not return REVIEW."
    elif reason == "verification_inconclusive":
        if "R-15" not in review:
            return "reason 'verification_inconclusive' is not supported: rule R-15 did not return REVIEW."
    elif reason == "system_unavailable":
        if not (s.failed_verifications or "get_applicant_profile" in s.failed_systems):
            return "reason 'system_unavailable' is not supported: no backend call has failed."
        if not s.uploads:
            # found live: a fee question during an identity outage created a case for an officer with nothing in it
            return ("nothing is attached yet, so there is no request for an officer: tell the parent a Ministry "
                    "system is unavailable and to try again later.")
    elif reason == "other":
        if not (fresh and s.rule_report.outcome == Outcome.HUMAN_REVIEW):
            return "reason 'other' needs a current HUMAN_REVIEW rules outcome."
    if reason != "system_unavailable" and s.receipt is None:
        # D-06 (decided 21 October): a request the rules send to an officer is submitted like any other, so the
        # AED 50 fee is paid first. Only a system failure reaches an officer unpaid (nothing could be checked).
        return "the AED 50 fee must be paid before the request goes to an officer (D-06): call request_payment first."
    return ""
