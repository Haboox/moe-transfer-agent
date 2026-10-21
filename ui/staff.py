"""Staff portal: the officer's side. The only place where an escalated case is approved or rejected (Approve).

Decision workflow (D-02): the agent never decides equivalency. The Decisions tab lists the exceptions the rules could
not decide and the submitted cases that passed every automated check; an officer decides both.

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
from agent.human_review import ReviewError, decide
from agent.mocks import CaseStore
from agent.models import CaseStatus
from ui.audit_view import actor, describe
from ui.i18n import reason, t
from ui.session import case_store, catalogue, persona_title

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
    """Log times are UTC; the screen shows this computer's local time (Dubai on the demo laptop)."""
    try:
        return datetime.fromisoformat(ts).astimezone().strftime(fmt)
    except (TypeError, ValueError):
        return ts or ""


def _when(rec) -> str:
    return _local(rec.created_at or "", "%H:%M")


def _kpis(cases, lang: str) -> None:
    counts = [(t("kpi_waiting", lang), sum(c.status == CaseStatus.PENDING_HUMAN_REVIEW for c in cases)),
              (t("kpi_submitted", lang), sum(c.status == CaseStatus.SUBMITTED for c in cases)),
              (t("kpi_decided", lang), sum(c.status in (CaseStatus.HUMAN_APPROVED, CaseStatus.HUMAN_REJECTED)
                                           for c in cases)),
              (t("kpi_total", lang), len(cases))]
    for col, (label, n) in zip(st.columns(4), counts):
        col.markdown(f"<div class='kpi'><div class='n'>{n}</div><div class='l'>{escape(label)}</div></div>",
                     unsafe_allow_html=True)


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


def _decision_form(store: CaseStore, rec, lang: str, ready: bool) -> None:
    a, b = st.columns([1, 2])
    officer = a.text_input(t("officer_id", lang), OFFICER, key=f"o_{rec.case_ref}")
    note = b.text_input(t("decision_note", lang), key=f"n_{rec.case_ref}",
                        placeholder=t("ready_note_ph" if ready else "decision_note_ph", lang))
    x, y, _ = st.columns([1, 1, 3])
    for col, decision, kind, icon in ((x, "approve", "primary", ":material/check:"),
                                      (y, "reject", "secondary", ":material/close:")):
        if col.button(t(decision, lang), key=f"{decision}_{rec.case_ref}", type=kind, width="stretch", icon=icon):
            try:
                decide(store, rec.case_ref, officer, decision, note)
                st.rerun()
            except ReviewError as e:
                st.error(str(e))


def _case_card(store: CaseStore, rec, lang: str, ready: bool) -> None:
    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        c1.markdown(f"#### {rec.case_ref}")
        pill = ("p-green", t("st_SUBMITTED", lang)) if ready else ("p-amber", t("st_PENDING_HUMAN_REVIEW", lang))
        c2.markdown(f"<span class='pill {pill[0]}'>{escape(pill[1])}</span>", unsafe_allow_html=True)
        st.markdown(f"<div class='kv'><div class='k'>{escape(t('case_student', lang))}</div>"
                    f"<div class='v'>{escape(_student(rec.student_ref, lang))}</div>"
                    f"<div class='k'>{escape(t('case_lang', lang))}</div>"
                    f"<div class='v'>{escape(t('lang_' + (rec.language or 'en'), lang))}</div>"
                    f"<div class='k'>{escape(t('case_created', lang))}</div><div class='v'>{escape(_when(rec))}</div></div>",
                    unsafe_allow_html=True)
        if ready:
            st.markdown(f"<div class='h5'>{escape(t('case_checks', lang))}</div>"
                        f"<ul class='why'><li>{escape(t('all_passed', lang))}</li></ul>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='h5'>{escape(t('case_why', lang))}</div>" + _why(rec, lang), unsafe_allow_html=True)
            if rec.escalation_reason == "customer_request" and _parent_words(rec):
                st.markdown(f"<div class='muted'>{escape(t('case_parent_said', lang))}: “{escape(_parent_words(rec))}”</div>",
                            unsafe_allow_html=True)
        if rec.documents:
            st.markdown(f"<div class='h5'>{escape(t('case_evidence', lang))}</div>" + _evidence(rec, lang),
                        unsafe_allow_html=True)
            _files(rec, lang)
        if rec.escalation_summary:
            # written by the model: shown as plain text and labelled; the officer checks it against the documents
            with st.expander(t("case_summary", lang)):
                st.text(rec.escalation_summary)
        _decision_form(store, rec, lang, ready)


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
    return f"<table class='rules evidence'>{head}{''.join(body)}</table>" if body else ""


