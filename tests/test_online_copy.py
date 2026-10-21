"""Found by testing the online copy (21 October): its server runs on UTC, and a closed case got an odd reply."""
from dataclasses import replace

from agent.agent import ServiceAgent
from agent.config import get_settings
from agent.llm import ScriptedLLM
from agent.mocks import MockBackend
from agent.models import CaseStatus
from ui.staff import _local

S = replace(get_settings(), llm_provider="scripted", mock_latency_seconds=0)


def test_staff_times_are_shown_in_uae_time_whatever_the_server_clock():
    assert _local("2026-10-21T15:12:30+00:00", "%H:%M") == "19:12"
    assert _local("2026-10-21T21:30:00+00:00") == "01:30:00"          # past midnight in the UAE
    assert _local("not a time") == "not a time"


def test_asking_for_a_person_after_submission_does_not_ask_for_documents(tmp_path):
    a = ServiceAgent(ScriptedLLM(), "SYN-P01", backend=MockBackend(), settings=S, log_dir=tmp_path)
    a.state.status, a.state.case_ref = CaseStatus.SUBMITTED, "SYN-1001"
    reply = a.handle_turn("I want to speak to a real person").reply
    assert "80051115" in reply and "attach" not in reply.lower()
    a2 = ServiceAgent(ScriptedLLM(), "SYN-P01", backend=MockBackend(), settings=S, log_dir=tmp_path)
    assert "attach" in a2.handle_turn("I want to speak to a real person").reply.lower()
