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
from ui.session import (FAILURES, PROVIDERS, ai_status, base_settings, config_key, defaults,  # noqa: E402
                        new_session, persona_ids, persona_story, persona_title)
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
        pids = persona_ids()
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
        ss.persona = st.radio(t("dc_applicant", lang), pids, index=pids.index(ss.persona),
                              format_func=lambda p: persona_title(p, lang),
                              captions=[persona_story(p, lang) for p in pids], key="dc_persona")
        ss.provider = st.radio(t("dc_model", lang), PROVIDERS, index=PROVIDERS.index(ss.provider),
                               format_func=lambda p: t("prov_" + p, lang), horizontal=True)
        colour, status = ai_status(ss.provider, lang)
        st.markdown(f"<div class='muted'><span class='dot' style='background:{colour}'></span>{status}</div>",
                    unsafe_allow_html=True)
        b1, b2 = st.columns(2)
        if b1.button(t("dc_check", lang), width="stretch"):
            ai_status.clear()
            st.rerun()
        if ss.provider == "ollama" and b2.button(t("dc_load", lang), width="stretch"):
            from agent.llm import warm_up
            with st.spinner(t("dc_loading", lang)):
                try:
                    warm_up(base_settings)
                except Exception as e:  # noqa: BLE001 - shown to the presenter
                    st.error(str(e))
            ai_status.clear()
            st.rerun()
        fails = list(FAILURES)
        ss.failure = st.selectbox(t("dc_failure", lang), fails, index=fails.index(ss.failure),
                                  format_func=lambda f: t("fail_" + f, lang))
        ss.show_inner = st.toggle(t("dc_inner", lang), value=ss.show_inner)
        if st.button(t("dc_start", lang), type="primary", width="stretch", icon=":material/restart_alt:"):
            new_session()
            st.rerun()
        if ss.get("config") != config_key():
            st.caption(t("dc_changed", lang))

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
