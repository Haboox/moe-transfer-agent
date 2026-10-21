"""Every word on screen exists in English and Arabic, with the same placeholders, for every status, outcome,
failure, model and upload type the code can show (a missing key would crash the page)."""
import glob
import re

from agent.models import CaseStatus, Outcome, RuleStatus
from ui.i18n import S

PH = re.compile(r"\{(\w+)\}")
AR = re.compile(r"[؀-ۿ]")


def test_every_text_has_both_languages_and_the_same_placeholders():
    for key, (en, ar) in S.items():
        assert en.strip() and ar.strip(), key
        assert sorted(PH.findall(en)) == sorted(PH.findall(ar)), key
        if key not in ("other_lang", "dc_guide_body"):          # these name the Arabic button on purpose
            assert not AR.search(en), key


def test_every_key_the_screens_ask_for_exists():
    used = set()
    for f in glob.glob("ui/*.py") + ["app.py"]:
        used |= set(re.findall(r'\bt\("([a-z0-9_]+)"', open(f, encoding="utf-8").read()))
    assert not [k for k in used if not k.endswith("_") and k not in S]


def test_every_dynamic_text_family_is_complete():
    from ui.parent import UPLOAD_TYPES
    from ui.session import FAILURES
    need = ([f"st_{s.value}" for s in CaseStatus] + [f"oc_{o.value}" for o in Outcome]
            + [f"rs_{r.value}" for r in RuleStatus] + [f"fail_{f}" for f in FAILURES]
            + [f"prov_{p}" for p in ("ollama", "hosted", "anthropic", "scripted")]
            + [f"ut_{u}" for u in UPLOAD_TYPES] + [f"lang_{x}" for x in ("en", "ar")]
            + [f"list_{x}" for x in ("todo", "decided", "all")] + [f"list_empty_{x}" for x in ("todo", "decided", "all")])
    assert not [k for k in need if k not in S]
