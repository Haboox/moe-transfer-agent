"""Staff portal: the officer's side. The only place where an escalated case is approved or rejected (Approve).

Decision workflow (D-02): the agent never decides equivalency. The case list shows what needs a decision first: the
exceptions the rules could not decide, then the submitted cases that passed every automated check; an officer decides
both. Every request reaching an officer is paid for first (D-06), one sent because a system was down included.

Layout: summary tiles; the case list on the left; the open case on the right, top to bottom: what needs deciding,
the evidence (with every document viewable on the page), the AI summary (labelled), the timeline of what happened,
and the decision. The full audit trail of every session is in its own tab.

Shows the cases of the current demonstration only (one case list per browser visit, ui/session.py), written so an
officer can read a case at a glance: who, which grade, why it needs a person (the rules' own words), which documents
were checked, and the AI summary clearly labelled as AI written. The audit trail is shown in plain words.
"""
from __future__ import annotations

import json
from datetime import datetime
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from agent.config import LOG_DIR, ROOT
from agent.countries import shown
from agent.facts import UAE
from agent.human_review import ReviewError, decide
from agent.mocks import CaseStore
from agent.models import CaseStatus
from ui.audit_view import actor, describe
from ui.i18n import reason, t
from ui.session import bind, case_store, catalogue, persona_title
from ui.viewer import view_button

OFFICER = "STAFF-DEMO1"
DOC_LABEL = {"passport": ("Passport", "جواز السفر"), "emirates_id": ("Emirates ID", "الهوية الإماراتية"),
             "uae_visa": ("Residence visa", "الإقامة"), "legal_translation": ("Legal translation", "ترجمة قانونية"),
             "supporting_document": ("Supporting document", "مرفق داعم")}


def _student(student_ref: str, lang: str) -> str:
    """Name, nationality and grade of the synthetic student (screen only; the log keeps the reference)."""
    for pid, p in catalogue().personas.items():
        if p["student"]["student_ref"] == student_ref:
            return persona_title(pid, lang)
    return t("student_unknown", lang) if student_ref == "UNKNOWN" else student_ref


def _local(ts: str, fmt: str = "%H:%M:%S") -> str:
    """Log times are UTC; the screen shows UAE time, wherever the portal runs (the online copy's server is on UTC)."""
    try:
        return datetime.fromisoformat(ts).astimezone(UAE).strftime(fmt)
    except (TypeError, ValueError):
        return ts or ""


def _when(rec) -> str:
    return _local(rec.created_at or "", "%H:%M")


KPI = (("kpi_waiting", "warn", ":material/flag:"), ("kpi_submitted", "ok", ":material/task_alt:"),
       ("kpi_decided", "muted", ":material/gavel:"), ("kpi_total", "gold", ":material/folder:"))
PILL = {CaseStatus.PENDING_HUMAN_REVIEW: "p-amber", CaseStatus.SUBMITTED: "p-green",
        CaseStatus.HUMAN_APPROVED: "p-green", CaseStatus.HUMAN_REJECTED: "p-red"}
TO_DECIDE = (CaseStatus.PENDING_HUMAN_REVIEW, CaseStatus.SUBMITTED)
DECIDED = (CaseStatus.HUMAN_APPROVED, CaseStatus.HUMAN_REJECTED)


def _kpis(cases, lang: str) -> None:
    counts = (sum(c.status == CaseStatus.PENDING_HUMAN_REVIEW for c in cases),
              sum(c.status == CaseStatus.SUBMITTED for c in cases),
              sum(c.status in DECIDED for c in cases), len(cases))
    for col, (key, tone, _), n in zip(st.columns(4), KPI, counts):
        col.markdown(f"<div class='kpi {tone}'><div class='n'>{n}</div><div class='l'>{escape(t(key, lang))}</div></div>",
                     unsafe_allow_html=True)


def _pill(rec, lang: str) -> str:
    return f"<span class='pill {PILL.get(rec.status, 'p-grey')}'>{escape(t('st_' + rec.status.value, lang))}</span>"


