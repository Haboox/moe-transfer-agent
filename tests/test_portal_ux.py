"""Portal changes of 21 October (night): the built-in document viewer, the nationality choice that picks the
matching documents in the open test, and the redesigned staff portal (case list, open case, decision)."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from agent.config import ROOT
from agent.mocks import MockBackend

APP = str(Path(__file__).resolve().parent.parent / "app.py")


@pytest.fixture(autouse=True)
def scripted(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_PROVIDER", "scripted")
    import agent.mocks as mocks
    monkeypatch.setattr(mocks, "RUNTIME_DIR", tmp_path)
    monkeypatch.setattr(mocks.CaseStore.__init__, "__defaults__", (tmp_path / "cases.json",))


def _run():
    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state["provider"] = "scripted"
    at.run()
    assert not at.exception, at.exception
    return at


def _start(at, pid):
    at.session_state["persona"] = pid
    next(b for b in at.button if b.label == "Start new session").click().run()


def _attach_all(at):
    for cb in at.checkbox:
        if cb.key and cb.key.startswith("pick_"):
            cb.check()
    next(b for b in at.button if b.label == "Attach selected").click().run()
    at.run()
    assert not at.exception, at.exception


# ------------------------------------------------------------------ the viewer
def test_every_synthetic_pdf_can_be_drawn_as_pages():
    from ui.viewer import _pdf_pages
    docs = MockBackend().documents
    for d in list(docs.values())[::7]:                    # a spread across applicants, types and both editions
        path = ROOT / d["path"]
        if path.suffix.lower() != ".pdf":
            continue
        pages, total = _pdf_pages(str(path), path.stat().st_mtime)
        assert total >= 1 and pages and pages[0][:8] == b"\x89PNG\r\n\x1a\n", d["doc_id"]


def test_view_buttons_are_offered_for_attached_documents_and_the_library():
    at = _run()
    _start(at, "SYN-P01")
    _attach_all(at)
    views = [b for b in at.button if b.key and b.key.startswith("view_att_")]
    assert len(views) == 5
    assert any(b.key and b.key.startswith("view_lib_") for b in at.button)


# ------------------------------------------------------------------ nationality picks the matching documents
@pytest.mark.parametrize("nat,owner", [("Oman", "SYN-P03"), ("Egypt", "SYN-P02"), ("Kuwait", "SYN-P11")])
def test_choosing_a_nationality_shows_that_applicants_documents(nat, owner):
    at = _run()
    at.session_state["open_nat"] = nat
    _start(at, "SYN-OPEN")
    lib = next(s for s in at.selectbox if s.key and s.key.startswith("lib_"))
    assert lib.value == owner
    assert any("nationality you chose" in c.value for c in at.caption)


def test_a_nationality_with_no_prepared_applicant_says_so():
    at = _run()
    at.session_state["open_nat"] = "Iceland"
    _start(at, "SYN-OPEN")
    assert any("No prepared applicant" in c.value for c in at.caption)


# ------------------------------------------------------------------ staff portal
def test_staff_portal_lists_cases_opens_one_and_records_the_decision():
    at = _run()
    _start(at, "SYN-P03")
    _attach_all(at)
    agent = at.session_state["agent"]
    ok, _ = agent.complete_payment("card", {"name": "Synthetic Parent", "number": "4242424242424242",
                                            "expiry": "12/29", "cvv": "123"})
    assert ok
    at.chat_input[0].set_value("Paid").run()
    at.run()
    ref = agent.state.case_ref
    assert agent.state.status.value == "PENDING_HUMAN_REVIEW"
    at.session_state["view"] = "staff"
    at.run()
    html = " ".join(m.value for m in at.markdown)
    assert ref in html and "callout warn" in html and "paid (receipt" in html
    assert any(b.key and b.key.startswith(f"view_st_{ref}_") for b in at.button)        # documents viewable
    at.text_input(key=f"n_{ref}").input("Lineage name, same person. Approved.")
    next(b for b in at.button if b.label == "Approve").click().run()
    at.run()
    assert not at.exception and agent.backend.cases.get(ref).status.value == "HUMAN_APPROVED"
    at.segmented_control(key="staff_filter__en0").set_value("decided").run()
    html = " ".join(m.value for m in at.markdown)
    assert "callout ok" in html and "Lineage name, same person" in html


def test_staff_portal_in_arabic_with_no_cases():
    at = _run()
    next(b for b in at.button if b.key == "lang_btn").click().run()
    at.session_state["view"] = "staff"
    at.run()
    assert not at.exception
    assert any("الطلبات" in str(t.label) for t in at.tabs)


# ------------------------------------------------------------------ quality of life (21 October, night)
def test_picking_a_situation_starts_it_at_once():
    at = _run()
    first = at.session_state["agent"].state.session_id
    at.radio(key="dc_persona__en0").set_value("SYN-P03").run()
    assert not at.exception
    agent = at.session_state["agent"]
    assert agent.state.persona_id == "SYN-P03" and agent.state.session_id != first


def test_changing_the_simulated_problem_starts_again_with_it():
    at = _run()
    at.radio(key="dc_persona__en0").set_value("SYN-P01").run()
    at.selectbox(key="dc_fsys__en0").set_value("payment").run()
    assert not at.exception and at.session_state["failure"] == "payment:timeout_once"
    at.selectbox(key="dc_fmode__en0").set_value("error_always").run()
    assert not at.exception and at.session_state["failure"] == "payment:error_always"
    assert at.session_state["config"][2] == "payment:error_always"
    assert at.session_state["agent"].backend.failures == {"payment": "error_always"}
    at.selectbox(key="dc_fsys__en0").set_value("none").run()
    assert at.session_state["failure"] == "none" and at.session_state["agent"].backend.failures == {}


def test_clear_all_cases_empties_the_staff_portal():
    at = _run()
    _start(at, "SYN-P01")
    _attach_all(at)                       # opens the payment window; a case is created after payment
    agent = at.session_state["agent"]
    agent.complete_payment("card", {"name": "x", "number": "4242424242424242", "expiry": "12/29", "cvv": "123"})
    at.chat_input[0].set_value("Paid").run()
    at.run()
    assert at.session_state["agent"].backend.cases.list()
    next(b for b in at.button if b.label == "Clear all cases").click().run()
    assert not at.exception and not at.session_state["agent"].backend.cases.list()


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_suggested_questions_are_offered_and_send_a_message(lang):
    at = _run()
    if lang == "ar":
        next(b for b in at.button if b.key == "lang_btn").click().run()
    pills = [p for p in at.get("button_group") if p.key and str(p.key).startswith("sugg_")]
    assert pills, "no suggestions shown"
    q = "What documents do I need?" if lang == "en" else "ما المستندات المطلوبة؟"
    pills[0].set_value(q).run()
    at.run()
    assert not at.exception
    chat = at.session_state["chat"]
    assert any(m["role"] == "user" and m["text"] == q for m in chat) and chat[-1]["role"] == "assistant"
