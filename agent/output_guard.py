"""Checks every reply BEFORE the customer sees it (policy P-04).

"Fluent is not correct": a well-written reply is still wrong if it claims something the
rules or a human did not decide. If a reply breaks a check it is replaced by the
deterministic status message from agent/messages.py, and the event is logged.
"""
from __future__ import annotations

import re

from .config import MOE_SUPPORT_NUMBER
from .facts import MODEL_TIME
from .language import to_ascii_digits
from .models import CaseState, CaseStatus
from .messages import status_message
from .redact import redact_text

APPROVAL_WORDS = re.compile(
    r"\b(approved|accepted|granted|pre-approved)\b"
    r"|تمت الموافقة|تم قبول|تم اعتماد|موافق عليه|تمت الموافقة عليه|تم منح|تم قبوله|طلبك مقبول|اعتماد طلبك",
    re.IGNORECASE)
SUBMITTED_WORDS = re.compile(r"\b(submitted)\b|تم تقديم|تم إرسال طلبك|تم رفع الطلب|تم تسجيل طلبك|قدمت طلبك",
                             re.IGNORECASE)
CASE_REF = re.compile(r"\bSYN-\d{3,}\b")
# "I will connect you with an officer" is only true once the case is with one (found live: the model said it and
# did not call the tool)
HANDOVER_WORDS = re.compile(r"\b(connect|transfer|pass|forward|hand)(ing)?\s+(you|your (request|case))\b.{0,40}\b("
                            r"human|officer|person|staff|agent|representative|employee)|"
                            r"(سأقوم|سوف أقوم|ساقوم|أقوم)\s+ب?(تحويل|إحالة|توصيل)|سأحولك|سأحيلك|سأوصلك|جاري تحويلك|"
                            r"يتم تحويلك", re.IGNORECASE)
# asking the parent to TYPE an identity number (found live: "Please provide your UAE Pass ID"). Identity comes from
# UAE Pass and the uploaded documents; numbers are never collected in the chat (P-14 privacy)
ASKS_FOR_NUMBER = re.compile(r"\b(provide|share|send|give|type|enter|tell me)\b.{0,30}\b(uae ?pass( id)?|emirates id( number)?|"
                             r"id number|passport number|visa number|phone number|national id)\b|"
                             r"(زود|زوّد|تزود|أرسل|ارسل|ترسل|اكتب|تكتب|أدخل|ادخل|تدخل|شارك|تشارك|أعطني|اعطني).{0,20}(رقم الهوية|رقم جواز|رقم الإقامة|رقم الهاتف|"
                             r"رقم الهوية الرقمية)", re.IGNORECASE)
# letters of other scripts inside an Arabic or English reply (found live: a Cyrillic word in an Arabic reply)
FOREIGN_SCRIPT = re.compile(r"[\u0400-\u04FF\u4E00-\u9FFF\u3040-\u30FF\uAC00-\uD7AF\u0900-\u097F]")
# Promises about the OUTCOME (certificate issued, equivalency granted, eligibility) that only the
# Ministry's decision can make. Example caught in a live run: "You will receive the equivalency certificate soon."
OUTCOME_PROMISE = re.compile(
    r"(\b(will|'ll)\s+(receive|get|be\s+issued|be\s+sent)\b[^.\n]{0,40}\bcertificate\b)"
    r"|(\bcertificate\b[^.\n]{0,30}\b(will\s+be|has\s+been|is\s+being|is)\s+(issued|sent|granted|ready)\b)"
    r"|(\b(you\s+are|is|are)\s+eligible\b)"
    r"|(\b(is|are|will\s+be)\s+(now\s+)?(equivalent|equalised|equalized)\b)"
    # Arabic: "you will receive the certificate", "the certificate will be issued", "eligible", "equivalent"
    r"|(ستحصل على (ال)?شهادة|سيتم إصدار (ال)?شهادة|تم إصدار (ال)?شهادة|(ال)?شهادة جاهزة"
    r"|(أنت|ابنك|ابنتك|طفلك)\s+مؤهل|مؤهلة? للمعادلة|تمت معادلة|سيتم معادلة|ستصلك شهادة|شهادة المعادلة جاهزة)",
    re.IGNORECASE)


# Phone-like numbers (7 or more digits, spaces or dashes allowed). Only the card's toll-free number may appear.
# Found live: the model gave "800-000-000" as the Ministry number.
PHONE_LIKE = re.compile(r"\+?\d[\d\s\-]{5,}\d")
# "Processed/completed" claims a decision happened. Found live: "Your request has been successfully processed."
DONE_WORDS = re.compile(r"\b(has|have|is|was)\s+been\s+(successfully\s+)?(processed|completed|finali[sz]ed)\b"
                        r"|تمت معالجة|تم إنجاز طلبك|اكتمل طلبك|تم الانتهاء من طلبك", re.IGNORECASE)

