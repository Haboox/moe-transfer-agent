"""Light (MoE website look) and dark themes, and the page direction for Arabic.

Light mode follows the published service page on moe.gov.ae: white page, thin gold bar at the top,
the Ministry logo, gold buttons, black headings, light grey card borders. Gold is taken from the
logo itself (#B68A35); buttons use a slightly darker gold so white text stays readable.
Streamlit's own theme (widgets) is switched at runtime, and our CSS uses the same colour tokens.
"""
from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

import streamlit as st

ASSETS = Path(__file__).resolve().parent.parent / "assets"

THEMES = {
    "light": dict(base="light", bg="#FFFFFF", bg2="#F7F5F0", card="#FFFFFF", text="#1B1D21", muted="#5F6670",
                  border="#E3E1DB", gold="#92722A", gold_logo="#B68A35", goldsoft="#F8F3E8", user_bubble="#F3EEE2",
                  ok="#1E7A46", okbg="#E7F5EC", warn="#8A5A00", warnbg="#FFF4D6", info="#1F5FA8", infobg="#E8F0FB",
                  bad="#B42318", badbg="#FDECEA", chip="#F1EFE9", shadow="0 1px 2px rgba(16,24,40,.06)"),
    "dark": dict(base="dark", bg="#0F1216", bg2="#161A20", card="#161A20", text="#E9E5DC", muted="#9AA3AE",
                 border="#2A2F37", gold="#C9A24D", gold_logo="#C9A24D", goldsoft="#221C10", user_bubble="#1E2229",
                 ok="#7EE2A0", okbg="#12301D", warn="#F2C66D", warnbg="#33270F", info="#8CC0FF", infobg="#132842",
                 bad="#F3A69C", badbg="#3A1714", chip="#1F242B", shadow="none"),
}
FONTS = {"en": "Inter, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
         "ar": "'Noto Kufi Arabic', Inter, 'Segoe UI', Tahoma, Arial, sans-serif"}


def apply_streamlit_theme(theme: str, lang: str) -> bool:
    """Set Streamlit's theme options. Returns True if they changed (the caller reruns once to show them)."""
    key = (theme, lang)
    if st.session_state.get("_applied_theme") == key:
        return False
    c = THEMES[theme]
    for opt, val in (("theme.base", c["base"]), ("theme.primaryColor", c["gold"]),
                     ("theme.backgroundColor", c["bg"]), ("theme.secondaryBackgroundColor", c["bg2"]),
                     ("theme.textColor", c["text"]), ("theme.borderColor", c["border"]),
                     ("theme.linkColor", c["gold"]), ("theme.baseRadius", "10px"), ("theme.font", FONTS[lang])):
        try:
            st._config.set_option(opt, val)
        except Exception:  # noqa: BLE001 - an option missing in another Streamlit version is not fatal
            pass
    st.session_state["_applied_theme"] = key
    return True


@lru_cache(maxsize=4)
def logo_data_uri(lang: str) -> str:
    svg = (ASSETS / f"moe-logo-{'ar' if lang == 'ar' else 'en'}.svg").read_bytes()
    return "data:image/svg+xml;base64," + base64.b64encode(svg).decode()