def _why(rec, lang: str) -> str:
    """Why the case needs a person, in the rules' own words (staff language)."""
    ar = lang == "ar"
    if rec.problems:
        items = "".join(
            f"<li><b>{escape(p.get('title_ar') if ar else p.get('title'))}</b> "
            f"<span class='muted'>({escape(t('rs_' + p['status'], lang))})</span><br>"
            f"{escape((p.get('detail_ar') or p.get('detail')) if ar else p.get('detail'))}</li>"
            for p in rec.problems)
        return f"<ul class='why'>{items}</ul>"
    return f"<ul class='why'><li>{escape(reason(rec.escalation_reason, lang))}</li></ul>"


# ------------------------------------------------------------------ evidence: what exactly is wrong, on which document
def _all_docs() -> dict:
    docs = dict(catalogue().documents)
    if st.session_state.get("agent"):
        docs.update(st.session_state.agent.backend.documents)   # files uploaded in this demonstration
    return docs


def _name(reg: dict, lang: str) -> str:
    """The holder's name as printed on the document (both scripts when the document has both)."""
    en, ar = reg.get("holder_name"), reg.get("holder_name_ar")
    return " / ".join(x for x in ((ar, en) if lang == "ar" else (en, ar)) if x) or "?"


def _same(a: dict, b: dict) -> bool | None:
    """Same comparison as rule R-14: in the script both documents share."""
    from agent.language import normalize_name
    for k in ("holder_name_ar", "holder_name"):
        if a.get(k) and b.get(k):
            return normalize_name(a[k]) == normalize_name(b[k])
    return None


def _doc_title(d: dict, reg: dict, lang: str) -> str:
    ar = lang == "ar"
    if d["doc_type"] == "school_certificate":
        g = d.get("grade") if d.get("grade") is not None else reg.get("grade")
        return (f"شهادة الصف {g}" if ar else f"Grade {g} certificate") if g is not None else (
            "شهادة مدرسية" if ar else "School certificate")
    if d["doc_type"] == "legal_translation":
        return "ترجمة قانونية" if ar else "Legal translation"
    return DOC_LABEL.get(d["doc_type"], (d["doc_type"], d["doc_type"]))[1 if ar else 0]


def _evidence(rec, lang: str) -> str:
    """One row per document: name on it, dates, country, verification. Cells that caused the escalation are
    marked, so the officer sees WHAT does not match and WHERE without opening every file."""
    ar = lang == "ar"
    docs = _all_docs()
    rows, passport = [], None
    for d in rec.documents:
        reg = (docs.get(d.get("doc_id") or "") or {}).get("registry", {})
        if d["doc_type"] == "passport":
            passport = reg
        rows.append((d, reg))
    flagged = {p["rule_id"] for p in rec.problems}
    head = ("<tr><th>" + "</th><th>".join(
        ("المستند", "الاسم في المستند", "مطابق للجواز؟", "التاريخ", "بلد الدراسة", "التحقق") if ar else
        ("Document", "Name on the document", "Same as passport?", "Date", "Country of study", "Verification")) + "</th></tr>")
    body = []
    for d, reg in rows:
        same = "" if d["doc_type"] == "passport" or passport is None or not reg else _same(reg, passport)
        same_txt = {True: ("نعم" if ar else "Yes"), False: ("لا" if ar else "No"), None: ("لا يمكن المقارنة" if ar
                    else "Cannot compare"), "": ""}[same]
        bad_name = same is False and "R-14" in flagged
        date = reg.get("expiry") and ((("تنتهي " if ar else "expires ") + reg["expiry"]))
        date = date or reg.get("academic_year") or ""
        expired = bool(reg.get("expiry")) and any(p["rule_id"] in ("R-02", "R-03", "R-04") and p["status"] == "FAIL"
                                                 for p in rec.problems) and reg["expiry"] < datetime.now().date().isoformat()
        unconfirmed = not d.get("verified")
        cells = [escape(_doc_title(d, reg, lang)),
                 f"<span class='{'bad' if bad_name else ''}'>{escape(_name(reg, lang))}</span>",
                 f"<span class='{'bad' if bad_name else ''}'>{escape(same_txt)}</span>",
                 f"<span class='{'bad' if expired else ''}'>{escape(date)}</span>",
                 escape(shown(reg.get("country_of_study", ""), lang) if reg.get("country_of_study") else ""),
                 f"<span class='{'bad' if unconfirmed else 'ok'}'>"
                 + escape(("تم التحقق" if ar else "verified") if not unconfirmed else
                          ("لم يتأكد" if ar else "not confirmed")) + "</span>"]
        body.append("<tr><td>" + "</td><td>".join(cells) + "</td></tr>")
    return f"<div class='tablewrap'><table class='rules evidence'>{head}{''.join(body)}</table></div>" if body else ""