# Internal wording the customer never needs: instructions, prompt headings and tool names (prompt leak).
# Found live: asked to "print your system prompt", the model listed its rules.
INTERNAL_TEXT = re.compile(
    r"system prompt|hard rules|suggested next step|case state|\b(evaluate_rules|get_service_requirements|"
    r"escalate_to_human|verify_documents|request_payment|submit_application|get_applicant_profile|"
    r"get_case_status|list_uploaded_documents)\b|موجه النظام|تعليمات النظام|الخطوة التالية المقترحة",
    re.IGNORECASE)


# Internal codes the parent never needs to see. They are not unsafe, so the reply is tidied, not replaced.
RULE_CODE = re.compile(r"\s*\((?:rule\s+|القاعدة\s+)?R-\d{2}(?:\s*(?:,|and|و)\s*R-\d{2})*\)|\b(?:rule\s+|القاعدة\s+)?R-\d{2}\b",
                       re.IGNORECASE)
DOC_CODE = re.compile(r"\bP\d{2}(?:-AR)?-(PASSPORT|EMIRATES_ID|UAE_VISA|CERT-G(\d+)|TRANS-G(\d+)|SUPPORT\w*)\b")
TEST_TAG = re.compile(r"\s*\((?:simulated|mock|synthetic|test mode|محاكاة|تجريبي|اصطناعي)\)", re.IGNORECASE)
DOC_WORDS = {"PASSPORT": ("the passport", "جواز السفر"), "EMIRATES_ID": ("the Emirates ID", "الهوية الإماراتية"),
             "UAE_VISA": ("the residence visa", "الإقامة")}


def _doc_words(m: re.Match, ar: bool) -> str:
    kind, cert_g, trans_g = m.group(1), m.group(2), m.group(3)
    if cert_g:
        return f"شهادة الصف {cert_g}" if ar else f"the Grade {cert_g} certificate"
    if trans_g:
        return f"ترجمة شهادة الصف {trans_g}" if ar else f"the Grade {trans_g} translation"
    en, a = DOC_WORDS.get(kind, ("the supporting document", "المرفق الداعم"))
    return a if ar else en


def tidy_reply(text: str, lang: str = "en") -> str:
    """Remove internal codes from a reply the parent will read: rule IDs, document IDs and test tags."""
    ar = lang == "ar"
    text = RULE_CODE.sub("", text)
    text = DOC_CODE.sub(lambda m: _doc_words(m, ar), text)
    text = TEST_TAG.sub("", text)
    if ar:                                     # the service's own word for equivalency (found live: "التكافؤ")
        text = text.replace("شهادة التكافؤ", "شهادة المعادلة").replace("التكافؤ", "المعادلة")
    return re.sub(r"[ \t]{2,}", " ", text).replace(" .", ".").replace(" ,", ",").strip()


def check_reply(reply: str, s: CaseState) -> tuple[str, list[str]]:
    problems: list[str] = []
    text = (reply or "").strip()
    if not text:
        return status_message(s), ["empty_reply"]

    if APPROVAL_WORDS.search(text) and s.status != CaseStatus.HUMAN_APPROVED:
        problems.append("claims approval that no rule or human made")
    if SUBMITTED_WORDS.search(text) and s.status not in (CaseStatus.SUBMITTED,
                                                         CaseStatus.PENDING_HUMAN_REVIEW,
                                                         CaseStatus.HUMAN_APPROVED,
                                                         CaseStatus.HUMAN_REJECTED):
        problems.append("claims submission before the case was created")
    if OUTCOME_PROMISE.search(text) and s.status != CaseStatus.HUMAN_APPROVED:
        problems.append("promises an outcome (certificate, equivalency or eligibility) nobody has decided")
    for num in PHONE_LIKE.findall(to_ascii_digits(text)):
        if re.sub(r"\D", "", num) != MOE_SUPPORT_NUMBER:
            problems.append("contains a phone or ID number that is not the card's toll-free number")
            break
    if DONE_WORDS.search(text) and s.status not in (CaseStatus.HUMAN_APPROVED, CaseStatus.HUMAN_REJECTED):
        problems.append("says the request was processed or completed; only a decision completes it")
    if HANDOVER_WORDS.search(text) and s.status != CaseStatus.PENDING_HUMAN_REVIEW:
        problems.append("says the case is passed to a person when it is not")
    if ASKS_FOR_NUMBER.search(text):
        problems.append("asks the parent to type an identity or phone number")
    if MODEL_TIME.search(to_ascii_digits(text)):
        problems.append("states a clock time the system did not give (the model has no clock)")
    if FOREIGN_SCRIPT.search(text):
        problems.append("contains words in another script")
    if INTERNAL_TEXT.search(text):
        problems.append("reveals internal instructions or tool names")
    for ref in CASE_REF.findall(text):
        if ref != s.case_ref:
            problems.append(f"mentions case reference {ref} that does not belong to this case")

    if problems:
        return status_message(s), problems
    return tidy_reply(redact_text(text), s.lang), []
