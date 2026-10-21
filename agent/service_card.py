"""The service card text the agent is allowed to quote (policy P-10), in English and Arabic.

Copied word for word from the published cards (docs/00_service_card.md and docs/00_service_card_ar.md).
The rule IDs in brackets trace every line to a rule (agent/rules.py). They are internal: requirements_text()
removes them before the parent sees the text.

Service time (decision D-01, revised after the Ministry's answer of 16 October 2026): the published 30 working days
is the service time stated to the parent. What the agent adds (a complete request is checked and submitted at once)
is shown only as a proposed improvement, never as a service commitment.
"""
import re

from .config import MOE_SUPPORT_NUMBER, SERVICE_FEE_AED

RULE_ID = re.compile(r"\s*\(R-\d{2}\)")

CARD = {
    "en": {
        "heading": "Service requirements",
        "covers_label": "About this service",
        "steps_label": "Service process",
        "steps": ["Log in using UAE Pass", "Fill out the application and upload the required documents.",
                  "Pay the applicable fees.",
                  "Receive the General Education Certificate Equivalency Decision via the email registered in the UAE Pass."],
        "covers": "This service aims to provide applicants with equivalency certificate for Grades 2-11 issued from "
                  "general education institutes outside the UAE, in accordance with the standards approved by the "
                  "Ministry. (R-01)",
        "documents_label": "Required documents",
        "documents": [
            "Valid passport (R-02)",
            "Valid Emirates ID. (R-03)",
            "Valid UAE Visa for non-GCC Nationals. (R-04)",
            "Certificates of the previous 2 years of study. (R-05)",
            "Legal translation if the certificate was issued in language other than English or Arabic. (R-06)",
            "Additional supporting documents (maximum of 2 documents) (R-11)",
        ],
        "conditions_label": "Service conditions",
        "conditions": [
            "Attest all certificates from the Ministry of Education, educational authorities or councils in the "
            "country of study. (R-07)",
            "Attest the last certificate that the student passed from the Ministry of Foreign Affairs and the UAE "
            "Embassy or UAE Education and Technology Science Attache (previously known as Cultural Attache) in the "
            "country of study. (R-08)",
            "Incomplete statements or certificates during the academic year are not valid. (R-09)",
        ],
        "notes_label": "Notes",
        "notes": [
            "The accepted file format is PDF, and the size limit for each file is 5 MB. (R-10)",
            "If there are multiple documents for the same requirement, please merge them into a single file. (R-13)",
        ],
        "fee": f"Fees: {SERVICE_FEE_AED} AED",
        "time": "Service time: 30 working days",                # the published card (official baseline)
        "support": f"Support: Toll-free number: {MOE_SUPPORT_NUMBER}",
        "grade12": "Grade 12 certificates have their own equivalency service.",
    },
    "ar": {
        "heading": "متطلبات الخدمة",
        "covers_label": "حول هذه الخدمة",
        "steps_label": "إجراءات الخدمة",
        "steps": ["تسجيل الدخول باستخدام الهوية الرقمية.", "تعبئة البيانات المطلوبة وإرفاق المستندات اللازمة.",
                  "دفع الرسوم الخدمة.",
                  "استلام شهادة المعادلة شهادة التعليم العام عبر البريد الإلكتروني المسجل في الهوية الرقمية."],
        "covers": "تتيح هذه الخدمة معادلة الشهادات الدراسية لصفوف النقل من الصف الثاني إلى الصف الحادي عشر الصادرة "
                  "من خارج دولة الإمارات العربية المتحدة، حسب المعايير المعتمدة من قبل الوزارة. (R-01)",
        "documents_label": "المستندات المطلوبة",
        "documents": [
            "جواز السفر (ساري المفعول) (R-02)",
            "والهوية الاماراتية (سارية المفعول) (R-03)",
            "الإقامة سارية المفعول (لغير أبناء دول مجلس التعاون الخليجي). (R-04)",
            "الشهادات لآخر سنتين دراسيتين (R-05)",
            "ترجمة قانونية (في حال كانت لغة الشهادة بلغة أخرى غير اللغة العربية أو اللغة الإنجليزية) (R-06)",
            "مرفقات إضافية داعمة إن وجد (مرفقين كحد أقصى) (R-11)",
        ],
        "conditions_label": "شروط الخدمة",
        "conditions": [
            "تصديق الشهادات المذكورة من وزارة التربية والتعليم او المديرية او مجلس التعليم في بلد الإصدار. (R-07)",
            "تصديق آخر شهادة دراسية نجح فيها الطالب من وزارة الخارجية في بلد اصدار الشهادة وسفارة دولة الإمارات في "
            "بلد الاصدار أو ملحق التعليم و علوم التكنولوجيا ( الملحق الثقافي سابقا) لدولة الامارات في بلد الإصدار. (R-08)",
            "لا يعتد بالشهادات أو الافادات الفصلية الصادرة خلال العام الدراسي. (R-09)",
        ],
        "notes_label": "ملاحظات",
        "notes": [
            "صيغة الملفات المقبولة PDF، والحد الأقصى لحجم كل ملف 5 ميجابايت. (R-10)",
            "إذا كان هناك أكثر من مستند للمتطلب نفسه، يرجى دمجها في ملف واحد. (R-13)",
        ],
        "fee": f"الرسوم: {SERVICE_FEE_AED} درهم",
        "time": "وقت الخدمة: 30 يوم عمل",                       # بطاقة الخدمة المنشورة (المدة الرسمية)
        "support": f"الدعم: الهاتف المجاني: {MOE_SUPPORT_NUMBER}",
        "grade12": "لشهادات الصف الثاني عشر خدمة معادلة مستقلة.",
    },
}


def public(text: str) -> str:
    """Card line as the parent sees it: without the internal rule ID."""
    return RULE_ID.sub("", text)


def requirements_text(lang: str = "en") -> str:
    c = CARD["ar" if lang == "ar" else "en"]
    lines = [f"**{c['heading']}**", "", f"**{c['covers_label']}:** {public(c['covers'])} {c['grade12']}", "",
             f"**{c['documents_label']}:**"]
    lines += [f"- {public(d)}" for d in c["documents"]]
    lines += ["", f"**{c['conditions_label']}:**"] + [f"- {public(x)}" for x in c["conditions"]]
    lines += ["", f"**{c['notes_label']}:**"] + [f"- {public(x)}" for x in c["notes"]]
    lines += ["", f"- {c['fee']}", f"- {c['time']}", f"- {c['support']}"]
    return "\n".join(lines)