def _parent_words(rec) -> str:
    """For a case the parent asked to hand over: their own last message (already masked in the log)."""
    path = Path(LOG_DIR) / f"audit_{rec.session_id}.jsonl"
    if not path.exists():
        return ""
    said = [json.loads(x)["detail"].get("text", "") for x in path.read_text(encoding="utf-8").splitlines()
            if x.strip() and '"customer_message"' in x]
    return said[-1].split("\n[")[0] if said else ""


def _files(rec, lang: str) -> None:
    docs = _all_docs()
    have = [d for d in rec.documents if d.get("doc_id") in docs]
    if not have:
        return
    with st.expander(t("case_open_docs", lang), icon=":material/folder_open:"):
        for i, d in enumerate(have):
            dd = docs[d["doc_id"]]
            path = ROOT / dd["path"]
            if path.exists():
                st.download_button(_doc_title(d, dd.get("registry", {}), lang), path.read_bytes(),
                                   file_name=dd["file_name"], key=f"dl_{rec.case_ref}_{i}",
                                   icon=":material/description:")


def _queue(store: CaseStore, lang: str) -> None:
    """Two lists, so the panel sees what the agent did on its own and what only a person decides."""
    st.markdown(f"##### {t('q_review_h', lang)}")
    st.caption(t("q_review_sub", lang))
    pending = store.list(CaseStatus.PENDING_HUMAN_REVIEW)
    if not pending:
        st.info(t("queue_empty", lang), icon=":material/inbox:")
    for rec in pending:
        _case_card(store, rec, lang, ready=False)
    st.write("")
    st.markdown(f"##### {t('q_ready_h', lang)}")
    st.caption(t("q_ready_sub", lang))
    ready = store.list(CaseStatus.SUBMITTED)
    if not ready:
        st.info(t("q_ready_empty", lang), icon=":material/inbox:")
    for rec in ready:
        _case_card(store, rec, lang, ready=True)


def _why_short(c, lang: str) -> str:
    if c.problems:
        return ("؛ " if lang == "ar" else "; ").join((p.get("title_ar") if lang == "ar" else p["title"]) or p["title"]
                                                   for p in c.problems)
    return reason(c.escalation_reason, lang) if c.escalation_reason else t("all_passed", lang)


def _all_cases(store: CaseStore, lang: str) -> None:
    cases = sorted(store.list(), key=lambda c: c.case_ref, reverse=True)
    if not cases:
        st.caption(t("cases_none", lang))
        return
    st.dataframe(pd.DataFrame([{
        t("col_case", lang): c.case_ref,
        t("case_student", lang): _student(c.student_ref, lang),
        t("col_status", lang): t("st_" + c.status.value, lang),
        t("col_why", lang): _why_short(c, lang),
        t("col_officer", lang): " · ".join(x for x in (c.reviewer_id, c.reviewer_note) if x),
        t("col_lang", lang): t("lang_" + (c.language or "en"), lang),
        t("col_created", lang): _when(c)} for c in cases]),
        hide_index=True, width="stretch")


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
    q, a, au = st.tabs([t("tab_queue", lang), t("tab_all", lang), t("tab_audit", lang)])
    with q:
        _queue(store, lang)
    with a:
        _all_cases(store, lang)
    with au:
        _audit(lang)
