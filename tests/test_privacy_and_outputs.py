"""No sensitive data in replies or logs; replies cannot overclaim; only staff can decide (P-01, P-04, P-08)."""
import pytest

from agent.human_review import ReviewError, decide
from agent.models import CaseState, CaseStatus
from agent.output_guard import check_reply
from agent.redact import redact_obj, redact_text


def test_mock_numbers_are_masked():
    assert redact_text("Passport MOCK-P-100001 and EID MOCK-EID-0001-01") == \
        "Passport MOCK-P-****01 and EID MOCK-EID-****01"


def test_real_format_emirates_id_email_phone_masked():
    out = redact_text("784-1990-1234567-1 a.b@example.com +971 50 123 4567")
    assert "784-1990" not in out and "example.com" not in out and "123 4567" not in out


def test_known_names_masked_recursively():
    out = redact_obj({"a": ["Hello Alpha Testchild"], "b": {"c": "alpha"}}, ["Alpha Testchild", "Alpha"])
    assert "Alpha" not in str(out) and "alpha" not in str(out)


def _state(status=CaseStatus.IN_PROGRESS, ref=None):
    return CaseState(session_id="S-x", persona_id="SYN-P01", status=status, case_ref=ref)


@pytest.mark.parametrize("reply", ["Your application has been approved!",
                                   "Good news, equivalency granted.",
                                   "I have submitted your request."])
def test_overclaiming_reply_is_replaced(reply):
    out, problems = check_reply(reply, _state())
    assert problems and out != reply


def test_foreign_case_reference_is_blocked():
    out, problems = check_reply("Your reference is SYN-9999.", _state(CaseStatus.SUBMITTED, "SYN-1001"))
    assert problems


def test_correct_submission_reply_allowed():
    out, problems = check_reply("Submitted, reference SYN-1001.", _state(CaseStatus.SUBMITTED, "SYN-1001"))
    assert not problems


def test_reply_numbers_are_masked():
    out, _ = check_reply("We checked passport MOCK-P-100001.", _state())
    assert "100001" not in out


# ---------------- human review path
def _pending_case(backend):
    return backend.cases_create(session_id="S-rev", student_ref="SYN-STU-P03",
                                status="PENDING_HUMAN_REVIEW", escalation_reason="name_mismatch")["case_ref"]


def test_staff_can_approve(backend, tmp_path):
    ref = _pending_case(backend)
    rec = decide(backend.cases, ref, "STAFF-A12", "approve", "Name difference is a transliteration.", tmp_path)
    assert rec.status == CaseStatus.HUMAN_APPROVED
    assert "human_decision" in (tmp_path / "audit_S-rev.jsonl").read_text()


@pytest.mark.parametrize("reviewer", ["", "customer", "MOE-EMPLOYEE", "staff-a12"])
def test_non_staff_cannot_decide(backend, tmp_path, reviewer):
    ref = _pending_case(backend)
    with pytest.raises(ReviewError):
        decide(backend.cases, ref, reviewer, "approve", "ok", tmp_path)


def test_decision_requires_note(backend, tmp_path):
    with pytest.raises(ReviewError):
        decide(backend.cases, _pending_case(backend), "STAFF-A12", "approve", "  ", tmp_path)


def test_an_officer_issues_the_decision_on_a_submitted_case_once(backend, tmp_path):
    """D-02: the agent only submits; the equivalency decision on a submitted case is an officer's, made once."""
    ref = backend.cases_create(session_id="S-x", student_ref="X", status="SUBMITTED")["case_ref"]
    rec = decide(backend.cases, ref, "STAFF-A12", "approve", "documents checked, Grade 6 equivalency approved", tmp_path)
    assert rec.status == CaseStatus.HUMAN_APPROVED
    with pytest.raises(ReviewError):
        decide(backend.cases, ref, "STAFF-A12", "reject", "changed my mind", tmp_path)   # decided cases are final
    log = (tmp_path / "audit_S-x.jsonl").read_text("utf-8")
    assert "P-16" in log and '"previous": "SUBMITTED"' in log


@pytest.mark.parametrize("reply", [
    "Your request has been successfully processed. You will receive the equivalency certificate soon.",
    "Your certificate is being issued now.",
    "Good news, you are eligible for equivalency.",
    "Your son's grades are now equivalent to the UAE Grade 7.",
])
def test_outcome_promises_are_blocked(reply):
    """Found in a live run with qwen3:8b: fluent, polite, and wrong (only a decision can promise this)."""
    out, problems = check_reply(reply, _state(CaseStatus.SUBMITTED, "SYN-1001"))
    assert problems and out != reply


def test_normal_guidance_about_certificates_is_allowed():
    out, problems = check_reply("Please upload the Grade 6 certificate with the embassy stamp.", _state())
    assert not problems


# ------------------------------------------------------------------ found in the live run of 20 October (qwen3:8b)
import pytest as _pt                                                                    # noqa: E402
from agent.llm import LLMReply, ScriptedLLM                                            # noqa: E402


