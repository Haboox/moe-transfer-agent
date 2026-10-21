"""Deterministic customer messages built ONLY from the case state and rule results, in English and Arabic.

Used whenever an answer must come from the record and not from the model (policies P-04, P-06, P-10):
outcomes, status, missing items, the requirements list, and the safe fallback when a model reply is blocked.
Both languages say the same thing: the Arabic missing items come from the rules engine itself (detail_ar).
The reply language is the language of the customer's latest message (agent/language.py), never the model's choice.
"""
from __future__ import annotations

from typing import Optional

from .config import GRADE12_SERVICE_URL, GRADE12_SERVICE_URL_AR, MOE_SUPPORT_NUMBER, SERVICE_FEE_AED
from .models import CaseState, CaseStatus, Outcome, RuleStatus
from .service_card import requirements_text  # noqa: F401  (re-exported for the agent)

REASON_TEXT = {
    "en": {
        "name_mismatch": "the name on a certificate does not match the passport",
        "verification_inconclusive": "a document could not be conclusively verified",
        "system_unavailable": "a verification system was unavailable, so nothing was guessed",
        "customer_request": "you asked to speak to a person",
        "other": "the case needs a decision the rules cannot make",
    },
    "ar": {
        "name_mismatch": "لأن الاسم في إحدى الشهادات لا يطابق الاسم في جواز السفر",
        "verification_inconclusive": "لأنه تعذر التحقق من إحدى الوثائق بشكل قاطع",
        "system_unavailable": "لأن نظام التحقق لم يكن متاحاً، لذلك لم يتم افتراض أي نتيجة",
        "customer_request": "لأنك طلبت التحدث مع موظف",
        "other": "لأن الطلب يحتاج إلى قرار لا تستطيع قواعد الخدمة اتخاذه",
    },
}

