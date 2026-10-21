"""The stress conversations (scripts/stress_test.py) as repeatable tests: everyday and extreme messages in English and
Arabic, every reply checked for language, internal codes, demo wording, promises and leaked numbers or names."""
import importlib.util
from pathlib import Path

import pytest

from agent.models import CaseStatus, Outcome

_spec = importlib.util.spec_from_file_location("stress_test", Path(__file__).resolve().parent.parent / "scripts" / "stress_test.py")
stress = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(stress)


@pytest.mark.parametrize("cid,pid,lang,turns,want", stress.CONVERSATIONS, ids=[c[0] for c in stress.CONVERSATIONS])
def test_stress_conversation(make_agent, backend, cid, pid, lang, turns, want):
    agent = make_agent(pid, ui_lang=lang)
    st = backend.personas[pid]["student"]
    names = [f"{st['given_name']} {st['family_name']}", f"{st.get('given_name_ar', '')} {st.get('family_name_ar', '')}".strip()]
    for turn in turns:
        text, ups, drop = (tuple(turn) + ([],))[:3]
        for doc_id in drop:
            agent.remove_upload(doc_id)
        r = agent.handle_turn(text, ups)
        assert not stress.check(r.reply, r.blocked_reply_reasons, agent.state.lang, agent.state.status.value, names), \
            (text, r.reply)
    s = agent.state
    if want:
        assert s.status.value == want
    if s.status == CaseStatus.SUBMITTED:
        assert s.rule_report.outcome == Outcome.ELIGIBLE and s.receipt and s.case_ref
