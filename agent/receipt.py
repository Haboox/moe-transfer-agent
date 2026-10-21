"""Application receipt (PDF) the parent can download once a case exists: proof of what was submitted.

It is NOT an equivalency certificate and says so. It states only facts from the case record: reference, date,
documents checked, the rules result, the fee receipt and what happens next. Labelled SYNTHETIC like every
document in the prototype. Built in English or Arabic (the page language).
"""
from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from .facts import now_uae
from .config import MOE_SUPPORT_NUMBER, ROOT, SERVICE_FEE_AED, SERVICE_NAME
from .models import CaseState, CaseStatus

FONTS = ROOT / "assets" / "fonts"
_registered = False

STATUS = {
    CaseStatus.SUBMITTED: ("Submitted: all service requirements met, fee paid",
                           "تم التقديم: جميع متطلبات الخدمة مستوفاة والرسوم مدفوعة"),
    CaseStatus.PENDING_HUMAN_REVIEW: ("Under review by a Ministry officer", "قيد المراجعة لدى موظف الوزارة"),
    CaseStatus.HUMAN_APPROVED: ("Approved by a Ministry officer", "وافق عليه موظف الوزارة"),
    CaseStatus.HUMAN_REJECTED: ("Not approved by a Ministry officer", "لم يوافق عليه موظف الوزارة"),
}
NEXT = {
    CaseStatus.SUBMITTED: ("A Ministry officer will issue the equivalency decision within 30 working days; it will be "
                           "sent to the email registered in UAE Pass.",
                           "سيُصدر موظف الوزارة قرار المعادلة خلال 30 يوم عمل، وسيُرسل إلى البريد الإلكتروني المسجل في "
                           "الهوية الرقمية."),
    CaseStatus.PENDING_HUMAN_REVIEW: ("A Ministry officer will review the case within 30 working days.",
                                      "سيراجع موظف الوزارة الطلب خلال 30 يوم عمل."),
    CaseStatus.HUMAN_APPROVED: ("The decision is recorded on the case.", "القرار مسجل في الطلب."),
    CaseStatus.HUMAN_REJECTED: ("The decision is recorded on the case.", "القرار مسجل في الطلب."),
}
DOC = {"passport": ("Passport", "جواز السفر"), "emirates_id": ("Emirates ID", "الهوية الإماراتية"),
       "uae_visa": ("Residence visa", "الإقامة"), "legal_translation": ("Legal translation", "ترجمة قانونية"),
       "supporting_document": ("Supporting document", "مرفق داعم")}