T = {
    "upload_prompt": {
        "en": ("To start, please upload these as PDF files (5 MB maximum each): the student's passport, "
               "Emirates ID, UAE visa (only if the student is not a GCC national), and the certificates for "
               "the last two years of study, with a legal translation for any certificate not in English or Arabic."),
        "ar": ("للبدء، يرجى تحميل الوثائق التالية بصيغة PDF (بحد أقصى 5 ميجابايت لكل ملف): جواز سفر الطالب، "
               "الهوية الإماراتية، الإقامة (لغير أبناء دول مجلس التعاون الخليجي)، وشهادات آخر سنتين "
               "دراسيتين، مع ترجمة قانونية لأي شهادة ليست باللغة العربية أو الإنجليزية."),
    },
    "grade12": {
        "en": ("This service covers Grades 2 to 11 only. For a completed Grade 12 certificate from abroad, please use "
               "the service 'Request for Equivalency Certificate - General Education from Abroad (Grade 12)': "
               f"{GRADE12_SERVICE_URL}"),
        "ar": ("هذه الخدمة تشمل الصفوف من الثاني إلى الحادي عشر فقط. لمعادلة شهادة الصف الثاني عشر من الخارج، "
               "يرجى استخدام خدمة 'طلب شهادة معادلة - التعليم العام من الخارج (الصف الثاني عشر)': "
               f"{GRADE12_SERVICE_URL_AR}"),
    },
    "out_of_scope": {
        "en": ("This service covers certificates for Grades 2 to 11 only, so it cannot be used for a {g} "
               "certificate. To find the right service, please contact the Ministry on its toll-free number "
               f"{MOE_SUPPORT_NUMBER}."),
        "ar": ("هذه الخدمة تشمل شهادات الصفوف من الثاني إلى الحادي عشر فقط، لذلك لا يمكن استخدامها لشهادة {g_ar}. "
               f"لمعرفة الخدمة المناسبة، يرجى التواصل مع الوزارة على الرقم المجاني {MOE_SUPPORT_NUMBER}."),
    },
    # Kindergarten or Grade 1 completed (A-15): explained, because the parent thinks of the grade the child is JOINING
    "low_grade": {
        "en": ("This service gives the equivalency of certificates for Grades 2 to 11 that a student has already "
               "completed outside the UAE. Your child has completed {g}, so the certificate would be a {g} "
               "certificate, which this service does not cover, even though your child is now joining {nxt}. This "
               "service does not state which procedure applies in that case, so please check with the Ministry on "
               f"its toll-free number {MOE_SUPPORT_NUMBER} before applying."),
        "ar": ("تمنح هذه الخدمة معادلة شهادات الصفوف من الثاني إلى الحادي عشر التي أنهاها الطالب خارج الدولة. أنهى "
               "طفلك {g_ar}، فتكون الشهادة شهادة {g_ar}، وهي لا تدخل ضمن هذه الخدمة، حتى لو كان طفلك سينتقل الآن "
               "إلى {nxt_ar}. لا توضح هذه الخدمة الإجراء المطلوب في هذه الحالة، لذلك يرجى التأكد من الوزارة على "
               f"الرقم المجاني {MOE_SUPPORT_NUMBER} قبل التقديم."),
    },
    "low_grade_why": {
        "en": ("I understand that your child is joining {nxt}. For this service, the grade that counts is the last "
               "grade completed abroad, the one shown on the certificate, and here that is {g}. A child who has "
               "completed Grade 2 or higher abroad applies through this service; for a child who has completed only "
               f"{{g}}, please check with the Ministry on its toll-free number {MOE_SUPPORT_NUMBER}."),
        "ar": ("أفهم أن طفلك سينتقل إلى {nxt_ar}. في هذه الخدمة، الصف المعتمد هو آخر صف أنهاه الطالب في الخارج، وهو "
               "الصف المذكور في الشهادة، وهو هنا {g_ar}. الطالب الذي أنهى الصف الثاني أو أعلى في الخارج يقدم عبر هذه "
               f"الخدمة، أما من أنهى {{g_ar}} فقط فيرجى التأكد من الوزارة على الرقم المجاني {MOE_SUPPORT_NUMBER}."),
    },
    "submitted": {
        "en": ("All service requirements are met and the AED {fee} fee has been paid. Your request is submitted with "
               "reference {ref}. A Ministry officer will issue the equivalency decision within the service time of "
               "30 working days, and it will be sent to the email registered in UAE Pass."),
        "ar": ("تم استيفاء جميع متطلبات الخدمة ودفع الرسوم البالغة {fee} درهماً. تم تقديم طلبك برقم مرجعي "
               "{ref}. سيُصدر موظف الوزارة قرار المعادلة خلال مدة الخدمة البالغة 30 يوم عمل، وسيتم إرساله إلى "
               "البريد الإلكتروني المسجل في الهوية الرقمية (UAE Pass)."),
    },
    "awaiting_payment": {
        "en": ("All service requirements are met. Please pay the AED {fee} service fee in the secure payment window "
               "to submit your request."),
        "ar": ("تم استيفاء جميع متطلبات الخدمة. يرجى دفع رسوم الخدمة البالغة {fee} درهماً في نافذة الدفع الآمنة "
               "لتقديم طلبك."),
    },
    "awaiting_payment_review": {
        "en": ("Your documents are checked. One point needs a decision by a Ministry officer: {why}. To submit your "
               "request for that review, please pay the AED {fee} service fee in the secure payment window. Like "
               "every request, it is paid for when it is submitted, whatever the officer decides."),
        "ar": ("تم فحص مستنداتك. هناك نقطة تحتاج إلى قرار من موظف في الوزارة {why}. لتقديم طلبك لهذه المراجعة، يرجى "
               "دفع رسوم الخدمة البالغة {fee} درهماً في نافذة الدفع الآمنة. وكما في كل الطلبات، تُدفع الرسوم عند تقديم "
               "الطلب أياً كان قرار الموظف."),
    },
    "fee_paid_note": {"en": "The AED {fee} fee is paid.", "ar": "تم دفع الرسوم البالغة {fee} درهماً."},
    "pending_review": {
        "en": ("Your case {ref} needs a decision by a Ministry staff member because {why}. I have passed it to a "
               "person for review. The review is completed within the service time of up to 30 working days, and you "
               "will be notified of the outcome."),
        "ar": ("طلبك {ref} يحتاج إلى قرار من موظف في الوزارة {why}. تمت إحالته إلى موظف للمراجعة، وتتم المراجعة "
               "خلال مدة الخدمة البالغة حتى 30 يوم عمل، وسيتم إبلاغك بالنتيجة."),
    },
    "reviewed": {
        "en": ("A Ministry officer has {word} case {ref}. The decision is sent to the email registered in UAE Pass. "
               f"For questions about this decision, call the Ministry on {MOE_SUPPORT_NUMBER}."),
        "ar": ("قام موظف الوزارة {word} الطلب {ref}، وأُرسل القرار إلى البريد الإلكتروني المسجل في الهوية الرقمية. "
               f"للاستفسار عن هذا القرار، يرجى الاتصال بالوزارة على الرقم {MOE_SUPPORT_NUMBER}."),
    },
    "needs_info": {
        "en": ("Thank you, I have checked {received}. Before the request can be submitted, the following is "
               "needed:\n\n{items}\n\nOnce you attach this, I will check the request again."),
        "ar": ("شكراً لك، قمت بفحص {received}. قبل تقديم الطلب، نحتاج إلى ما يلي:\n\n{items}\n\n"
               "بعد إرفاق ذلك سأعيد فحص الطلب."),
    },
    "system_down": {
        "en": ("The document verification system is not responding right now, so I cannot check your documents. "
               f"Nothing has been decided. Support: {MOE_SUPPORT_NUMBER}."),
        "ar": ("نظام التحقق من الوثائق لا يستجيب حالياً، لذلك لا يمكنني فحص وثائقك. لم يتم اتخاذ أي قرار. "
               f"للدعم: {MOE_SUPPORT_NUMBER}."),
    },
    "checking": {"en": "I am checking your documents against the service requirements.",
                 "ar": "أقوم الآن بفحص وثائقك مقابل متطلبات الخدمة."},
    "llm_down_note": {"en": "(The AI assistant is unavailable for a moment; this answer comes from the published service "
                            "information and your case record.)",
                      "ar": "(المساعد الذكي غير متاح مؤقتاً؛ هذه الإجابة من معلومات الخدمة المنشورة وسجل طلبك.)"},
    "llm_down": {"en": "(The assistant is temporarily unavailable, so this is an automatic update on your request.)",
                 "ar": "(المساعد غير متاح مؤقتاً، لذلك هذه رسالة تلقائية عن حالة طلبك.)"},
    "override": {
        "en": ("I can't make exceptions to the service rules or approve requests myself; the same rules apply to "
               "every application, and only a Ministry officer issues the equivalency decision."),
        "ar": ("لا يمكنني تجاوز قواعد الخدمة أو الموافقة على الطلبات بنفسي؛ نفس القواعد تطبق على جميع الطلبات، "
               "ويُصدر قرار المعادلة موظف الوزارة فقط."),
    },
    "requirements_intro": {
        "en": "Here are the requirements for this service.",
        "ar": "هذه متطلبات الخدمة.",
    },
    "not_on_card": {
        "en": ("If your question is not answered above, I don't have confirmed information about it for this "
               f"service. The Ministry can help on its toll-free number {MOE_SUPPORT_NUMBER}."),
        "ar": ("إذا لم تجد إجابة سؤالك أعلاه، فلا تتوفر لدي معلومات مؤكدة عنه لهذه الخدمة. "
               f"يمكن للوزارة مساعدتك على الرقم المجاني {MOE_SUPPORT_NUMBER}."),
    },
    "card_silent": {
        "en": ("I don't have confirmed information about this for this service, so I can't answer it or act on "
               f"it here. The Ministry can help on its toll-free number {MOE_SUPPORT_NUMBER}."),
        "ar": ("لا تتوفر لدي معلومات مؤكدة عن هذا الأمر في هذه الخدمة، لذلك لا يمكنني الإجابة عنه أو تنفيذه هنا. "
               f"يمكن للوزارة مساعدتك على الرقم المجاني {MOE_SUPPORT_NUMBER}."),
    },
    "no_application": {"en": "You have not started an application yet.", "ar": "لم تبدأ تقديم طلب بعد."},
    "system_outage": {"en": "A Ministry system is not responding right now, even after a second try, so I cannot "
                          "continue at the moment. Nothing has been submitted or charged and nothing is lost: "
                          "send any message in a few minutes and I will try again, or call the Ministry on its "
                          "toll-free number {phone}.",
                    "ar": "أحد أنظمة الوزارة لا يستجيب حالياً حتى بعد المحاولة مرة ثانية، لذلك لا يمكنني المتابعة الآن. "
                          "لم يُقدَّم أي شيء ولم تُحصَّل أي رسوم ولم يضع أي شيء: أرسل أي رسالة بعد دقائق وسأحاول مرة "
                          "أخرى، أو اتصل بالوزارة على الرقم المجاني {phone}."},
    "system_down_paid": {"en": "Your documents passed every check and the fee is paid (receipt {receipt}), but the "
                               "Ministry's case system is not responding right now, so the request is not registered "
                               "yet. You will not be charged again: send any message in a few minutes and I will try "
                               "again, or call the Ministry on its toll-free number {phone}.",
                         "ar": "اجتازت مستنداتك جميع الفحوص ودُفعت الرسوم (الإيصال {receipt})، لكن نظام إدارة الطلبات في "
                               "الوزارة لا يستجيب حالياً، لذلك لم يُسجَّل الطلب بعد. لن تُحصَّل الرسوم مرة أخرى: أرسل أي "
                               "رسالة بعد دقائق وسأحاول مرة أخرى، أو اتصل بالوزارة على الرقم المجاني {phone}."},
    "person_contact": {"en": "To speak with a Ministry employee, please call the Ministry's toll-free number {phone}. "
                             "I can also continue here: I can answer your questions about this service and check your "
                             "documents as soon as you attach them.",
                       "ar": "للتحدث مع موظف في الوزارة، يرجى الاتصال بالرقم المجاني للوزارة {phone}. ويمكنني أيضاً "
                             "متابعة طلبك هنا: أجيب عن أسئلتك حول هذه الخدمة وأفحص مستنداتك فور إرفاقها."},
    "person_contact_closed": {"en": "To speak with a Ministry employee, please call the Ministry's toll-free number {phone}. "
                                    "I can also answer your questions about this service here.",
                              "ar": "للتحدث مع موظف في الوزارة، يرجى الاتصال بالرقم المجاني للوزارة {phone}. ويمكنني أيضاً "
                                    "الإجابة هنا عن أسئلتك حول هذه الخدمة."},
    "closed_no_change": {"en": "The new file was not added: your request has already been sent, and it is decided on "
                               "the documents that were checked. If something needs to change, the Ministry can help "
                               "on its toll-free number {phone}.",
                         "ar": "لم تتم إضافة الملف الجديد: لقد تم إرسال طلبك بالفعل، ويُبت فيه بناءً على المستندات التي "
                               "تم فحصها. إذا احتاج شيء إلى تغيير، يمكن للوزارة مساعدتك على الرقم المجاني {phone}."},
    "as_above": {"en": "As listed above, you need", "ar": "كما ذكرت أعلاه، تحتاج إلى"},
}

