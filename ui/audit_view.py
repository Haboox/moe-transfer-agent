"""The audit trail in plain words, for the staff screen: who acted, what happened and why, one line per event.

The log itself (logs/audit_<session>.jsonl) is unchanged and still downloadable; this only reads it.
Values in the log are already masked (agent/redact.py), so nothing sensitive appears here either.
"""
from __future__ import annotations

ACTOR = {
    "customer": ("Parent", "ولي الأمر"), "model": ("AI model", "نموذج الذكاء الاصطناعي"),
    "guard": ("Guard", "الحارس"), "tool": ("Tool", "أداة"), "rules": ("Rules engine", "محرك القواعد"),
    "policy": ("Policy", "السياسة"), "human": ("Officer", "الموظف"), "system": ("System", "النظام"),
}
TOOL = {
    "get_service_requirements": ("read the service card", "قراءة بطاقة الخدمة"),
    "get_applicant_profile": ("load the UAE Pass profile", "تحميل ملف الهوية الرقمية"),
    "list_uploaded_documents": ("list the attached documents", "عرض المستندات المرفقة"),
    "verify_documents": ("verify the documents", "التحقق من المستندات"),
    "evaluate_rules": ("check the rules", "فحص الشروط"),
    "request_payment": ("open the payment window", "فتح نافذة الدفع"),
    "submit_application": ("submit the application", "تقديم الطلب"),
    "escalate_to_human": ("send the case to an officer", "إحالة الطلب إلى موظف"),
    "get_case_status": ("read the case status", "قراءة حالة الطلب"),
}
DOC = {"passport": ("passport", "جواز السفر"), "emirates_id": ("Emirates ID", "الهوية الإماراتية"),
       "uae_visa": ("residence visa", "الإقامة"), "school_certificate": ("school certificate", "شهادة مدرسية"),
       "legal_translation": ("legal translation", "ترجمة قانونية"), "supporting_document": ("supporting document", "مرفق داعم")}
POLICY = {
    "requirements_attached": ("answered from the service card", "أُجيب من بطاقة الخدمة"),
    "reply_from_record": ("reply written from the case record or the card", "الرد مكتوب من سجل الطلب أو البطاقة"),
    "reply_replaced": ("model reply blocked and replaced", "حُجب رد النموذج واستُبدل"),
    "redirected_wrong_service": ("redirected: grade outside this service", "تحويل: الصف خارج نطاق الخدمة"),
    "redirect_withdrawn": ("redirect withdrawn after the parent's correction", "أُلغي التحويل بعد تصحيح ولي الأمر"),
    "payment_window_closed": ("payment window closed: new documents, rules must run again",
                              "أُغلقت نافذة الدفع: مستندات جديدة ويجب إعادة الفحص"),
    "model_reminded": ("model reminded to finish the standard steps", "تذكير النموذج بإكمال الخطوات المعتادة"),
    "security_event": ("manipulation attempt detected", "رُصدت محاولة تلاعب"),
    "card_silent_topic": ("topic not covered by the card: toll-free number given", "موضوع لا تغطيه البطاقة: أُعطي الرقم المجاني"),
    "upload_refused_case_closed": ("upload refused: case already closed", "رُفض الإرفاق: الطلب مغلق"),
    "intent_corrected": ("AI reading corrected by code", "صُحح فهم النموذج بواسطة الشيفرة"),
    "person_contact_given": ("parent asked for a person: toll-free number given, no case referred",
                             "طلب ولي الأمر موظفاً: أُعطي الرقم المجاني ولم يُحَل الطلب"),
    "clock_answered": ("time and date given from the system clock (UAE time), not by the AI",
                       "أُعطي الوقت والتاريخ من ساعة النظام (بتوقيت الإمارات) وليس من الذكاء الاصطناعي"),
    "off_topic_answered": ("question outside the service: fixed reply, nothing invented",
                           "سؤال خارج الخدمة: رد ثابت دون اختلاق معلومات"),
    "redirect_explained": ("parent asked again: the grade rule explained (last grade completed)",
                           "سأل ولي الأمر مجدداً: شُرح أن المعتمد هو آخر صف مكتمل"),
    "handover_failed": ("a Ministry system stayed down: the parent was told, nothing submitted",
                        "تعطل أحد أنظمة الوزارة: أُبلغ ولي الأمر ولم يُقدَّم شيء"),
    "max_steps_reached": ("step limit reached", "بلغ الحد الأقصى للخطوات"),
    "context_near_limit": ("conversation near the model's limit", "المحادثة قريبة من حد النموذج"),
}


def _q(text: str, n: int = 140) -> str:
    text = " ".join((text or "").split())
    return "“" + (text[:n] + "…" if len(text) > n else text) + "”"