def _why_short(c, lang: str) -> str:
    if c.problems:
        return ("؛ " if lang == "ar" else "; ").join((p.get("title_ar") if lang == "ar" else p["title"]) or p["title"]
                                                   for p in c.problems)
    return reason(c.escalation_reason, lang) if c.escalation_reason else t("all_passed", lang)


def _documents(rec, lang: str) -> None:
    """Every checked document with View (opens on the page) and Download."""
    docs = _all_docs()
    have = [d for d in rec.documents if d.get("doc_id") in docs]
    if not have:
        return
    st.markdown(f"<div class='h5'>{escape(t('case_open_docs', lang))}</div>", unsafe_allow_html=True)
    for i, d in enumerate(have):
        dd = docs[d["doc_id"]]
        path = ROOT / dd["path"]
        title = _doc_title(d, dd.get("registry", {}), lang)
        a, b, c = st.columns([2.4, 1, 1.1], vertical_alignment="center")
        a.markdown(f"<div class='att'>{'✓' if d.get('verified') else '•'} {escape(title)}</div>", unsafe_allow_html=True)
        view_button(b, path, f"{rec.case_ref} · {title}", dd["file_name"], lang, key=f"st_{rec.case_ref}_{i}")
        if path.exists():
            c.download_button(t("view_download", lang), path.read_bytes(), file_name=dd["file_name"],
                              key=f"dl_{rec.case_ref}_{i}", icon=":material/download:", type="tertiary")


KEY_EVENTS = {"session_started", "customer_message", "document_uploaded", "document_removed", "rules_evaluated",
              "payment_completed", "payment_declined", "security_event", "human_decision", "person_contact_given",
              "payment_window_closed", "upload_refused_case_closed"}


def _events(rec) -> list[dict]:
    path = Path(LOG_DIR) / f"audit_{rec.session_id}.jsonl"
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def _timeline(rec, lang: str) -> None:
    """What happened on this case, in plain words and UAE time: the key steps first, every step on request."""
    events = _events(rec)
    if not events:
        return
    key = [e for e in events if e["event"] in KEY_EVENTS
           or (e["event"] == "tool_result" and e["detail"].get("tool") in ("submit_application", "escalate_to_human"))]
    with st.expander(t("case_timeline", lang, n=len(key)), icon=":material/timeline:"):
        every = st.toggle(t("case_every_step", lang), key=f"every_{rec.case_ref}")
        rows = events if every else key
        st.markdown("<div class='timeline'>" + "".join(
            f"<div class='ev {escape(e['actor'])}'><span class='tm'>{escape(_local(e['ts'], '%H:%M:%S'))}</span>"
            f"<span class='who'>{escape(actor(e['actor'], lang))}</span>"
            f"<span class='what'>{escape(describe(e, lang))}</span>"
            f"<span class='why'>{escape(e['basis'])}</span></div>" for e in rows) + "</div>",
            unsafe_allow_html=True)


def _decided_box(rec, lang: str) -> None:
    when = next((_local(e["ts"], "%H:%M") for e in reversed(_events(rec)) if e["event"] == "human_decision"), "")
    ok = rec.status == CaseStatus.HUMAN_APPROVED
    st.markdown(f"<div class='callout {'ok' if ok else 'bad'}'><b>{escape(t('st_' + rec.status.value, lang))}</b>"
                f"<span class='muted'> · {escape(rec.reviewer_id or '')} · {escape(when)}</span>"
                f"<div>{escape(rec.reviewer_note or '')}</div></div>", unsafe_allow_html=True)