GRADE_EN = {0: "kindergarten", 1: "Grade 1"}
GRADE_AR = {0: "رياض الأطفال", 1: "الصف الأول", 12: "الصف الثاني عشر"}


def say(key: str, lang: str = "en", **fields) -> str:
    text = T[key]["ar" if lang == "ar" else "en"]
    return text.format(**fields) if fields else text


def lang_of(s: CaseState) -> str:
    """Language of the customer's latest message (decided by code in agent/language.py)."""
    return "ar" if s.lang == "ar" else "en"


def redirect_message(lang: str = "en", grade: Optional[int] = 12) -> str:
    """Wrong service (R-01 / P-06): Grade 12 has its own service; other grades are not covered by this one."""
    if grade is None or grade == 12:
        return say("grade12", lang)
    if grade in (0, 1):
        return say("low_grade", lang, **_low_fields(grade))
    return say("out_of_scope", lang, g=GRADE_EN.get(grade, f"Grade {grade}"), g_ar=GRADE_AR.get(grade, f"الصف {grade}"))


def _low_fields(grade: int) -> dict:
    return {"g": GRADE_EN[grade], "g_ar": GRADE_AR[grade], "nxt": "Grade 1" if grade == 0 else "Grade 2",
            "nxt_ar": "الصف الأول" if grade == 0 else "الصف الثاني"}


