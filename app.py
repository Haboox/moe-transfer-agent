"""Class Transfer Equivalency: prototype portal (Streamlit).

Run:  double-click run_app.bat   (or: streamlit run app.py)  ->  http://localhost:8501

Top bar (one click each):
  Parent portal | Staff portal    the parent's service page, or the officer's case screen
  عربي | English                  page language; the assistant replies in the language the parent writes in
  Light | Dark                    light mode follows the moe.gov.ae service page; dark mode for presenting
  Demo controls                   not part of a real portal: which synthetic parent is signed in, which AI
                                  model runs, which system failure to simulate, and the "how it decided" panels
"""
import hmac
import os
from html import escape

import streamlit as st


def _secrets_to_env() -> None:
    """Online (Streamlit Community Cloud) the settings come from the app's Secrets box instead of .env.
    Copied into the environment BEFORE the agent reads its settings. Locally there is no secrets file: .env is used."""
    try:
        items = dict(st.secrets)
    except Exception:  # noqa: BLE001 - no secrets file when running locally
        return
    for key, value in items.items():
        if isinstance(value, (str, int, float, bool)):
            os.environ.setdefault(key, str(value))


_secrets_to_env()

from ui import parent, staff  # noqa: E402  (after the settings are in place)
from ui.i18n import t  # noqa: E402
from agent.countries import names, shown  # noqa: E402
from agent.mocks import OPEN_ID  # noqa: E402
from ui.session import (MODES, PROVIDERS, S5_PICKS, SCENARIO_FAILURE, SYSTEMS, ai_status, base_settings,  # noqa: E402
                        bind, clear_cases, defaults, fail_label, fail_parts, new_session, persona_detail,
                        persona_ids, persona_story, refresh_ai_status, turn_flags, valid_setup)
from ui.theme import apply_streamlit_theme, css, logo_data_uri  # noqa: E402

st.set_page_config(page_title="MoE | Equivalency Assistant (Prototype)", page_icon="assets/moe-favicon.png",
                   layout="wide", initial_sidebar_state="collapsed")
defaults()
valid_setup()                                    # every setting is one the app offers (a stale value falls back)
ss = st.session_state


def _access_gate() -> None:
    """Online copy only: an access code (APP_PASSCODE in the app's secrets) in front of the whole portal, on top of
    Streamlit's own viewer list. Compared in constant time; five wrong tries lock this browser session."""
    code = os.getenv("APP_PASSCODE", "")
    if not code or ss.get("unlocked"):
        return
    ss.setdefault("gate_tries", 0)
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.markdown("### Equivalency Assistant (Prototype) · مساعد المعادلة (نموذج أولي)")
        st.caption("Synthetic data only. Enter the access code you were given. "
                   "بيانات اصطناعية فقط. أدخل رمز الدخول الذي حصلت عليه.")
        if ss.gate_tries >= 5:
            st.error("Too many attempts. Close this tab and try again later. محاولات كثيرة، أعد المحاولة لاحقاً.")
            st.stop()
        with st.form("gate"):
            entered = st.text_input("Access code · رمز الدخول", type="password")
            if st.form_submit_button("Open · فتح", width="stretch"):
                if hmac.compare_digest(entered.strip().encode(), code.encode()):
                    ss.unlocked = True
                    st.rerun()
                ss.gate_tries += 1
                st.error("Wrong code. الرمز غير صحيح.")
    st.stop()


_access_gate()
lang, theme = ss.lang, ss.theme

if apply_streamlit_theme(theme, lang):
    st.rerun()                                   # the new theme reaches the browser on the next run
st.markdown(css(theme, lang), unsafe_allow_html=True)
if "agent" not in ss:
    new_session()


def switch_language() -> None:
    """The page switches language. A request already under way continues (conversation, documents, payment and
    case are kept; the assistant follows the language the parent writes in). A page with nothing done yet simply
    reopens in the other language."""
    ss.lang = "en" if ss.lang == "ar" else "ar"
    ss.ui_epoch = ss.get("ui_epoch", 0) + 1          # fresh widget keys for the new language (ui/session.py, wkey)
    agent = ss.get("agent")
    underway = agent is not None and (agent.state.turn > 0 or agent.state.uploads or turn_flags().get("pending")
                                      or len(ss.get("chat", [])) > 1)
    if underway:
        agent.set_portal_language(ss.lang)
        ss.flash = t("lang_kept", ss.lang, l=t("lang_" + ss.lang, ss.lang))
    else:
        new_session()
        ss.flash = t("new_session_toast", ss.lang, l=t("lang_" + ss.lang, ss.lang))


def switch_theme() -> None:
    ss.theme = "dark" if ss.theme == "light" else "light"