class _SaysButDoesNot(ScriptedLLM):
    """A model that promises a transfer to a person and never calls the tool (seen live in Q18, Q19, A18)."""
    def __init__(self, text):
        super().__init__([{"intent": "request_human", "confidence": 0.95, "last_completed_grade": 0,
                           "asks_to_override_rules": False, "language": "en"}])
        self.text = text

    def chat(self, system, messages, tools):
        return LLMReply(text=self.text)


@_pt.mark.parametrize("msg,reply", [
    ("I want to speak to a real person please", "Let me connect you with a human officer right away."),
    ("أريد التحدث مع موظف", "أهلاً بك! سأقوم بتحويلك إلى موظف في Министерия التعليم لمساعدتك."),
])
def test_a_parent_who_asks_for_a_person_gets_the_number_from_code_not_a_false_promise(make_agent, msg, reply):
    a = make_agent("SYN-P01", llm=_SaysButDoesNot(reply), ui_lang="ar" if "موظف" in msg else "en")
    r = a.handle_turn(msg)
    assert a.state.case_ref is None and "80051115" in r.reply
    assert "Министерия" not in r.reply and "connect you" not in r.reply and "سأقوم بتحويلك" not in r.reply


def test_a_handover_claim_or_foreign_script_is_never_shown_when_untrue():
    s = CaseState(session_id="S-x", persona_id="SYN-P01")
    assert check_reply("I will transfer you to an officer now.", s)[1]
    assert check_reply("سأقوم بتحويلك إلى موظف", s)[1]
    assert check_reply("مرحباً بك في Министерия", s)[1]
    assert not check_reply("You can ask for a person at any time.", s)[1]


def test_a_reply_asking_for_an_id_number_is_never_shown():
    s = CaseState(session_id="S-x", persona_id="SYN-P01")
    assert check_reply("Please provide your UAE Pass ID so I can continue with your request.", s)[1]
    assert check_reply("يرجى أن ترسل رقم الهوية الخاص بك", s)[1]
    assert not check_reply("Please attach the passport.", s)[1]


# ------------------------------------------------------------------ P-17: no invented facts (found live 21 October)
from datetime import datetime as _dt, timezone as _tz                                  # noqa: E402
from agent.facts import clock_reply, is_clock_question                                 # noqa: E402


@_pt.mark.parametrize("msg", ["hi whats the time here?", "What time is it in Dubai", "what is the date today",
                              "كم الساعة الآن؟", "شو الساعة", "ما تاريخ اليوم"])
def test_time_questions_are_recognised(msg):
    assert is_clock_question(msg)


@_pt.mark.parametrize("msg", ["How long does it take?", "what time will my request be done", "when will I get it",
                              "كم المدة"])
def test_service_time_questions_are_not_clock_questions(msg):
    assert not is_clock_question(msg)


def test_the_time_comes_from_the_clock_in_uae_time():
    noon_utc = _dt(2026, 10, 21, 10, 7, tzinfo=_tz.utc)                    # 14:07 in the UAE
    assert "2:07 PM on Wednesday, 21 October 2026" in clock_reply("en", noon_utc)
    assert "2:07 مساءً، يوم الأربعاء 21 أكتوبر 2026" in clock_reply("ar", noon_utc)


@_pt.mark.parametrize("lang,msg", [("en", "hi whats the time here?"), ("ar", "كم الساعة الآن؟"),
                                   ("en", "what's the weather in Dubai tomorrow?"), ("ar", "كيف الطقس اليوم؟")])
def test_the_model_is_never_asked_for_the_time_or_outside_facts(make_agent, lang, msg):
    class Inventor(_SaysButDoesNot):
        def interpret(self, *a):
            return {"intent": "unclear", "confidence": 0.9, "last_completed_grade": 0,
                    "asks_to_override_rules": False, "language": lang}
    a = make_agent("SYN-P01", llm=Inventor("The current time in the UAE is 10:45 AM and it is sunny."), ui_lang=lang)
    r = a.handle_turn(msg)
    assert "10:45" not in r.reply and "sunny" not in r.reply
    assert any(e["event"] in ("clock_answered", "off_topic_answered") for e in a.ctx.audit.events)


def test_a_model_reply_with_a_clock_time_is_blocked():
    s = CaseState(session_id="S-x", persona_id="SYN-P01")
    assert check_reply("The current time in the UAE is 10:45 AM.", s)[1]
    assert check_reply("الساعة 10 صباحاً الآن", s)[1]
    assert not check_reply("The fee is 50 AED.", s)[1]


@_pt.mark.parametrize("msg", ["hi", "thanks", "???", "whats the time", "how is the weather", "I want to talk to a person",
                              "رقمي 0501234567", "مرحبا", "كم الساعة"])
def test_small_talk_and_fixed_answers_never_call_the_model(make_agent, msg):
    class NoCalls(ScriptedLLM):
        def interpret(self, *a):
            raise AssertionError("the model was called")

        def chat(self, *a):
            raise AssertionError("the model was called")
    r = make_agent("SYN-P01", llm=NoCalls(), ui_lang="ar" if any("؀" <= c <= "ۿ" for c in msg) else "en").handle_turn(msg)
    assert r.reply