def low_grade_why(lang: str, grade: int) -> str:
    """The parent asks again after a Kindergarten or Grade 1 redirect: explain instead of repeating."""
    return say("low_grade_why", lang, **_low_fields(grade))


def scope_grade(s: CaseState) -> Optional[int]:
    """The out-of-range grade behind a redirect: stated by the customer (P-06) or found on the certificates (R-01)."""
    if s.scope_grade is not None:
        return s.scope_grade
    certs = [v.grade for v in s.verifications.values() if v.grade is not None]
    return max(certs) if certs else None


DOC_WORDS = {"passport": ("the passport", "جواز السفر"), "emirates_id": ("the Emirates ID", "الهوية الإماراتية"),
             "uae_visa": ("the visa", "الإقامة"), "supporting_document": ("a supporting document", "مرفق داعم")}


def received_list(s: CaseState, lang: str) -> str:
    """The documents checked so far, in words ("the passport, the Emirates ID and the Grade 6 certificate")."""
    ar = lang == "ar"
    names = []
    for u in s.uploads:
        v = s.verifications.get(u.doc_id)
        if u.doc_type == "school_certificate":
            g = v.grade if v and v.grade is not None else None
            names.append((f"شهادة الصف {g}" if g is not None else "شهادة مدرسية") if ar
                         else (f"the Grade {g} certificate" if g is not None else "a school certificate"))
        elif u.doc_type == "legal_translation":
            names.append("ترجمة قانونية" if ar else "a legal translation")
        else:
            names.append(DOC_WORDS.get(u.doc_type, (u.doc_type, u.doc_type))[1 if ar else 0])
    if not names:
        return "مستنداتك" if ar else "your documents"
    if len(names) == 1:
        return names[0]
    return ("، ".join(names[:-1]) + " و" + names[-1]) if ar else (", ".join(names[:-1]) + " and " + names[-1])


