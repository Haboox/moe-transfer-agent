"""Session state for the app: which demo is set up, the agent of the current parent session, the chat."""
from __future__ import annotations

import os
from dataclasses import replace

import streamlit as st

from uuid import uuid4

from agent.agent import ServiceAgent
from agent.config import RUNTIME_DIR, get_settings
from agent.llm import LLMError, hosted_status, make_llm, ollama_status
from agent.mocks import OPEN_ID, CaseStore, MockBackend
from ui.i18n import t

FAILURES = {
    "none": None,
    "timeout_once": {"verification": ["timeout"]},
    "error_once": {"verification": ["error"]},
    "malformed": {"verification": "malformed_always"},
    "timeout_always": {"verification": "timeout_always"},
    "identity_down": {"identity": "error_always"},
    "payment_down": {"payment": "error_always"},
    "cases_down": {"cases": "error_always"},
}
base_settings = get_settings()
ONLINE = os.getenv("MOE_ONLINE", "").strip().lower() in ("1", "true", "yes")   # the hosted copy (plan B)


def _providers() -> list[str]:
    """The AI models offered in Demo controls. The online copy has no local model (no graphics card there), and a
    hosted model is offered only when its key is set."""
    out = [] if ONLINE else ["ollama"]
    if base_settings.hosted_api_key or base_settings.llm_provider == "hosted":
        out.append("hosted")
    if base_settings.anthropic_api_key or base_settings.llm_provider == "anthropic":
        out.append("anthropic")
    return out + ["scripted"]


PROVIDERS = _providers()


@st.cache_resource(show_spinner=False)
def catalogue() -> MockBackend:
    """Read-only copy of the synthetic data for the screens (names, document lists)."""
    return MockBackend()


def defaults() -> None:
    ss = st.session_state
    ss.setdefault("lang", "en")
    ss.setdefault("theme", "light")
    ss.setdefault("view", "parent")
    ss.setdefault("persona", OPEN_ID)             # the portal opens on the open test: no preset case
    ss.setdefault("open_nat", None)               # nationality on the mock UAE Pass record in the open test (none yet)
    ss.setdefault("provider", base_settings.llm_provider if base_settings.llm_provider in PROVIDERS else PROVIDERS[0])
    ss.setdefault("failure", "none")
    ss.setdefault("show_inner", False)          # the presenter turns this on in Demo controls
    # One case list per browser visit: the Staff portal shows the cases of THIS demonstration only. Reloading the
    # page starts a clean list (earlier visits stay on disk in runtime/sessions/ and in logs/, never shown again).
    ss.setdefault("store_path", RUNTIME_DIR / "sessions" / f"cases_{uuid4().hex[:12]}.json")
    ss.setdefault("session_ids", [])


def case_store() -> CaseStore:
    return CaseStore(st.session_state.store_path)


def student_name(pid: str, lang: str) -> str:
    s = catalogue().personas[pid]["student"]
    if lang == "ar" and s.get("given_name_ar"):
        return f"{s['given_name_ar']} {s['family_name_ar']}"
    return f"{s['given_name']} {s['family_name']}"


def top_grade(pid: str) -> int:
    certs = [d["registry"]["grade"] for d in catalogue().persona_documents(pid, "en")
             if d["doc_type"] == "school_certificate"]
    return max(certs) if certs else 0


def persona_ids() -> list[str]:
    """The open test first, then the prepared applicants."""
    return [OPEN_ID] + [p for p in catalogue().personas if p != OPEN_ID]


def persona_title(pid: str, lang: str) -> str:
    if pid == OPEN_ID:
        # fixed text: a drop-down option whose label changed with the nationality made Streamlit lose the selection
        return t("open_title", lang)
    s = catalogue().personas[pid]["student"]
    nat = s.get("nationality_ar") if lang == "ar" else s["nationality"]
    g = top_grade(pid)
    grade = (f"الصف {g}" if lang == "ar" else f"Grade {g}")
    return f"{student_name(pid, lang)} · {nat} · {grade}"


def persona_story(pid: str, lang: str) -> str:
    p = catalogue().personas[pid]
    return p.get("story_ar", p["story"]) if lang == "ar" else p["story"]