def describe(e: dict, lang: str) -> str:
    ar = lang == "ar"
    k = 1 if ar else 0
    d, ev = e.get("detail") or {}, e.get("event", "")
    if ev == "session_started":
        return "بدأت الجلسة" if ar else "Session started"
    if ev == "customer_message":
        return ("كتب ولي الأمر: " if ar else "Parent wrote: ") + _q(str(d.get("text", "")).split("\n[")[0])
    if ev == "document_uploaded":
        doc = DOC.get(d.get("doc_type"), (d.get("doc_type"), d.get("doc_type")))[k]
        return (f"أرفق ولي الأمر {doc}" if ar else f"Parent attached the {doc}") + f" ({d.get('file_format')}, {d.get('size_mb')} MB)"
    if ev == "document_removed":
        return "أزال ولي الأمر مستنداً مرفقاً" if ar else "Parent removed an attached document"
    if ev == "intent_interpreted" and "no model call" in (e.get("basis") or ""):
        return "قرأت الشيفرة الرسالة (حديث عام أو رد ثابت، دون استدعاء النموذج)" if ar else \
            "Code read the message (small talk or a fixed answer, no model call)"
    if ev == "intent_interpreted":
        return (f"فهم النموذج الطلب: {d.get('intent')} (الثقة {d.get('confidence')})" if ar
                else f"AI read the request as: {d.get('intent')} (confidence {d.get('confidence')})")
    if ev == "tool_requested":
        tool = d.get("tool")
        who = ("السياسة" if ar else "Policy") if e.get("actor") == "policy" else ("النموذج" if ar else "AI")
        return (f"طلب {who}: {TOOL.get(tool, (tool, tool))[1]}" if ar
                else f"{who} asked to {TOOL.get(tool, (tool, tool))[0]}")
    if ev == "model_step":
        return (f"خطوة النموذج {d.get('step')} ({d.get('prompt_tokens')} من {d.get('context_limit')} رمزاً)" if ar
                else f"AI step {d.get('step')} ({d.get('prompt_tokens')} of {d.get('context_limit')} tokens)")
    if ev == "tool_allowed":
        return (f"سمح الحارس: {TOOL.get(d.get('tool'), (d.get('tool'),) * 2)[1]}" if ar
                else f"Guard allowed: {TOOL.get(d.get('tool'), (d.get('tool'),) * 2)[0]}")
    if ev == "tool_blocked":
        return (f"منع الحارس: {d.get('tool')} ({d.get('reason', '')})" if ar
                else f"Guard blocked: {d.get('tool')} ({d.get('reason', '')})")
    if ev == "backend_call":
        return (f"نظام {d.get('system')}: {d.get('operation')} محاولة {d.get('attempt')} ← {d.get('outcome')}" if ar
                else f"{d.get('system')} system: {d.get('operation')}, attempt {d.get('attempt')} → {d.get('outcome')}")
    if ev == "tool_result":
        return (f"نتيجة {d.get('tool')}: {d.get('status')}" if ar else f"{d.get('tool')} finished: {d.get('status')}")
    if ev == "rules_evaluated":
        res = d.get("results") or {}
        bad = [f"{r} {v}" for r, v in res.items() if v not in ("PASS", "NOT_APPLICABLE")]
        tail = ("، ".join(bad) if ar else ", ".join(bad)) if bad else ("جميع الشروط مستوفاة" if ar else "all rules passed")
        return (f"فحص الشروط ← {d.get('outcome')}: {tail}" if ar else f"Rules checked → {d.get('outcome')}: {tail}")
    if ev == "payment_completed":
        return (f"دُفعت الرسوم ({d.get('method')}، {d.get('amount_aed')} درهم، الإيصال {d.get('receipt_id')})" if ar
                else f"Fee paid ({d.get('method')}, AED {d.get('amount_aed')}, receipt {d.get('receipt_id')})")
    if ev == "payment_declined":
        return (f"رُفض الدفع ({d.get('method')}: {d.get('reason')})" if ar else f"Payment declined ({d.get('method')}: {d.get('reason')})")
    if ev == "human_decision":
        verb = ("وافق على" if d.get("decision") == "approve" else "رفض") if ar else (
            "approved" if d.get("decision") == "approve" else "rejected")
        return (f"الموظف {d.get('reviewer_id')} {verb} الطلب {d.get('case_ref')}: {_q(d.get('note', ''))}" if ar
                else f"Officer {d.get('reviewer_id')} {verb} case {d.get('case_ref')}: {_q(d.get('note', ''))}")
    if ev == "case_status_refreshed":
        return (f"تحدثت حالة الطلب {d.get('case_ref')}: {d.get('old')} ← {d.get('new')}" if ar
                else f"Case {d.get('case_ref')} updated: {d.get('old')} → {d.get('new')}")
    if ev == "agent_reply":
        return ("رد المساعد: " if ar else "Assistant replied: ") + _q(d.get("text", ""))
    if ev in POLICY:
        return POLICY[ev][k]
    if ev in ("llm_call_failed", "interpret_failed"):
        return "لم يستجب النموذج؛ تابعت الشيفرة من السجل" if ar else "The AI model did not answer; code continued from the record"
    return ev.replace("_", " ")


def actor(name: str, lang: str) -> str:
    return ACTOR.get(name, (name, name))[1 if lang == "ar" else 0]