def status_message(s: CaseState, lang: Optional[str] = None) -> str:
    lang = lang or lang_of(s)
    ar = lang == "ar"
    r = s.rule_report
    if s.status == CaseStatus.SUBMITTED:
        return say("submitted", lang, fee=SERVICE_FEE_AED, ref=s.case_ref)
    if s.status == CaseStatus.AWAITING_PAYMENT:
        if r is not None and r.outcome == Outcome.HUMAN_REVIEW:        # D-06: paid first, then the officer
            review = {x.rule_id for x in r.by_status(RuleStatus.REVIEW)}
            code = "name_mismatch" if "R-14" in review else "verification_inconclusive"
            return say("awaiting_payment_review", lang, fee=SERVICE_FEE_AED,
                       why=REASON_TEXT["ar" if ar else "en"].get(code, REASON_TEXT["ar" if ar else "en"]["other"]))
        return say("awaiting_payment", lang, fee=SERVICE_FEE_AED)
    if s.status == CaseStatus.PENDING_HUMAN_REVIEW:
        reasons = REASON_TEXT["ar" if ar else "en"]
        msg = say("pending_review", lang, ref=s.case_ref,
                  why=reasons.get(s.escalation_reason or "other", reasons["other"]))
        return msg + (" " + say("fee_paid_note", lang, fee=SERVICE_FEE_AED) if s.receipt else "")
    if s.status in (CaseStatus.HUMAN_APPROVED, CaseStatus.HUMAN_REJECTED):
        ok = s.status == CaseStatus.HUMAN_APPROVED
        word = ("بالموافقة على" if ok else "بعدم الموافقة على") if ar else ("approved" if ok else "not approved")
        return say("reviewed", lang, word=word, ref=s.case_ref)
    if s.status == CaseStatus.REDIRECTED:
        return redirect_message(lang, scope_grade(s))
    if not s.uploads:
        from .guide import next_step              # the same wording as the guided answers (stated grade, GCC)
        return next_step(s, lang, s.stated_grade) or say("upload_prompt", lang)
    if r is not None and not s.rules_stale and r.outcome == Outcome.NEEDS_INFO:
        items = "\n".join(f"- {(x.detail_ar or x.detail) if ar else x.detail}" for x in r.results
                          if x.status in (RuleStatus.MISSING, RuleStatus.FAIL))
        return say("needs_info", lang, items=items, received=received_list(s, lang))
    if s.failed_verifications:
        return say("system_down", lang)
    return say("checking", lang)


def outcome_panel(s: CaseState) -> dict:
    r = s.rule_report
    return {
        "case_status": s.status.value,
        "rule_outcome": (r.outcome.value + (" (stale: new uploads)" if s.rules_stale else "")) if r else "not evaluated",
        "case_ref": s.case_ref,
        "fee": "paid" if s.receipt else "not paid",
        "message": status_message(s),
        "rules": [{"id": x.rule_id, "status": x.status.value, "detail": x.detail, "detail_ar": x.detail_ar,
                   "source": x.source} for x in (r.results if r else [])],
    }