def new_session() -> None:
    ss = st.session_state
    settings = replace(base_settings, llm_provider=ss.provider)
    try:
        llm = make_llm(settings)
    except LLMError as e:
        ss.flash = f"{ss.provider}: {e}. Using the scripted planner."
        llm = make_llm(replace(settings, llm_provider="scripted"))
    backend = MockBackend(failures=FAILURES[ss.failure], case_store=case_store(),
                          latency_s=settings.mock_latency_seconds, hang_s=settings.mock_hang_seconds,
                          interactive_payments=True, open_nationality=ss.open_nat or "")
    ss.agent = ServiceAgent(llm, ss.persona, backend=backend, settings=settings, ui_lang=ss.lang)
    ss.session_ids.append((ss.agent.state.session_id, ss.persona, ss.lang))
    ss.chat = [{"role": "assistant", "text": t("greeting", ss.lang), "kind": ""}]
    ss.config = config_key()
    for k in ("pending", "busy", "pay_prompted"):
        ss.pop(k, None)


def clear_cases() -> None:
    """Start the demonstration's case list again (an empty staff portal, for example before a recording). The old
    list stays on disk in runtime/sessions/ and its audit logs in logs/; it is only no longer shown."""
    ss = st.session_state
    ss.store_path = RUNTIME_DIR / "sessions" / f"cases_{uuid4().hex[:12]}.json"
    ss.session_ids = []
    ss.pop("staff_sel", None)
    new_session()


def config_key() -> tuple:
    ss = st.session_state
    return (ss.persona, ss.provider, ss.failure, ss.lang, ss.open_nat if ss.persona == OPEN_ID else None)


def send(text: str, uploads: list[str]) -> None:
    """Show the parent's message at once; the assistant answers on the next run (typing indicator)."""
    ss = st.session_state
    if ss.get("pending") or ss.get("busy"):
        ss.flash = t("wait_answer", ss.lang)      # one turn at a time: the parent is told, nothing is lost silently
        return
    from ui.i18n import doc_label
    docs = ss.agent.backend.documents if ss.get("agent") else catalogue().documents
    names = [doc_label(docs[u], ss.lang) for u in uploads if u in docs]
    shown = text + (("\n\n" + t("attached", ss.lang) + ": " + "، ".join(names) if ss.lang == "ar"
                     else "\n\n" + t("attached", ss.lang) + ": " + ", ".join(names)) if names else "")
    last = ss.chat[-1] if ss.chat else None
    if last and last["role"] == "user" and last["text"] == shown:
        return                                   # same message twice in a row, not yet answered
    ss.chat.append({"role": "user", "text": shown, "kind": ""})
    ss.pending = (text, uploads)


@st.cache_data(ttl=8, show_spinner=False)
def ai_status(provider: str, lang: str) -> tuple[str, str]:
    """(colour, text) for the demo controls."""
    m = base_settings.ollama_model
    if provider == "scripted":
        return "#1E7A46", t("ai_ready_scripted", lang)
    if provider == "anthropic":
        return ("#1E7A46", t("ai_key_ok", lang)) if base_settings.anthropic_api_key else ("#B42318", t("ai_no_key", lang))
    if provider == "hosted":
        g = hosted_status(base_settings)
        if not g["key"]:
            return "#B42318", t("ai_no_key", lang)
        if not g["ok"]:
            return "#B42318", t("ai_hosted_down", lang, d=g["detail"])
        if not g["model_listed"]:
            return "#B42318", t("ai_not_offered", lang, m=base_settings.hosted_model)
        return "#1E7A46", t("ai_ready", lang, m=base_settings.hosted_model)
    s = ollama_status(base_settings)
    if not s["running"]:
        return "#B42318", t("ai_not_running", lang)
    if not s["model_downloaded"]:
        return "#B42318", t("ai_not_downloaded", lang, m=m)
    if not s["model_loaded"]:
        return "#C08A00", t("ai_not_loaded", lang, m=m)
    return "#1E7A46", t("ai_ready", lang, m=m)
