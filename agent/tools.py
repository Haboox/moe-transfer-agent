"""The ONLY actions the agent can take (policy P-01).

Each tool has:
  * a name and description the model sees
  * a parameter contract (JSON schema for the model + Pydantic model the guard validates)
  * a handler that talks to the MOCK systems through call_backend (retry policy)

Deliberately missing: any tool that approves, rejects or changes a rule. Only the rules
engine (ELIGIBLE) plus a paid fee can submit, and only a human (staff screen) can decide
an escalated case. That function is in agent/human_review.py and is NOT in this list.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Literal, Optional, Type

from pydantic import BaseModel, ConfigDict, Field

from . import rules
from .config import (MOE_SUPPORT_NUMBER, SERVICE_CARD_URL, SERVICE_FEE_AED, SERVICE_NAME)
from .executor import AgentContext, ToolFailure, call_backend
from .facts import instructions_in_document
from .models import (ApplicantProfile, CaseRecord, CaseStatus, Outcome, PaymentReceipt, PaymentRequest,
                     RuleStatus, VerificationResult)
from .redact import mask_number, redact_text
from .service_card import CARD


# ------------------------------------------------------------------ argument contracts
class NoArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


class VerifyArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    doc_ids: Optional[list[str]] = None


ReasonCode = Literal["name_mismatch", "verification_inconclusive", "system_unavailable",
                     "customer_request", "other"]


class EscalateArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason_code: ReasonCode
    summary: str = Field(default="", max_length=600)


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict
    args_model: Type[BaseModel]
    handler: Callable[[AgentContext, BaseModel], dict]
    basis: str = ""          # where this action comes from: service card section and/or rule IDs


# KEY REQUIREMENT: every agent action must trace to a customer input, the service card or a rule.
TOOL_BASIS = {
    "get_service_requirements": "Card: Required documents, Fees, Service Conditions",
    "get_applicant_profile": "Card: Service Process step 1 (UAE Pass)",
    "list_uploaded_documents": "Card: Service Process step 2 (upload documents)",
    "verify_documents": "Card: Service Conditions (attestation); R-02 to R-09, R-15",
    "evaluate_rules": "Rules R-01 to R-15 (agent/rules.py)",
    "request_payment": "Card: Fees; Service Process step 3; R-12",
    "submit_application": "Card: Service Process steps 2 to 4; requires ELIGIBLE + R-12",
    "escalate_to_human": "Approve: a person decides what the rules cannot (P-09 grounds)",
    "get_case_status": "Card: Service Process step 4 (decision)",
}


EMPTY = {"type": "object", "properties": {}, "required": []}


# ------------------------------------------------------------------ handlers
def _requirements(ctx: AgentContext, _: NoArgs) -> dict:
    """The card text itself (agent/service_card.py). The customer always receives it word for word (P-10)."""
    c = CARD["en"]
    return {
        "service": SERVICE_NAME,
        "source": SERVICE_CARD_URL,
        "covers": c["covers"] + " Grade 12 uses a different service.",
        "required_documents": c["documents"],
        "conditions": c["conditions"],
        "notes": c["notes"],
        "fee_aed": SERVICE_FEE_AED,
        "service_time": "30 working days (published service card). A complete request is checked and submitted at "
                        "once; a Ministry officer issues the equivalency decision within the 30 working days",
        "support": f"MoE toll-free {MOE_SUPPORT_NUMBER}",
        "note": "The official list is attached to your reply automatically, in the customer's language.",
    }


def _profile(ctx: AgentContext, _: NoArgs) -> dict:
    s = ctx.state
    prof: ApplicantProfile = call_backend(
        ctx, "identity", "get_applicant_profile",
        lambda: ctx.backend.identity_get_profile(s.persona_id), ApplicantProfile,
        basis="Card: Service Process step 1 (UAE Pass login)")
    s.profile = prof
    st = prof.student
    ctx.audit.add_known_terms(st.given_name, st.family_name, f"{st.given_name} {st.family_name}",
                              st.given_name_ar, st.family_name_ar,
                              f"{st.given_name_ar} {st.family_name_ar}" if st.given_name_ar else "")
    gcc = rules.is_gcc(st.nationality)
    ctx.add_trace("get_applicant_profile() -> found", "mock tool (identity, UAE Pass)")
    return {"status": "ok", "student_ref": st.student_ref,
            "nationality": st.nationality, "gcc_national": gcc,
            "uae_visa_required": not gcc}


def _list_uploads(ctx: AgentContext, _: NoArgs) -> dict:
    s = ctx.state
    return {"status": "ok", "documents": [
        {"doc_id": u.doc_id, "type": u.doc_type, "file": u.file_name, "format": u.file_format,
         "size_mb": u.size_mb,
         "verification": (s.verifications[u.doc_id].authenticity if u.doc_id in s.verifications else
                          "failed" if u.doc_id in s.failed_verifications else "not yet verified")}
        for u in s.uploads]}


def _summarise_verification(v: VerificationResult, known_names: Iterable[str] = ()) -> dict:
    out: dict[str, Any] = {"doc_id": v.doc_id, "type": v.doc_type, "authenticity": v.authenticity}
    if v.number:
        out["number"] = mask_number(v.number)
    if v.expiry:
        out["expiry"] = v.expiry.isoformat()
    if v.doc_type == "school_certificate":
        out.update(grade=v.grade, grade_label=v.grade_label, academic_year=v.academic_year,
                   language=v.language, complete_year=v.complete_year, school=v.school_name,
                   attestations=v.attestations.model_dump() if v.attestations else None,
                   attested_by=v.attested_by)
        # Untrusted content (policy P-05): passed as data, clearly labelled, never as instructions.
        # The student's names are masked here as in the log, so the model never gets the child's name (P-14).
        out["document_text_UNTRUSTED_DATA"] = redact_text(v.extracted_text[:400], known_names)
    if v.translates_doc_id:
        out["translates_doc_id"] = v.translates_doc_id
    return out


def _verify(ctx: AgentContext, args: VerifyArgs) -> dict:
    s = ctx.state
    targets = args.doc_ids or s.unverified_ids()
    results = []
    for doc_id in targets:
        try:
            v: VerificationResult = call_backend(
                ctx, "verification", "verify_document",
                lambda d=doc_id: ctx.backend.verification_verify(s.persona_id, d),
                VerificationResult, basis="Card: Service Conditions (attestation)")
            s.verifications[doc_id] = v
            s.failed_verifications.pop(doc_id, None)
            results.append(_summarise_verification(v, ctx.audit.known_terms))
            ctx.add_trace(f"verify_document({doc_id}) -> {v.authenticity}", "mock tool (document verification)")
            if instructions_in_document(v.extracted_text):
                # P-05, shown and logged: text addressed to the AI inside a document is data, never an instruction
                ctx.stats["doc_instructions"] += 1
                ctx.audit.log("policy", "document_instructions_ignored", basis="P-05: document text is data",
                              doc_id=doc_id)
                ctx.add_trace(f"Instructions to the AI inside {doc_id}", "deterministic check: treated as data, "
                              "ignored (P-05)", "block", lane="validate")
        except ToolFailure as f:
            s.failed_verifications[doc_id] = f.outcome
            results.append({"doc_id": doc_id, "status": "failed", "error": f.outcome})
    s.rules_stale = True
    failed = [r for r in results if r.get("status") == "failed"]
    out: dict[str, Any] = {"status": "partial_failure" if failed else "ok", "results": results}
    if failed:
        out["advice"] = ("Verification system unavailable after a retry. Do not guess. "
                         "An officer checks the documents instead: the fee is paid first (request_payment), "
                         "then escalate with reason_code=system_unavailable.")
    return out


def _evaluate(ctx: AgentContext, _: NoArgs) -> dict:
    s = ctx.state
    inp = rules.VerifiedInputs(nationality=s.profile.student.nationality, uploads=s.uploads,
                               verifications=s.verifications,
                               application_date=ctx.settings.application_date)
    report = rules.evaluate(inp)
    s.rule_report, s.rules_stale = report, False
    if report.outcome == Outcome.NEEDS_INFO:
        s.status = CaseStatus.AWAITING_CUSTOMER
    elif report.outcome == Outcome.WRONG_SERVICE:
        s.status = CaseStatus.REDIRECTED
    else:
        s.status = CaseStatus.IN_PROGRESS
    ctx.audit.log("rules", "rules_evaluated", basis="agent/rules.py",
                  outcome=report.outcome.value,
                  results={r.rule_id: r.status.value for r in report.results})
    span = f" {report.results[0].rule_id} to {report.results[-1].rule_id}" if report.results else ""
    ctx.add_trace(f"Rules{span} -> {report.outcome.value}",
                  "rule engine, no AI: " + (", ".join(f"{r.rule_id} {r.status.value}" for r in report.results
                                                      if r.status not in (RuleStatus.PASS, RuleStatus.NOT_APPLICABLE))
                                            or "all passed"),
                  "rule", lane="validate")
    return {"status": "ok", "outcome": report.outcome.value,
            "problems": [{"rule": r.rule_id, "status": r.status.value, "detail": r.detail}
                         for r in report.results
                         if r.status not in (RuleStatus.PASS, RuleStatus.NOT_APPLICABLE)],
            "passed": [r.rule_id for r in report.results if r.status == RuleStatus.PASS]}


def _pay(ctx: AgentContext, _: NoArgs) -> dict:
    s = ctx.state
    if ctx.backend.interactive_payments:
        # The customer pays in the payment window (card or wallet, simulated). Card details never reach
        # the agent, the model or the log: the app sends them straight to the MOCK gateway.
        req: PaymentRequest = call_backend(
            ctx, "payment", "open_payment_window",
            lambda: ctx.backend.payment_open(s.session_id, SERVICE_FEE_AED), PaymentRequest,
            basis="Card: Fees; Service Process step 3")
        s.payment_request, s.status = req, CaseStatus.AWAITING_PAYMENT
        ctx.add_trace("request_payment() -> payment window opened", f"mock tool, AED {req.amount_aed}, SIMULATED", "ok")
        return {"status": "awaiting_customer_payment", "payment_id": req.payment_id, "amount_aed": req.amount_aed,
                "note": "The customer pays in the payment window. Tell them to complete the payment there."}
    receipt: PaymentReceipt = call_backend(
        ctx, "payment", "request_payment",
        lambda: ctx.backend.payment_charge(s.session_id, SERVICE_FEE_AED), PaymentReceipt,
        basis="Card: Fees; Service Process step 3; A-10")
    s.receipt = receipt
    ctx.add_trace(f"request_payment() -> {receipt.status}", f"mock tool, AED {receipt.amount_aed}, SIMULATED")
    return {"status": "ok", "receipt_id": receipt.receipt_id, "amount_aed": receipt.amount_aed,
            "note": "Payment received."}


def _rule_summary(s) -> dict:
    return {r.rule_id: r.status.value for r in (s.rule_report.results if s.rule_report else [])}


def _case_facts(s) -> dict:
    """What the officer reads first, written by code from the case record (never by the model)."""
    results = s.rule_report.results if s.rule_report else []
    problems = [{"rule_id": r.rule_id, "status": r.status.value, "title": r.title, "title_ar": r.title_ar,
                 "detail": r.detail, "detail_ar": r.detail_ar}
                for r in results if r.status.value in ("FAIL", "MISSING", "REVIEW")]
    docs = [{"doc_id": u.doc_id, "doc_type": u.doc_type, "grade": s.verifications[u.doc_id].grade if u.doc_id in s.verifications else None,
             "verified": u.doc_id in s.verifications and s.verifications[u.doc_id].authenticity == "verified"} for u in s.uploads]
    grades = [d["grade"] for d in docs if d["grade"] is not None]
    return {"problems": problems, "documents": docs, "grade": max(grades) if grades else None,
            "nationality": s.profile.student.nationality if s.profile else None}


def _submit(ctx: AgentContext, _: NoArgs) -> dict:
    s = ctx.state
    rec: CaseRecord = call_backend(
        ctx, "cases", "submit_application",
        lambda: ctx.backend.cases_create(session_id=s.session_id, student_ref=s.profile.student.student_ref,
                                         status=CaseStatus.SUBMITTED,
                                         rule_outcome=Outcome.ELIGIBLE.value,
                                         receipt_id=s.receipt.receipt_id, language=s.lang,
                                         rule_summary=_rule_summary(s), **_case_facts(s)),
        CaseRecord, basis="Rules ELIGIBLE + R-12 fee paid")
    s.case_ref, s.status = rec.case_ref, CaseStatus.SUBMITTED
    ctx.add_trace(f"submit_application() -> {rec.case_ref}", "authorised action, logged", "ok")
    return {"status": "ok", "case_ref": rec.case_ref, "case_status": rec.status.value}


def _escalate(ctx: AgentContext, args: EscalateArgs) -> dict:
    s = ctx.state
    st = s.profile.student if s.profile else None
    summary = redact_text(args.summary, [st.given_name, st.family_name, st.given_name_ar, st.family_name_ar]
                          if st else [])
    rec: CaseRecord = call_backend(
        ctx, "cases", "escalate_to_human",
        lambda: ctx.backend.cases_create(
            session_id=s.session_id,
            student_ref=s.profile.student.student_ref if s.profile else "UNKNOWN",
            status=CaseStatus.PENDING_HUMAN_REVIEW,
            rule_outcome=s.rule_report.outcome.value if s.rule_report else None,
            escalation_reason=args.reason_code, escalation_summary=summary, language=s.lang,
            receipt_id=s.receipt.receipt_id if s.receipt else None,
            rule_summary=_rule_summary(s), **_case_facts(s)),
        CaseRecord, basis=f"escalation: {args.reason_code}")
    s.case_ref, s.status, s.escalation_reason = rec.case_ref, CaseStatus.PENDING_HUMAN_REVIEW, args.reason_code
    ctx.add_trace(f"escalate_to_human() -> {rec.case_ref}", f"a person decides; reason: {args.reason_code}",
                  "escalate", lane="approve")
    return {"status": "ok", "case_ref": rec.case_ref, "case_status": rec.status.value,
            "note": "A staff member will review and decide. The agent cannot decide this case."}


def _case_status(ctx: AgentContext, _: NoArgs) -> dict:
    s = ctx.state
    if s.case_ref:
        rec = ctx.backend.cases.get(s.case_ref)
        if rec:
            s.status = rec.status
            return {"status": "ok", "case_ref": rec.case_ref, "case_status": rec.status.value,
                    "reviewer_note": rec.reviewer_note}
    return {"status": "ok", "case_ref": None, "case_status": s.status.value}


# ------------------------------------------------------------------ registry
_TOOL_LIST = [
    ToolSpec("get_service_requirements",
             "Returns the official requirements of this service from the MoE service card. "
             "Use it to answer questions about documents, fees or conditions.",
             EMPTY, NoArgs, _requirements),
    ToolSpec("get_applicant_profile",
             "Loads the logged-in applicant and student from the identity system (UAE Pass). "
             "Needed before rules can be evaluated.", EMPTY, NoArgs, _profile),
    ToolSpec("list_uploaded_documents",
             "Lists documents the customer has uploaded in this session and whether each is verified.",
             EMPTY, NoArgs, _list_uploads),
    ToolSpec("verify_documents",
             "Sends uploaded documents to the document verification service (attestations, validity, "
             "authenticity). With no doc_ids it verifies every document not yet verified.",
             {"type": "object", "properties": {"doc_ids": {"type": "array", "items": {"type": "string"},
                                                           "description": "Optional list of doc_ids"}},
              "required": []}, VerifyArgs, _verify),
    ToolSpec("evaluate_rules",
             "Runs the official business rules on the verified documents. Returns the outcome: "
             "ELIGIBLE, NEEDS_INFO, HUMAN_REVIEW or WRONG_SERVICE. Only this decides eligibility.",
             EMPTY, NoArgs, _evaluate),
    ToolSpec("request_payment",
             f"Requests the service fee (AED {SERVICE_FEE_AED}). Only allowed when rules are ELIGIBLE, or HUMAN_REVIEW "
             "(the request is paid for before an officer reviews it). "
             "In the app it opens a payment window where the customer pays.",
             EMPTY, NoArgs, _pay),
    ToolSpec("submit_application",
             "Creates the case in the case management system. Only allowed when rules are ELIGIBLE "
             "and the fee is paid.", EMPTY, NoArgs, _submit),
    ToolSpec("escalate_to_human",
             "Sends the case to a staff member when the rules return HUMAN_REVIEW (after the fee is paid) "
             "or a system is unavailable. Never for a customer who asks for a person (give the phone number).",
             {"type": "object",
              "properties": {"reason_code": {"type": "string",
                                             "enum": ["name_mismatch", "verification_inconclusive",
                                                      "system_unavailable", "customer_request", "other"]},
                             "summary": {"type": "string",
                                         "description": "One or two sentences for the reviewer"}},
              "required": ["reason_code"]}, EscalateArgs, _escalate),
    ToolSpec("get_case_status", "Returns the current status of this customer's case.",
             EMPTY, NoArgs, _case_status),
]
TOOLS: dict[str, ToolSpec] = {t.name: t for t in _TOOL_LIST}
for _t in _TOOL_LIST:
    _t.basis = TOOL_BASIS[_t.name]
