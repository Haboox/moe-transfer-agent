"""The portal runs in both languages and both views without errors (Streamlit's headless test runner, no AI).

The browser look (light/dark, right to left) was checked with screenshots; these tests make sure the
screens and the main journey keep working after any change.
"""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


@pytest.fixture(autouse=True)
def scripted(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_PROVIDER", "scripted")
    import agent.mocks as mocks
    monkeypatch.setattr(mocks, "RUNTIME_DIR", tmp_path)           # cases of this test only
    monkeypatch.setattr(mocks.CaseStore.__init__, "__defaults__", (tmp_path / "cases.json",))


def _run():
    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state["provider"] = "scripted"
    at.run()
    assert not at.exception, at.exception
    return at


def _attach_all(at, label):
    for cb in at.checkbox:
        if cb.key and cb.key.startswith("pick_"):
            cb.check()
    next(b for b in at.button if b.label == label).click().run()
    at.run()
    assert not at.exception, at.exception


@pytest.mark.parametrize("lang,attach,pay_word", [("en", "Attach selected", "payment window"),
                                                  ("ar", "إرفاق المحدد", "نافذة الدفع")])
def test_parent_journey_to_payment_and_submission(lang, attach, pay_word):
    at = _run()
    if lang == "ar":
        next(b for b in at.button if b.key == "lang_btn").click().run()
        assert at.session_state["lang"] == "ar"
    _attach_all(at, attach)
    agent = at.session_state["agent"]
    assert agent.state.status.value == "AWAITING_PAYMENT"
    assert any(pay_word in m["text"] for m in at.session_state["chat"])
    ok, _ = agent.complete_payment("card", {"name": "Synthetic Parent", "number": "4242424242424242",
                                            "expiry": "12/29", "cvv": "123"})
    assert ok
    at.chat_input[0].set_value("تم الدفع" if lang == "ar" else "Paid").run()
    at.run()
    assert not at.exception and agent.state.status.value == "SUBMITTED"


def test_staff_view_and_theme_switch_render():
    at = _run()
    next(b for b in at.button if b.key == "theme_btn").click().run()
    assert at.session_state["theme"] == "dark" and not at.exception
    at.session_state["view"] = "staff"            # the Parent | Staff switch
    at.run()
    assert not at.exception
    assert any("Cases" in str(t.label) for t in at.tabs) and any("Audit" in str(t.label) for t in at.tabs)


def test_language_switch_starts_a_session_with_that_editions_documents():
    at = _run()
    next(b for b in at.button if b.key == "lang_btn").click().run()
    labels = [cb.label for cb in at.checkbox if cb.key and cb.key.startswith("pick_")]
    assert "جواز السفر" in labels and all("Passport" not in x for x in labels)
    keys = [cb.key for cb in at.checkbox if cb.key and cb.key.startswith("pick_")]
    assert all("-AR-" in k for k in keys)


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_every_prepared_applicant_and_the_open_test_run_on_both_screens(lang):
    """Each test situation in Demo controls: start it, attach everything offered, then open the staff screen."""
    from ui.session import persona_ids
    at = _run()
    if lang == "ar":
        next(b for b in at.button if b.key == "lang_btn").click().run()
    label = "إرفاق المحدد" if lang == "ar" else "Attach selected"
    for pid in persona_ids():
        at.session_state["persona"] = pid
        at.session_state["open_nat"] = "Oman" if pid == "SYN-OPEN" else None
        next(b for b in at.button if b.label in ("Start new session", "بدء جلسة جديدة")).click().run()
        assert not at.exception, (pid, at.exception)
        if any(cb.key and cb.key.startswith("pick_") for cb in at.checkbox):
            _attach_all(at, label)
        assert not at.exception, (pid, at.exception)
    at.session_state["view"] = "staff"
    at.run()
    assert not at.exception


def test_the_officer_sees_which_name_does_not_match_and_on_which_document():
    at = _run()
    at.session_state["persona"] = "SYN-P03"
    next(b for b in at.button if b.label == "Start new session").click().run()
    _attach_all(at, "Attach selected")
    agent = at.session_state["agent"]
    # D-06: the request that needs an officer is paid for first
    assert agent.state.status.value == "AWAITING_PAYMENT"
    assert "officer" in at.session_state["chat"][-1]["text"] and "AED 50" in at.session_state["chat"][-1]["text"]
    ok, _ = agent.complete_payment("card", {"name": "Synthetic Parent", "number": "4242424242424242",
                                            "expiry": "12/29", "cvv": "123"})
    assert ok
    at.chat_input[0].set_value("Paid").run()
    at.run()
    assert agent.state.status.value == "PENDING_HUMAN_REVIEW" and agent.state.receipt is not None
    assert "fee is paid" in at.session_state["chat"][-1]["text"]
    at.session_state["view"] = "staff"
    at.run()
    html = " ".join(m.value for m in at.markdown)
    assert "Salem bin Saeed Al Qarwani" in html and "class='bad'>No<" in html and "Grade 4 certificate" in html
    greeting = at.session_state["chat"][0]["text"]
    assert "speak" not in greeting and "Arabic" not in greeting