def _decision_form(store: CaseStore, rec, lang: str) -> None:
    ready = rec.status == CaseStatus.SUBMITTED
    st.markdown(f"<div class='h5'>{escape(t('case_decide', lang))}</div>", unsafe_allow_html=True)
    with st.form(f"decide_{rec.case_ref}", border=False):
        a, b = st.columns([1, 2.4])
        officer = a.text_input(t("officer_id", lang), OFFICER, key=f"o_{rec.case_ref}")
        note = b.text_input(t("decision_note", lang), key=f"n_{rec.case_ref}",
                            placeholder=t("ready_note_ph" if ready else "decision_note_ph", lang))
        x, y, _ = st.columns([1, 1, 2])
        approve = x.form_submit_button(t("approve", lang), type="primary", width="stretch", icon=":material/check:")
        reject = y.form_submit_button(t("reject", lang), width="stretch", icon=":material/close:")
    if approve or reject:
        try:
            decide(store, rec.case_ref, officer, "approve" if approve else "reject", note)
            st.session_state.flash = t("decided_toast", lang, ref=rec.case_ref)
            # keep the decided case open, under "Decided", so the officer sees what was recorded
            st.session_state.staff_filter_next, st.session_state.staff_sel = "decided", rec.case_ref
            st.rerun()
        except ReviewError as e:
            key = {"staff_id": "rv_staff_id", "note": "rv_note", "decided": "rv_decided"}.get(e.code)
            st.error(t(key, lang) if key else t("rv_other", lang, e=str(e)))


def _case_detail(store: CaseStore, rec, lang: str) -> None:
    with st.container(border=True):
        h1, h2 = st.columns([3, 2], vertical_alignment="center")
        h1.markdown(f"<div class='case-ref'>{escape(rec.case_ref)}</div>", unsafe_allow_html=True)
        h2.markdown(f"<div style='text-align:end'>{_pill(rec, lang)}</div>", unsafe_allow_html=True)
        fee = (t("case_fee_paid", lang, r=rec.receipt_id) if rec.receipt_id else t("case_fee_none", lang))
        st.markdown("<div class='kv wide'>"
                    f"<div class='k'>{escape(t('case_student', lang))}</div><div class='v'>{escape(_student(rec.student_ref, lang))}</div>"
                    f"<div class='k'>{escape(t('case_lang', lang))}</div><div class='v'>{escape(t('lang_' + (rec.language or 'en'), lang))}</div>"
                    f"<div class='k'>{escape(t('case_created', lang))}</div><div class='v'>{escape(_when(rec))}</div>"
                    f"<div class='k'>{escape(t('app_fee', lang))}</div><div class='v'>{escape(fee)}</div></div>",
                    unsafe_allow_html=True)
        if rec.status == CaseStatus.PENDING_HUMAN_REVIEW:
            st.markdown(f"<div class='callout warn'><b>{escape(t('case_why', lang))}</b>{_why(rec, lang)}</div>",
                        unsafe_allow_html=True)
        elif rec.status == CaseStatus.SUBMITTED:
            st.markdown(f"<div class='callout ok'><b>{escape(t('case_checks', lang))}</b>"
                        f"<div>{escape(t('all_passed', lang))}. {escape(t('q_ready_sub', lang))}</div></div>",
                        unsafe_allow_html=True)
        else:
            _decided_box(rec, lang)
        if rec.documents:
            heading = t("case_evidence" if rec.escalation_reason else "case_evidence_ok", lang)   # red only if referred
            st.markdown(f"<div class='h5'>{escape(heading)}</div>" + _evidence(rec, lang),
                        unsafe_allow_html=True)
            _documents(rec, lang)
        if rec.escalation_summary:
            # written by the model: shown as plain text and labelled; the officer checks it against the documents
            with st.expander(t("case_summary", lang), icon=":material/smart_toy:"):
                st.text(rec.escalation_summary)
        _timeline(rec, lang)
        if rec.status in TO_DECIDE:
            _decision_form(store, rec, lang)


