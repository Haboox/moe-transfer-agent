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
from ui.session import (FAILURES, PROVIDERS, ai_status, base_settings, clear_cases, defaults,  # noqa: E402
                        new_session, persona_ids, persona_story, persona_title, refresh_ai_status)
from ui.theme import apply_streamlit_theme, css, logo_data_uri  # noqa: E402

st.set_page_config(page_title="MoE | Equivalency Assistant (Prototype)", page_icon="assets/moe-favicon.png",
                   layout="wide", initial_sidebar_state="collapsed")
defaults()
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
    ss.lang = "en" if ss.lang == "ar" else "ar"
    new_session()                                # the portal reopens in the other language, with that edition's documents
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
    choice = st.segmented_control("view", ["parent", "staff"], default=ss.view, label_visibility="collapsed",
                                  format_func=lambda v: t("view_" + v, lang), key="view_pick", width="stretch")
    if choice and choice != ss.view:
        ss.view = choice
        st.rerun()
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

        def apply_now(what: str) -> None:
            """Every choice here applies at once: the demonstration restarts with it (no extra button press)."""
            ss.persona = ss.get("dc_persona", ss.persona)
            ss.provider = ss.get("dc_provider", ss.provider)
            ss.failure = ss.get("dc_failure", ss.failure)
            new_session()
            label = {"persona": persona_story(ss.persona, lang), "provider": t("prov_" + ss.provider, lang),
                     "failure": t("fail_" + ss.failure, lang)}[what]
            ss.flash = t("dc_applied", lang, x=label)

        # 1. the test situation: what is tested first, who the applicant is underneath
        st.markdown(f"<div class='h5'>1 · {escape(t('dc_applicant', lang))}</div>", unsafe_allow_html=True)
        # The open test's nationality comes first (it is the default test), so it is never pushed below the list.
        if ss.get("dc_persona", ss.persona) == OPEN_ID:
            nats = names(lang)

            def nationality_changed() -> None:
                # Applied at once: the open test restarts with the new UAE Pass record, and the document library
                # switches to the applicant with that nationality (ui/parent.py)
                ss.open_nat = ss.dc_open_nat
                if ss.persona == OPEN_ID:
                    new_session()
                    ss.flash = t("nat_applied", lang, n=shown(ss.open_nat, lang) if ss.open_nat else "-")

            ss.open_nat = st.selectbox(t("dc_open_nat", lang), nats,
                                       index=nats.index(ss.open_nat) if ss.open_nat in nats else None,
                                       placeholder=t("dc_open_nat_ph", lang), format_func=lambda n: shown(n, lang),
                                       help=t("dc_open_nat_help", lang), key="dc_open_nat",
                                       on_change=nationality_changed)
            if not ss.open_nat:
                st.caption(t("dc_open_nat_none", lang))
        # A list, not a drop-down: every test situation is readable in full without opening anything
        st.radio(t("dc_applicant", lang), pids, index=pids.index(ss.persona), label_visibility="collapsed",
                 format_func=lambda p: persona_story(p, lang),
                 captions=[persona_title(p, lang) for p in pids], key="dc_persona",
                 on_change=apply_now, args=("persona",))

        # 2. the AI model
        st.markdown(f"<div class='h5'>2 · {escape(t('dc_model', lang))}</div>", unsafe_allow_html=True)
        st.radio(t("dc_model", lang), PROVIDERS, index=PROVIDERS.index(ss.provider), label_visibility="collapsed",
                 format_func=lambda p: t("prov_" + p, lang), horizontal=True, key="dc_provider",
                 on_change=apply_now, args=("provider",))
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

        # 3. a Ministry system problem, and how much of the agent's work to show
        st.markdown(f"<div class='h5'>3 · {escape(t('dc_failure', lang))}</div>", unsafe_allow_html=True)
        fails = list(FAILURES)
        st.selectbox(t("dc_failure", lang), fails, index=fails.index(ss.failure), label_visibility="collapsed",
                     format_func=lambda f: t("fail_" + f, lang), key="dc_failure",
                     on_change=apply_now, args=("failure",))
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
