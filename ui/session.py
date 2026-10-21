"""Session state for the app: which demo is set up, the agent of the current parent session, the chat."""
from __future__ import annotations

import json
import os
import re
from dataclasses import replace
from datetime import datetime

import streamlit as st

from uuid import uuid4

from agent.agent import ServiceAgent
from agent.config import RUNTIME_DIR, get_settings
from agent.facts import UAE
from agent.llm import LLMError, hosted_status, make_llm, ollama_status
from agent.mocks import OPEN_ID, CaseStore, MockBackend
from ui.i18n import t

# A Ministry system problem to simulate (Demo controls, section 3). Every mocked system can fail in the three ways
# the case study names (a timeout, a server error, a bad response), once (the retry recovers) or every time.
SYSTEMS = ["verification", "identity", "payment", "cases"]
MODES = ["timeout_once", "error_once", "malformed_once", "timeout_always", "error_always", "malformed_always"]


def _plan(system: str, mode: str) -> dict:
    kind, when = mode.rsplit("_", 1)
    return {system: [kind] if when == "once" else f"{kind}_always"}


FAILURES = {"none": None} | {f"{sy}:{m}": _plan(sy, m) for sy in SYSTEMS for m in MODES}

# Picking a test situation sets the system problem that goes with it (Scenario 5 of the case study: a backend
# failure, timeout or bad response). Every other situation starts with all systems working.
SCENARIO_FAILURE = {"SYN-P05": "verification:timeout_once"}
# The one-click problems offered right under Scenario 5 (any system and problem can still be picked in section 3)
S5_PICKS = [f"verification:{m}" for m in MODES]
# The case study's six mandatory scenarios, by their names in the brief (the other situations are extras)
MANDATORY = {f"SYN-P0{n}": n for n in range(1, 7)}


def fail_parts(key: str) -> tuple[str, str]:
    """("none", "") or (system, mode)."""
    return tuple(key.split(":", 1)) if ":" in (key or "") else ("none", "")


def fail_label(key: str, lang: str) -> str:
    system, mode = fail_parts(key)
    if system == "none":
        return t("fail_none", lang)
    return f"{t('sys_' + system, lang)}: {t('mode_' + mode, lang)}"


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
    # last: a simulated compromised model (it obeys the injection), to demonstrate that the guard holds anyway
    return out + ["scripted", "adversarial"]


PROVIDERS = _providers()


@st.cache_resource(show_spinner=False)
def catalogue() -> MockBackend:
    """Read-only copy of the synthetic data for the screens (names, document lists)."""
    return MockBackend()


def _url(name: str) -> str | None:
    try:
        return st.query_params.get(name)
    except Exception:  # noqa: BLE001 - no page address (bare run)
        return None


def _sessions_file(store_path) -> "os.PathLike":
    return store_path.with_name(store_path.stem + "_sessions.json")


def _remember_sessions() -> None:
    """The parent sessions of this demonstration (for the staff portal's audit trail), kept beside its case list."""
    ss = st.session_state
    try:
        f = _sessions_file(ss.store_path)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(ss.session_ids), encoding="utf-8")
    except OSError:
        pass                                    # the audit trail list is a convenience; the logs themselves are kept