def _case_list(cases, lang: str) -> str | None:
    """The cases on the left: what needs a decision first, then the decided ones. Returns the selected case."""
    ss = st.session_state
    if "staff_filter_next" in ss:                    # set by a decision, before the control is drawn
        ss.staff_list = ss.pop("staff_filter_next")
    if ss.get("staff_list") not in ("todo", "decided", "all"):
        ss.staff_list = "todo"

    def changed(key: str) -> None:
        if ss.get(key) in ("todo", "decided", "all"):    # pressing the selected one again keeps the list as it is
            ss.staff_list = ss[key]

    k = bind("staff_filter", ss.staff_list)
    st.segmented_control(t("list_show", lang), ["todo", "decided", "all"], format_func=lambda x: t("list_" + x, lang),
                         key=k, on_change=changed, args=(k,), label_visibility="collapsed", width="stretch")
    show = ss.staff_list
    pick = [c for c in cases if show == "all" or (c.status in TO_DECIDE) == (show == "todo")]
    # exceptions first (they need the most thought), then ready cases, newest first within each
    pick.sort(key=lambda c: (c.status != CaseStatus.PENDING_HUMAN_REVIEW, c.status != CaseStatus.SUBMITTED,
                             -int(c.case_ref.split("-")[-1]) if c.case_ref.split("-")[-1].isdigit() else 0))
    if not pick:
        st.info(t("list_empty_" + show, lang), icon=":material/inbox:")
        return None
    refs = [c.case_ref for c in pick]
    if ss.get("staff_sel") not in refs:
        ss.staff_sel = refs[0]
    for c in pick:
        sel = c.case_ref == ss.staff_sel
        with st.container(border=True):
            st.markdown(f"<div class='case-row{' sel' if sel else ''}'><div class='top'><b>{escape(c.case_ref)}</b>"
                        f"{_pill(c, lang)}</div><div>{escape(_student(c.student_ref, lang))}</div>"
                        f"<div class='muted'>{escape(_why_short(c, lang))} · {escape(_when(c))}</div></div>",
                        unsafe_allow_html=True)
            if st.button(t("list_open", lang) if not sel else t("list_opened", lang), key=f"open_{c.case_ref}",
                         width="stretch", type="primary" if sel else "secondary", disabled=sel,
                         icon=":material/chevron_right:" if not sel else ":material/visibility:"):
                ss.staff_sel = c.case_ref
                st.rerun()
    return ss.staff_sel


def _audit(lang: str) -> None:
    st.caption(t("audit_caption", lang))
    sessions = list(reversed(st.session_state.get("session_ids", [])))
    if not sessions:
        st.caption(t("audit_none", lang))
        return
    current = st.session_state.agent.state.session_id if st.session_state.get("agent") else None
    labels = {sid: f"{persona_title(pid, lang)} · {t('lang_' + lg, lang)}"
                   + (f" ({t('this_session', lang)})" if sid == current else "") for sid, pid, lg in sessions}
    sid = st.selectbox(t("audit_pick", lang), [s for s, _, _ in sessions], format_func=labels.get)
    path = Path(LOG_DIR) / f"audit_{sid}.jsonl"
    if not path.exists():
        st.caption(t("audit_none", lang))
        return
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    actors = sorted({e["actor"] for e in events})
    show = st.multiselect(t("audit_actors", lang), actors, default=actors, format_func=lambda a: actor(a, lang))
    rows = [e for e in events if e["actor"] in show]
    st.dataframe(pd.DataFrame([{
        t("au_time", lang): _local(e["ts"]), t("au_who", lang): actor(e["actor"], lang),
        t("au_what", lang): describe(e, lang), t("au_why", lang): e["basis"]} for e in rows]),
        hide_index=True, width="stretch", height=520,
        column_config={t("au_what", lang): st.column_config.TextColumn(width="large"),
                       t("au_why", lang): st.column_config.TextColumn(width="medium")})
    with st.expander(t("au_raw", lang)):
        st.dataframe(pd.DataFrame([{"#": e["seq"], "actor": e["actor"], "event": e["event"], "basis": e["basis"],
                                    "detail": json.dumps(e["detail"], ensure_ascii=False)[:300]} for e in rows]),
                     hide_index=True, width="stretch")
        st.download_button(t("audit_download", lang), path.read_text(encoding="utf-8"), file_name=path.name,
                           icon=":material/download:")


def render(lang: str) -> None:
    store = case_store()
    cases = store.list()
    st.markdown(f"<div class='svc-title' role='heading' aria-level='1'>{escape(t('staff_title', lang))}</div>",
                unsafe_allow_html=True)
    st.caption(f"{t('staff_sub', lang)}  ·  {t('staff_officer', lang)}: {OFFICER}")
    _kpis(cases, lang)
    st.write("")
    work, audit = st.tabs([t("tab_queue", lang), t("tab_audit", lang)])
    with work:
        if not cases:
            st.info(t("cases_none", lang), icon=":material/inbox:")
        else:
            left, right = st.columns([1.05, 2.3], gap="medium")
            with left:
                sel = _case_list(cases, lang)
            with right:
                rec = store.get(sel) if sel else None
                if rec is not None:
                    _case_detail(store, rec, lang)
    with audit:
        _audit(lang)