def _fonts() -> None:
    global _registered
    if not _registered:
        pdfmetrics.registerFont(TTFont("RcSans", str(FONTS / "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("RcSans-Bold", str(FONTS / "DejaVuSans-Bold.ttf")))
        _registered = True


def _ar(text: str) -> str:
    import arabic_reshaper
    from bidi.algorithm import get_display
    return get_display(arabic_reshaper.reshape(text))


def build_receipt(s: CaseState, lang: str, student_name: str) -> bytes:
    if not s.case_ref or s.status not in STATUS:
        raise ValueError("a receipt exists only once a case has been created")
    _fonts()
    ar = lang == "ar"
    k = 1 if ar else 0
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    left, right = 50, w - 50
    put = (lambda y, txt, font="RcSans", size=10: (c.setFont(font, size), c.drawRightString(right, y, _ar(txt)))) if ar \
        else (lambda y, txt, font="RcSans", size=10: (c.setFont(font, size), c.drawString(left, y, txt)))

    c.setTitle(f"Application receipt {s.case_ref} (SYNTHETIC)")
    c.setFillColor(colors.HexColor("#92722A"))
    c.rect(0, h - 8, w, 8, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#8B0000"))
    c.rect(0, h - 30, w, 22, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("RcSans-Bold", 8)
    c.drawCentredString(w / 2, h - 23, "SYNTHETIC SAMPLE - PROTOTYPE RECEIPT - NOT AN EQUIVALENCY CERTIFICATE")
    c.setFillColor(colors.black)
    y = h - 70
    put(y, "Ministry of Education" if not ar else "وزارة التربية والتعليم", "RcSans-Bold", 13); y -= 20
    put(y, "Application receipt" if not ar else "إيصال تقديم الطلب", "RcSans-Bold", 16); y -= 18
    put(y, SERVICE_NAME if not ar else "طلب معادلة شهادة دراسية صفوف النقل من خارج الدولة", "RcSans", 9); y -= 30

    when = now_uae()                                  # UAE time, also when the server runs on UTC
    rows = [
        (("Reference", "الرقم المرجعي"), s.case_ref),
        (("Date", "التاريخ"), when.strftime("%Y-%m-%d %H:%M")),
        (("Student", "الطالب"), student_name),
        (("Status", "الحالة"), STATUS[s.status][k]),
    ]
    if s.receipt:
        rows.append((("Fee", "الرسوم"), (f"{SERVICE_FEE_AED} درهم، مدفوعة، الإيصال {s.receipt.receipt_id}" if ar
                                         else f"AED {SERVICE_FEE_AED}, paid, receipt {s.receipt.receipt_id}")))
    for (label, value) in rows:
        if ar:
            c.setFont("RcSans-Bold", 10); c.drawRightString(right, y, _ar(label[1] + ":"))
            c.setFont("RcSans", 10); c.drawRightString(right - 130, y, _ar(str(value)))
        else:
            c.setFont("RcSans-Bold", 10); c.drawString(left, y, label[0] + ":")
            c.setFont("RcSans", 10); c.drawString(left + 130, y, str(value))
        y -= 18
    y -= 14
    put(y, "Documents checked" if not ar else "المستندات التي تم فحصها", "RcSans-Bold", 11); y -= 18
    for u in s.uploads:
        v = s.verifications.get(u.doc_id)
        if u.doc_type == "school_certificate":
            name = (f"شهادة الصف {v.grade}" if ar else f"Grade {v.grade} certificate") if v and v.grade is not None \
                else ("شهادة مدرسية" if ar else "School certificate")
        else:
            name = DOC.get(u.doc_type, (u.doc_type, u.doc_type))[k]
        ok = v is not None and v.authenticity == "verified"
        mark = ("تم التحقق" if ar else "verified") if ok else ("لم يتم التحقق" if ar else "not verified")
        put(y, f"- {name} ({mark})"); y -= 15
    y -= 12
    if s.rule_report:
        passed = sum(r.status.value in ("PASS", "NOT_APPLICABLE") for r in s.rule_report.results)
        put(y, (f"فحص الشروط: {passed} من {len(s.rule_report.results)} مستوفاة أو لا تنطبق" if ar
                else f"Rules check: {passed} of {len(s.rule_report.results)} rules passed or not applicable"), "RcSans", 10)
        y -= 22
    put(y, "What happens next" if not ar else "الخطوة التالية", "RcSans-Bold", 11); y -= 18
    put(y, NEXT[s.status][k]); y -= 15
    put(y, (f"للاستفسار: الرقم المجاني {MOE_SUPPORT_NUMBER}" if ar else f"Questions: toll-free {MOE_SUPPORT_NUMBER}")); y -= 30
    c.setFont("RcSans", 8)
    c.setFillColor(colors.HexColor("#666666"))
    note = ("This receipt confirms the application only. It is not an equivalency certificate or decision."
            if not ar else "هذا الإيصال يؤكد تقديم الطلب فقط، وليس شهادة معادلة أو قراراً.")
    (c.drawRightString(right, 60, _ar(note)) if ar else c.drawString(left, 60, note))
    c.saveState()
    c.setFillColor(colors.Color(0.8, 0, 0, alpha=0.10)); c.setFont("RcSans-Bold", 44)
    c.translate(w / 2, h / 2); c.rotate(35); c.drawCentredString(0, 0, "SYNTHETIC SAMPLE")
    c.restoreState()
    c.save()
    return buf.getvalue()