def defaults() -> None:
    ss = st.session_state
    if "store_path" not in ss:
        # First run of this browser visit, or the page was reloaded. The page address carries the demonstration
        # (?run=...&lang=...&theme=...), so a reload keeps the staff portal's cases, the language and the look
        # (found 22 October: a reload in the middle of a demonstration emptied the staff portal). The parent's chat
        # starts again; the cases and their audit trails stay. "Clear all cases" starts a new run.
        run = _url("run")
        run = run if run and re.fullmatch(r"[0-9a-f]{12}", run) else uuid4().hex[:12]
        ss.store_path = RUNTIME_DIR / "sessions" / f"cases_{run}.json"
        try:
            ss.session_ids = [tuple(x) for x in json.loads(_sessions_file(ss.store_path).read_text(encoding="utf-8"))]
        except (OSError, ValueError, TypeError):
            ss.session_ids = []
        ss.lang = _url("lang") if _url("lang") in ("en", "ar") else "en"
        ss.theme = _url("theme") if _url("theme") in ("light", "dark") else "light"
    ss.setdefault("lang", "en")
    ss.setdefault("theme", "light")
    ss.setdefault("view", "parent")
    ss.setdefault("persona", OPEN_ID)             # the portal opens on the open test: no preset case
    ss.setdefault("open_nat", None)               # nationality on the mock UAE Pass record in the open test (none yet)
    ss.setdefault("provider", base_settings.llm_provider if base_settings.llm_provider in PROVIDERS[:-1] else PROVIDERS[0])
    ss.setdefault("failure", "none")
    ss.setdefault("show_inner", False)          # the presenter turns this on in Demo controls
    ss.setdefault("ui_epoch", 0)                # counts language switches (fresh widget keys each time, see wkey)
    ss.setdefault("staff_list", "todo")         # which cases the staff portal lists
    # One case list per demonstration: the Staff portal shows the cases of THIS demonstration only (a new browser
    # visit without the address of an earlier one starts a clean list; earlier lists stay on disk, never shown).
    keep_address()


def keep_address() -> None:
    """Writes the demonstration into the page address (no reload), so reloading the page comes back to it."""
    ss = st.session_state
    want = {"run": ss.store_path.stem.removeprefix("cases_"), "lang": ss.lang, "theme": ss.theme}
    try:
        for k, v in want.items():
            if st.query_params.get(k) != v:
                st.query_params[k] = v
    except Exception:  # noqa: BLE001 - no page address (bare run)
        pass


def turn_flags() -> dict:
    """{"pending": the parent's message waiting for an answer, "busy": True while the assistant answers}. A plain
    dict kept in the session, so a turn can take the message and finish without touching st.session_state
    (see ui/parent.py, _chat)."""
    return st.session_state.setdefault("turn_flags", {"busy": False, "pending": None})


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
    """The situation's name in Demo controls: the six mandatory scenarios carry the brief's own names."""
    if pid in MANDATORY:
        n = MANDATORY[pid]
        return t("cs_label", lang, n=n, x=t(f"cs_{n}", lang))
    p = catalogue().personas[pid]
    return p.get("story_ar", p["story"]) if lang == "ar" else p["story"]


def persona_detail(pid: str, lang: str) -> str:
    """The line under each situation: what this synthetic case contains, and who the applicant is."""
    if pid == OPEN_ID:
        return t("open_title", lang)
    p = catalogue().personas[pid]
    story = p.get("story_ar", p["story"]) if lang == "ar" else p["story"]
    what = story.split(":", 1)[1].strip() if pid in MANDATORY and ":" in story else ""
    return (what[:1].upper() + what[1:] + " · " if what else "") + persona_title(pid, lang)


def wkey(name: str) -> str:
    """Key of a widget whose labels change with the page language. Streamlit keeps a keyed choice as its label
    text, so after a language switch the old label matches nothing (found 22 October: the English label "None"
    came back as the chosen problem and crashed the restart). Each language visit gets fresh widget keys, and the
    widget is filled from the session's own value (bind)."""
    ss = st.session_state
    return f"{name}__{ss.get('lang', 'en')}{ss.get('ui_epoch', 0)}"


def bind(name: str, value) -> str:
    """Fills a language-keyed widget from the session's value, before the widget is drawn. Returns its key."""
    k = wkey(name)
    st.session_state[k] = value
    return k