# ------------------------------------------------------------------ header (as on moe.gov.ae)
st.markdown("<div class='goldbar'></div>", unsafe_allow_html=True)
h_brand, h_view, h_lang, h_theme = st.columns([5, 3, 1, 1], vertical_alignment="center")
with h_brand:
    st.markdown(f"<div class='brand'><img src='{logo_data_uri(lang)}' alt='{t('ministry', lang)}'>"
                f"<div class='sep'></div><div class='svc'>{t('page_title', lang)}</div></div>",
                unsafe_allow_html=True)
with h_view:
    def view_changed(key: str) -> None:
        if ss.get(key) in ("parent", "staff"):       # pressing the selected one again leaves the view as it is
            ss.view = ss[key]

    k_view = bind("view_pick", ss.view)
    st.segmented_control("view", ["parent", "staff"], label_visibility="collapsed", key=k_view, width="stretch",
                         format_func=lambda v: t("view_" + v, lang), on_change=view_changed, args=(k_view,))
with h_lang:
    st.button(t("other_lang", lang), on_click=switch_language, width="stretch", key="lang_btn",
              icon=":material/translate:")
with h_theme:
    st.button("", on_click=switch_theme, width="stretch", key="theme_btn",
              icon=":material/dark_mode:" if theme == "light" else ":material/light_mode:",
              help=t("theme_dark" if theme == "light" else "theme_light", lang))

# ------------------------------------------------------------------ demo ribbon and controls
r_text, r_ctrl = st.columns([5, 1], vertical_alignment="center")
with r_text:
    st.markdown(f"<div class='demo-ribbon'><span class='tag'>{t('demo_ribbon', lang)}</span>"
                f"<span>{t('demo_text', lang)}</span></div>", unsafe_allow_html=True)