def css(theme: str, lang: str) -> str:
    c = THEMES[theme]
    rtl = lang == "ar"
    direction = "rtl" if rtl else "ltr"
    start = "right" if rtl else "left"
    return f"""
<style>
/* Fonts are bundled in static/fonts (SIL Open Font License), so the app works offline */
@font-face {{ font-family:'Inter'; font-weight:400; font-display:swap; src:url('app/static/fonts/inter-latin-400-normal.woff2') format('woff2'); }}
@font-face {{ font-family:'Inter'; font-weight:600; font-display:swap; src:url('app/static/fonts/inter-latin-600-normal.woff2') format('woff2'); }}
@font-face {{ font-family:'Inter'; font-weight:700; font-display:swap; src:url('app/static/fonts/inter-latin-700-normal.woff2') format('woff2'); }}
@font-face {{ font-family:'Noto Kufi Arabic'; font-weight:400; font-display:swap; src:url('app/static/fonts/noto-kufi-arabic-arabic-400-normal.woff2') format('woff2'); unicode-range:U+0600-06FF,U+0750-077F,U+08A0-08FF,U+FB50-FDFF,U+FE70-FEFF; }}
@font-face {{ font-family:'Noto Kufi Arabic'; font-weight:600; font-display:swap; src:url('app/static/fonts/noto-kufi-arabic-arabic-600-normal.woff2') format('woff2'); unicode-range:U+0600-06FF,U+0750-077F,U+08A0-08FF,U+FB50-FDFF,U+FE70-FEFF; }}
@font-face {{ font-family:'Noto Kufi Arabic'; font-weight:700; font-display:swap; src:url('app/static/fonts/noto-kufi-arabic-arabic-700-normal.woff2') format('woff2'); unicode-range:U+0600-06FF,U+0750-077F,U+08A0-08FF,U+FB50-FDFF,U+FE70-FEFF; }}

:root {{ --gold:{c['gold']}; --gold-logo:{c['gold_logo']}; --bg2:{c['bg2']}; --card:{c['card']}; --text:{c['text']};
        --muted:{c['muted']}; --border:{c['border']}; --goldsoft:{c['goldsoft']}; --chip:{c['chip']}; }}
.stApp {{ background:{c['bg']}; }}
header[data-testid="stHeader"] {{ background: transparent; height: 0; }}
[data-testid="stToolbar"] {{ display:none; }}
.block-container {{ padding-top: 0 !important; padding-bottom: 2rem; max-width: 1360px; }}
[data-testid="stMain"], [data-testid="stDialog"], [data-testid="stPopoverBody"] {{ direction:{direction}; }}
[data-testid="stMarkdownContainer"], [data-testid="stCaptionContainer"], [data-testid="stText"] {{ direction:{direction}; text-align:{start}; }}
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li {{ text-align:start; }}
[data-testid="stChatMessage"] p, [data-testid="stChatMessage"] li {{ unicode-bidi: plaintext; }}
/* top gold bar, as on moe.gov.ae */
.goldbar {{ height:6px; margin:0 0 14px; }}
/* the bar spans the full window without widening the page (a wide bar made the page scroll sideways in narrow windows) */
.goldbar::before {{ content:''; position:fixed; top:0; left:0; right:0; height:6px; z-index:999990;
                   background: linear-gradient(90deg,#8A6A26,#C9A24D 35%,#E4C87D 55%,#B68A35 80%,#8A6A26); }}
.brand {{ display:flex; align-items:center; gap:14px; min-height:64px; }}
.brand img {{ height:60px; }}
.brand .sep {{ width:1px; height:40px; background:var(--border); }}
.brand .svc {{ font-size:.82rem; color:var(--muted); line-height:1.35; }}
.demo-ribbon {{ display:flex; align-items:center; gap:10px; background:var(--goldsoft); border:1px solid var(--border);
               border-radius:10px; padding:7px 12px; font-size:.82rem; color:var(--text); }}
.demo-ribbon .tag {{ background:var(--gold); color:#fff; font-weight:700; letter-spacing:.06em; border-radius:6px;
                    padding:2px 8px; font-size:.72rem; white-space:nowrap; }}
.crumbs {{ font-size:.86rem; color:var(--muted); margin:18px 0 6px; }}
.crumbs a {{ color:var(--gold); text-decoration:underline; }}
.crumbs .chev {{ margin:0 8px; }}
div.svc-title {{ font-size:2rem; line-height:1.25; font-weight:700; color:{c['text']}; margin:4px 0 18px; }}
.card {{ background:var(--card); border:1px solid var(--border); border-radius:12px; padding:16px 18px;
        margin-bottom:14px; box-shadow:{c['shadow']}; }}
.card .h4 {{ margin:0 0 10px; font-size:1rem; font-weight:700; color:{c['text']}; }}
.kv {{ display:grid; grid-template-columns: 120px 1fr; row-gap:8px; column-gap:10px; font-size:.9rem; }}
.kv .k {{ color:var(--muted); }} .kv .v {{ color:{c['text']}; overflow-wrap:anywhere; }}
.info-row {{ display:flex; gap:10px; align-items:flex-start; margin:8px 0; font-size:.9rem; }}
.info-row .ic {{ color:var(--gold); font-weight:700; min-width:18px; }}
.info-row b {{ display:block; }}
.pill {{ display:inline-block; padding:3px 10px; border-radius:999px; font-size:.78rem; font-weight:600; }}
.p-green {{ background:{c['okbg']}; color:{c['ok']}; }} .p-amber {{ background:{c['warnbg']}; color:{c['warn']}; }}
.p-blue {{ background:{c['infobg']}; color:{c['info']}; }} .p-red {{ background:{c['badbg']}; color:{c['bad']}; }}
.p-grey {{ background:var(--chip); color:var(--muted); }}
.steps {{ display:flex; gap:6px; margin:4px 0 12px; }}
.step {{ flex:1 1 0; min-width:0; text-align:center; font-size:.76rem; padding:8px 4px; border-radius:8px;
        background:var(--chip); color:var(--muted); border:1px solid var(--border); white-space:nowrap;
        overflow:hidden; text-overflow:ellipsis; }}
.step.done {{ background:var(--goldsoft); color:var(--gold); border-color:var(--gold); }}
.step.now {{ background:var(--gold); color:#fff; border-color:var(--gold); font-weight:700; }}
.step.alert {{ background:{c['badbg']}; color:{c['bad']}; border-color:{c['bad']}; font-weight:600; }}
.src {{ display:inline-block; font-size:.68rem; letter-spacing:.06em; text-transform:uppercase; font-weight:700;
       color:var(--gold); border:1px solid var(--gold); border-radius:6px; padding:1px 7px; margin-bottom:6px; }}
[data-testid="stChatMessage"] {{ background:transparent; padding:.35rem .2rem; }}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] {{
    background:{c['user_bubble']}; border-radius:12px; padding:8px 12px; }}
[data-testid="stChatMessageAvatarAssistant"] {{ background:var(--gold) !important; color:#fff !important; }}
table.rules {{ width:100%; border-collapse:collapse; font-size:.82rem; }}
table.rules th {{ text-align:{start}; color:var(--muted); font-weight:600; border-bottom:1px solid var(--border); padding:6px; }}
table.rules td {{ border-bottom:1px solid var(--border); padding:6px; vertical-align:top; color:{c['text']}; text-align:{start}; }}
table.rules td.r {{ white-space:nowrap; color:var(--gold); font-weight:700; direction:ltr; }}
table.evidence .bad {{ font-weight:700; }} table.evidence {{ margin:2px 0 8px; }}
.ok {{ color:{c['ok']}; }} .bad {{ color:{c['bad']}; }} .miss {{ color:{c['warn']}; }} .rev {{ color:{c['info']}; }} .na {{ color:var(--muted); }}
.trace div.t {{ font-size:.82rem; padding:6px 0; border-bottom:1px solid var(--border); direction:ltr; text-align:left; }}
.trace span.n {{ display:block; color:var(--muted); font-size:.75rem; }}
.muted {{ color:var(--muted); font-size:.82rem; }}
.dot {{ display:inline-block; width:9px; height:9px; border-radius:50%; margin-inline-end:6px; }}
.kpi {{ background:var(--card); border:1px solid var(--border); border-radius:12px; padding:14px 16px;
        border-inline-start:5px solid var(--gold); box-shadow:{c['shadow']}; }}
.kpi .n {{ font-size:1.8rem; font-weight:700; color:var(--gold); line-height:1.1; }}
.kpi .l {{ font-size:.84rem; color:var(--muted); margin-top:2px; }}
.kpi.warn {{ border-inline-start-color:{c['warn']}; }} .kpi.warn .n {{ color:{c['warn']}; }}
.kpi.ok {{ border-inline-start-color:{c['ok']}; }} .kpi.ok .n {{ color:{c['ok']}; }}
.kpi.muted {{ border-inline-start-color:var(--muted); }} .kpi.muted .n {{ color:{c['text']}; }}
/* staff portal: case list, case header, call-outs and the timeline */
.case-row {{ font-size:.88rem; line-height:1.45; }}
.case-row .top {{ display:flex; justify-content:space-between; align-items:center; gap:8px; margin-bottom:2px; }}
.case-row .top b {{ font-size:1rem; letter-spacing:.02em; direction:ltr; white-space:nowrap; }}
.case-row .top .pill {{ text-align:center; }}
.case-row.sel .top b {{ color:var(--gold); }}
.case-ref {{ font-size:1.45rem; font-weight:700; letter-spacing:.02em; color:{c['text']}; direction:ltr; }}
.kv.wide {{ grid-template-columns: 150px 1fr; margin:6px 0 12px; }}
.callout {{ border-radius:10px; padding:10px 14px; margin:6px 0 12px; font-size:.9rem; border:1px solid var(--border); }}
.callout b {{ display:block; margin-bottom:4px; }}
.callout.warn {{ background:{c['warnbg']}; border-color:{c['warn']}; }} .callout.warn b {{ color:{c['warn']}; }}
.callout.ok {{ background:{c['okbg']}; border-color:{c['ok']}; }} .callout.ok b {{ color:{c['ok']}; }}
.callout.bad {{ background:{c['badbg']}; border-color:{c['bad']}; }} .callout.bad b {{ color:{c['bad']}; }}
.callout ul.why {{ margin-bottom:0; }}
.timeline {{ border-inline-start:2px solid var(--border); margin:4px 0 4px 6px; padding-inline-start:12px; }}
.timeline .ev {{ position:relative; display:grid; grid-template-columns:70px 110px 1fr; column-gap:10px; row-gap:2px;
                padding:6px 0; border-bottom:1px dashed var(--border); font-size:.84rem; }}
.timeline .ev::before {{ content:''; position:absolute; inset-inline-start:-18px; top:11px; width:10px; height:10px;
                        border-radius:50%; background:var(--muted); }}
.timeline .ev.customer::before {{ background:var(--gold); }} .timeline .ev.human::before {{ background:{c['ok']}; }}
.timeline .ev.guard::before, .timeline .ev.policy::before {{ background:{c['warn']}; }}
.timeline .ev.model::before {{ background:{c['info']}; }}
.timeline .tm {{ color:var(--muted); direction:ltr; font-variant-numeric:tabular-nums; }}
.timeline .who {{ font-weight:600; }}
.timeline .why {{ grid-column:3; color:var(--muted); font-size:.76rem; }}
.chips span {{ display:inline-block; font-size:.74rem; border-radius:6px; padding:2px 7px; margin:2px 3px 2px 0;
              background:var(--chip); border:1px solid var(--border); direction:ltr; }}
.payhead {{ display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--border);
           padding-bottom:10px; margin-bottom:10px; }}
.payhead .amt {{ font-size:1.6rem; font-weight:700; color:var(--gold); }}
.cardviz {{ border-radius:14px; padding:16px 18px; color:#fff; background:linear-gradient(135deg,#1F2937,#4B5563 60%,#92722A);
           font-family: 'Courier New', monospace; letter-spacing:.12em; margin:6px 0 12px; direction:ltr; }}
.cardviz .brand2 {{ font-family:Inter, sans-serif; letter-spacing:.04em; font-weight:700; text-align:right; }}
/* card number, expiry and CVV always read left to right, also on the Arabic page */
[data-testid="stDialog"] input {{ direction:ltr; text-align:left; }}
.h5 {{ font-weight:700; font-size:.88rem; margin:10px 0 4px; color:{c['text']}; }}
.att {{ font-size:.9rem; padding:2px 0; }}
ul.why {{ margin:0 0 6px; padding-inline-start:20px; font-size:.9rem; }} ul.why li {{ margin:4px 0; }}
.footer {{ border-top:1px solid var(--border); margin-top:26px; padding-top:12px; font-size:.78rem; color:var(--muted); }}
div[data-testid="stPopover"] button, div[data-testid="stPopoverButton"] {{ white-space:nowrap; }}
/* narrow windows (side panels, small laptops, tablets): header and ribbon rows wrap instead of clipping labels */
@media (max-width: 1100px) {{
  .brand .svc, .brand .sep {{ display:none; }}
  [data-testid="stHorizontalBlock"]:has(.brand), [data-testid="stHorizontalBlock"]:has(.demo-ribbon) {{ flex-wrap:wrap; row-gap:8px; }}
  [data-testid="stHorizontalBlock"]:has(.brand) > [data-testid="stColumn"]:first-child,
  [data-testid="stHorizontalBlock"]:has(.demo-ribbon) > [data-testid="stColumn"] {{ flex:1 1 100% !important; min-width:100% !important; }}
  [data-testid="stHorizontalBlock"]:has(.brand) > [data-testid="stColumn"]:nth-child(2) {{ flex:3 1 0 !important; min-width:0 !important; }}
  [data-testid="stHorizontalBlock"]:has(.brand) > [data-testid="stColumn"]:nth-child(n+3) {{ flex:0 0 auto !important; width:auto !important; min-width:0 !important; }}
  [data-testid="stHorizontalBlock"]:has(.brand) button {{ white-space:nowrap; }}
  .step {{ white-space:normal; overflow:visible; line-height:1.2; font-size:.68rem; padding:7px 2px;
           word-break:keep-all; overflow-wrap:normal; hyphens:none; }}
}}
/* phones: the Parent | Staff switch gets its own full row, wide tables scroll inside their box */
@media (max-width: 640px) {{
  [data-testid="stHorizontalBlock"]:has(.brand) > [data-testid="stColumn"]:nth-child(2) {{ flex:1 1 100% !important;
      min-width:100% !important; order:3; }}
  [data-testid="stHorizontalBlock"]:has(.brand) > [data-testid="stColumn"]:first-child {{ flex:1 1 auto !important;
      min-width:0 !important; }}
  .tablewrap {{ overflow-x:auto; }}
  .timeline .ev {{ grid-template-columns:62px 1fr; }} .timeline .what, .timeline .why {{ grid-column:1 / -1; }}
  div.svc-title {{ font-size:1.5rem; }}
}}
.tablewrap {{ max-width:100%; overflow-x:auto; }}
</style>"""
