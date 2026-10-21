"""Data shapes used across the project (Pydantic models).

Pydantic checks that data has the right fields and types. We use it for:
  * tool contracts: what each mock system returns (a malformed response fails validation)
  * the case state the agent carries between turns
"""
from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------- statuses
class CaseStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"                    # collecting / checking
    AWAITING_CUSTOMER = "AWAITING_CUSTOMER"        # rules said something is missing
    AWAITING_PAYMENT = "AWAITING_PAYMENT"          # rules ELIGIBLE, the customer is paying in the payment window
    REDIRECTED = "REDIRECTED"                      # wrong service (R-01 / P-06)
    SUBMITTED = "SUBMITTED"                        # rules ELIGIBLE + fee paid + case created
    PENDING_HUMAN_REVIEW = "PENDING_HUMAN_REVIEW"  # escalated
    HUMAN_APPROVED = "HUMAN_APPROVED"              # decided by a person
    HUMAN_REJECTED = "HUMAN_REJECTED"              # decided by a person


class RuleStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    MISSING = "MISSING"
    REVIEW = "REVIEW"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class Outcome(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    NEEDS_INFO = "NEEDS_INFO"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    WRONG_SERVICE = "WRONG_SERVICE"


# ---------------------------------------------------------------- identity (mock UAE Pass)
class StudentProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    student_ref: str
    given_name: str
    family_name: str
    nationality: str
    given_name_ar: Optional[str] = None
    family_name_ar: Optional[str] = None
    nationality_ar: Optional[str] = None


class ApplicantProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    uae_pass_ref: str
    applicant_display_name: str
    student: StudentProfile


# ---------------------------------------------------------------- documents
class UploadedDocument(BaseModel):
    """What the customer uploaded (metadata only, as a portal would see it)."""
    model_config = ConfigDict(extra="forbid")
    doc_id: str
    doc_type: str
    file_name: str
    file_format: str
    size_mb: float


class Attestations(BaseModel):
    model_config = ConfigDict(extra="forbid")
    education_authority: bool
    mofa: bool
    uae_embassy: bool


class VerificationResult(BaseModel):
    """Contract of the mock Document Verification Service. Anything else = malformed."""
    model_config = ConfigDict(extra="forbid")
    doc_id: str
    doc_type: str
    authenticity: str = Field(pattern="^(verified|inconclusive)$")
    holder_name: Optional[str] = None
    holder_name_ar: Optional[str] = None     # Arabic edition documents carry the name in Arabic
    number: Optional[str] = None           # sensitive: masked before it leaves the tool layer
    expiry: Optional[date] = None
    grade: Optional[int] = None
    academic_year: Optional[str] = None
    language: Optional[str] = None
    complete_year: Optional[bool] = None
    country_of_study: Optional[str] = None
    grade_label: Optional[str] = None        # local name, e.g. "Second Preparatory Year (Grade 8)"
    school_name: Optional[str] = None
    issued: Optional[str] = None
    attestations: Optional[Attestations] = None
    attested_by: list[str] = []              # authority names on the stamps (explainability)
    translates_doc_id: Optional[str] = None
    translation_language: Optional[str] = None   # a legal translation counts only into English or Arabic (R-06)
    extracted_text: str = ""               # UNTRUSTED content of the document


class PaymentReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")
    receipt_id: str
    amount_aed: int
    status: str = Field(pattern="^PAID$")
    simulated: bool = True
    method: str = "card"                      # card, apple_pay, google_pay, samsung_pay (all simulated)
    card_last4: Optional[str] = None          # the only card detail ever kept


class PaymentRequest(BaseModel):
    """Contract of the MOCK payment gateway when it opens a payment window (hosted payment page)."""
    model_config = ConfigDict(extra="forbid")
    payment_id: str
    amount_aed: int
    status: str = Field(pattern="^PENDING$")
    simulated: bool = True


class CaseRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_ref: str
    session_id: str
    student_ref: str
    status: CaseStatus
    rule_outcome: Optional[str] = None
    escalation_reason: Optional[str] = None
    escalation_summary: Optional[str] = None
    receipt_id: Optional[str] = None
    reviewer_id: Optional[str] = None
    reviewer_note: Optional[str] = None
    language: str = "en"                      # language the customer used (for the staff screen)
    rule_summary: dict[str, str] = {}         # rule ID -> status when the case was created (evidence for staff)
    created_at: Optional[str] = None
    # what the officer needs to read the case at a glance (written by code from the record, not by the model)
    problems: list[dict] = []                 # rules not passed: rule_id, status, title(_ar), detail(_ar)
    documents: list[dict] = []                # documents checked: doc_type, grade, verified
    grade: Optional[int] = None               # highest verified grade
    nationality: Optional[str] = None


# ---------------------------------------------------------------- rules
class RuleResult(BaseModel):
    rule_id: str
    title: str
    status: RuleStatus
    detail: str
    source: str
    title_ar: str = ""                        # the same result in Arabic, written by the rules engine
    detail_ar: str = ""


class RuleReport(BaseModel):
    outcome: Outcome
    results: list[RuleResult]

    def by_status(self, *statuses: RuleStatus) -> list[RuleResult]:
        return [r for r in self.results if r.status in statuses]


# ---------------------------------------------------------------- case state
class CaseState(BaseModel):
    """Everything the agent knows about one customer session."""
    session_id: str
    persona_id: str
    status: CaseStatus = CaseStatus.IN_PROGRESS
    profile: Optional[ApplicantProfile] = None
    uploads: list[UploadedDocument] = []
    verifications: dict[str, VerificationResult] = {}
    failed_verifications: dict[str, str] = {}   # doc_id -> error after retries
    rule_report: Optional[RuleReport] = None
    rules_stale: bool = True                    # True when uploads changed since last evaluation
    receipt: Optional[PaymentReceipt] = None
    payment_request: Optional[PaymentRequest] = None   # open payment window (interactive payment)
    case_ref: Optional[str] = None
    escalation_reason: Optional[str] = None
    conversation: list[dict] = []               # chat history in a provider-neutral format
    last_intent: Optional[dict] = None
    turn: int = 0
    lang: str = "en"                            # language of the customer's latest message (replies use it)
    ui_lang: str = "en"                         # language of the portal page (used when a message has no words)
    scope_grade: Optional[int] = None           # grade outside 2 to 11 the customer stated (P-06 redirect message)
    failed_systems: list[str] = Field(default_factory=list)   # tools whose system failed after the retry
    last_topics: list[str] = Field(default_factory=list)   # card sections answered last turn (no repeated card text)
    stated_country: Optional[str] = None        # a country the parent named (wording only; never a rule input)
    stated_grade: Optional[int] = None          # grade inside 2 to 11 the customer stated (guidance only, never a rule input)

    def upload_ids(self) -> set[str]:
        return {u.doc_id for u in self.uploads}

    def unverified_ids(self) -> list[str]:
        return [u.doc_id for u in self.uploads
                if u.doc_id not in self.verifications and u.doc_id not in self.failed_verifications]

    def is_closed(self) -> bool:
        return self.status in {CaseStatus.SUBMITTED, CaseStatus.PENDING_HUMAN_REVIEW,
                               CaseStatus.HUMAN_APPROVED, CaseStatus.HUMAN_REJECTED}