with r_ctrl:
    with st.popover(t("demo_controls", lang), icon=":material/tune:", width="stretch"):
        st.markdown(f"**{t('dc_title', lang)}**")
        st.caption(t("dc_howto", lang))
        pids = persona_ids()

        def apply_now(what: str, key: str) -> None:
            """Every choice here applies at once: the demonstration restarts with it (no extra button press).
            Only a value the app offers is taken; anything else (a stale or empty widget value) changes nothing."""
            v = ss.get(key)
            if what == "persona" and v in pids:
                ss.persona = v
                ss.failure = SCENARIO_FAILURE.get(v, "none")     # each situation starts with its own setup
            elif what == "provider" and v in PROVIDERS:
                ss.provider = v
                if v == "adversarial":
                    ss.show_inner = True             # an attack test is only worth running with the trace in view
            elif what == "system" and v in ["none"] + SYSTEMS:
                ss.failure = "none" if v == "none" else f"{v}:{fail_parts(ss.failure)[1] or MODES[0]}"
            elif what == "mode" and v in MODES and fail_parts(ss.failure)[0] != "none":
                ss.failure = f"{fail_parts(ss.failure)[0]}:{v}"
            elif what == "s5" and v in S5_PICKS:
                ss.failure = v
            else:
                return
            new_session()
            label = {"persona": persona_story(ss.persona, lang), "provider": t("prov_" + ss.provider, lang)}.get(
                what, fail_label(ss.failure, lang))
            if what == "persona" and ss.failure != "none":
                label += " · " + fail_label(ss.failure, lang)
            ss.flash = t("dc_applied", lang, x=label)

        # 1. the test situation. What is running now comes first (how to show it, and its own settings), so it is
        # never pushed below the list of situations.
        st.markdown(f"<div class='h5'>1 · {escape(t('dc_applicant', lang))}</div>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(f"**{escape(t('open_title', lang) if ss.persona == OPEN_ID else persona_story(ss.persona, lang))}**")
            how = {"SYN-P01": "how_p01", "SYN-P02": "how_p02", "SYN-P03": "how_p03", "SYN-P04": "how_p04",
                   "SYN-P05": "how_p05", "SYN-P06": "how_p06", OPEN_ID: "how_open"}.get(ss.persona, "how_other")
            st.caption(f"{t('how_h', lang)}: {t(how, lang)}")
            if ss.persona == "SYN-P05":
                # Scenario 5 of the brief: the backend problem is chosen right here, one click, applied at once
                k = bind("dc_s5", ss.failure if ss.failure in S5_PICKS else None)
                st.pills(t("s5_pick", lang), S5_PICKS, key=k, selection_mode="single",
                         format_func=lambda f: t("mode_" + fail_parts(f)[1], lang), on_change=apply_now,
                         args=("s5", k))
                st.caption(t("s5_note", lang))
            if ss.persona == OPEN_ID:
                nats = names(lang)

                def nationality_changed(key: str) -> None:
                    # Applied at once: the open test restarts with the new UAE Pass record, and the document library
                    # switches to the applicant with that nationality (ui/parent.py)
                    v = ss.get(key)
                    if v is not None and v not in nats:
                        return
                    ss.open_nat = v
                    new_session()
                    ss.flash = t("nat_applied", lang, n=shown(ss.open_nat, lang) if ss.open_nat else "-")

                k = bind("dc_open_nat", ss.open_nat if ss.open_nat in nats else None)
                st.selectbox(t("dc_open_nat", lang), nats, index=None, placeholder=t("dc_open_nat_ph", lang),
                             format_func=lambda n: shown(n, lang), help=t("dc_open_nat_help", lang), key=k,
                             on_change=nationality_changed, args=(k,))
                if not ss.open_nat:
                    st.caption(t("dc_open_nat_none", lang))
        # A list, not a drop-down: every test situation is readable in full without opening anything
        k = bind("dc_persona", ss.persona)
        st.radio(t("dc_applicant", lang), pids, label_visibility="collapsed",
                 format_func=lambda p: persona_story(p, lang), captions=[persona_detail(p, lang) for p in pids],
                 key=k, on_change=apply_now, args=("persona", k))

        # 2. the AI model
        st.markdown(f"<div class='h5'>2 · {escape(t('dc_model', lang))}</div>", unsafe_allow_html=True)
        k = bind("dc_provider", ss.provider)
        st.radio(t("dc_model", lang), PROVIDERS, label_visibility="collapsed",
                 format_func=lambda p: t("prov_" + p, lang), horizontal=True, key=k,
                 on_change=apply_now, args=("provider", k))
        colour, status = ai_status(ss.provider, lang)
        c1, c2 = st.columns([3, 2], vertical_alignment="center")
        c1.markdown(f"<div class='muted'><span class='dot' style='background:{colour}'></span>{status}</div>",
                    unsafe_allow_html=True)
        if c2.button(t("dc_check", lang), width="stretch", type="tertiary", icon=":material/refresh:"):
            refresh_ai_status()
            st.rerun()
        if ss.provider == "ollama" and st.button(t("dc_load", lang), width="stretch"):
            from agent.llm import warm_up
            with st.spinner(t("dc_loading", lang)):
                try:
                    warm_up(base_settings)
                except Exception as e:  # noqa: BLE001 - shown to the presenter
                    st.error(str(e))
            ai_status.clear()
            st.rerun()

        # 3. a Ministry system problem (any mocked system; a timeout, a server error or a bad response; once, so the
        # retry recovers, or every time), and how much of the agent's work to show
        st.markdown(f"<div class='h5'>3 · {escape(t('dc_failure', lang))}</div>", unsafe_allow_html=True)
        system, mode = fail_parts(ss.failure)
        f1, f2 = st.columns(2)
        k = bind("dc_fsys", system)
        f1.selectbox(t("dc_fsys", lang), ["none"] + SYSTEMS, key=k, on_change=apply_now, args=("system", k),
                     format_func=lambda x: t("fail_none" if x == "none" else "sys_" + x, lang))
        k = bind("dc_fmode", mode or MODES[0])
        f2.selectbox(t("dc_fmode", lang), MODES, key=k, on_change=apply_now, args=("mode", k),
                     format_func=lambda x: t("mode_" + x, lang), disabled=system == "none")
        ss.show_inner = st.toggle(t("dc_inner", lang), value=ss.show_inner, help=t("dc_inner_help", lang))

        st.divider()
        r1, r2 = st.columns(2)
        if r1.button(t("dc_start", lang), type="primary", width="stretch", icon=":material/restart_alt:",
                     help=t("dc_start_help", lang)):
            new_session()
            ss.flash = t("dc_restarted", lang)
            st.rerun()
        if r2.button(t("dc_clear", lang), width="stretch", icon=":material/delete_sweep:", help=t("dc_clear_help", lang)):
            clear_cases()
            ss.flash = t("dc_cleared", lang)
            st.rerun()
        with st.expander(t("dc_guide", lang), icon=":material/help:"):
            st.markdown(t("dc_guide_body", lang))

if ss.get("flash"):
    st.toast(ss.pop("flash"))

# ------------------------------------------------------------------ page
if ss.view == "parent":
    st.markdown(f"<div class='crumbs'><a>{t('home', lang)}</a><span class='chev'>{'‹' if lang == 'ar' else '›'}</span>"
                f"<a>{t('services', lang)}</a><span class='chev'>{'‹' if lang == 'ar' else '›'}</span>"
                f"{t('page_title', lang)}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='svc-title' role='heading' aria-level='1'>{t('service_title', lang)}</div>",
                unsafe_allow_html=True)
    parent.render(lang)
else:
    staff.render(lang)

st.markdown(f"<div class='footer'>{t('footer', lang)}</div>", unsafe_allow_html=True)