def valid_setup() -> None:
    """Every setting the session starts from is one the app offers. Found 22 October: switching the page language
    could leave a stale Demo controls value ("None") that crashed the restart; a bad value now falls back."""
    ss = st.session_state
    if ss.get("persona") not in catalogue().personas:
        ss.persona = OPEN_ID
    if ss.get("provider") not in PROVIDERS:
        ss.provider = base_settings.llm_provider if base_settings.llm_provider in PROVIDERS[:-1] else PROVIDERS[0]
    if ss.get("failure") not in FAILURES:
        ss.failure = "none"
    if ss.get("lang") not in ("en", "ar"):
        ss.lang = "en"


def new_session() -> None:
    ss = st.session_state
    valid_setup()
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
    _remember_sessions()
    ss.chat = [{"role": "assistant", "text": t("greeting", ss.lang), "kind": ""}]
    ss.config = config_key()
    ss.pop("pay_prompted", None)
    ss.turn_flags = {"busy": False, "pending": None}


def clear_cases() -> None:
    """Start the demonstration's case list again (an empty staff portal, for example before a recording). The old
    list stays on disk in runtime/sessions/ and its audit logs in logs/; it is only no longer shown."""
    ss = st.session_state
    ss.store_path = RUNTIME_DIR / "sessions" / f"cases_{uuid4().hex[:12]}.json"
    ss.session_ids = []
    ss.pop("staff_sel", None)
    new_session()
    keep_address()


def config_key() -> tuple:
    ss = st.session_state
    return (ss.persona, ss.provider, ss.failure, ss.lang, ss.open_nat if ss.persona == OPEN_ID else None)


def send(text: str, uploads: list[str]) -> None:
    """Show the parent's message at once; the assistant answers on the next run (typing indicator)."""
    ss = st.session_state
    flags = turn_flags()
    if flags.get("pending") or flags["busy"]:
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
    flags["pending"] = (text, uploads)


@st.cache_data(ttl=60, show_spinner=False)
def _hosted_probe() -> dict:
    """The hosted model's allowance, asked at most once a minute (each check is a one-token request)."""
    return hosted_status(base_settings)


def refresh_ai_status() -> None:
    """"Check again" in Demo controls: ask the AI service now instead of using the last minute's answer."""
    ai_status.clear()
    _hosted_probe.clear()


@st.cache_data(ttl=8, show_spinner=False)
def ai_status(provider: str, lang: str) -> tuple[str, str]:
    """(colour, text) for the demo controls."""
    m = base_settings.ollama_model
    if provider == "scripted":
        return "#1E7A46", t("ai_ready_scripted", lang)
    if provider == "adversarial":
        return "#C08A00", t("ai_adversarial", lang)
    if provider == "anthropic":
        return ("#1E7A46", t("ai_key_ok", lang)) if base_settings.anthropic_api_key else ("#B42318", t("ai_no_key", lang))
    if provider == "hosted":
        g = _hosted_probe()
        if not g["key"]:
            return "#B42318", t("ai_no_key", lang)
        if not g["ok"]:
            return "#B42318", t("ai_hosted_down", lang, d=g["detail"])
        if not g["model_listed"]:
            return "#B42318", t("ai_not_offered", lang, m=base_settings.hosted_model)
        if not g["active"]:
            back = datetime.fromtimestamp(g["back_at"], UAE).strftime("%H:%M") if g["back_at"] else "?"
            return "#C08A00", t("ai_paused", lang, t=back)
        left = t("ai_left", lang, n=g["requests_left"]) if g["requests_left"] is not None else ""
        if g["active"] != base_settings.hosted_model:
            return "#C08A00", t("ai_on_fallback", lang, m=g["active"]) + left
        return "#1E7A46", t("ai_ready", lang, m=g["active"]) + left
    s = ollama_status(base_settings)
    if not s["running"]:
        return "#B42318", t("ai_not_running", lang)
    if not s["model_downloaded"]:
        return "#B42318", t("ai_not_downloaded", lang, m=m)
    if not s["model_loaded"]:
        return "#C08A00", t("ai_not_loaded", lang, m=m)
    return "#1E7A46", t("ai_ready", lang, m=m)
