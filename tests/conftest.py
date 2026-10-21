"""Shared test fixtures. Tests never use a real AI model and never touch the real logs/ or runtime/ folders."""
import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="moe-tests-")
os.environ.setdefault("MOE_LOG_DIR", os.path.join(_TMP, "logs"))       # set before the app's modules are imported
os.environ.setdefault("MOE_RUNTIME_DIR", os.path.join(_TMP, "runtime"))

from dataclasses import replace  # noqa: E402
from datetime import date

import pytest

from agent.agent import ServiceAgent
from agent.audit import AuditLog
from agent.config import get_settings
from agent.executor import AgentContext
from agent.llm import ScriptedLLM
from agent.mocks import CaseStore, MockBackend
from agent.models import CaseState

TODAY = date(2026, 10, 12)


@pytest.fixture
def settings():
    return replace(get_settings(), application_date=TODAY, llm_provider="scripted", tool_max_retries=1,
                   tool_timeout_seconds=0.2, mock_latency_seconds=0.0, mock_hang_seconds=0.5)


@pytest.fixture
def backend(tmp_path):
    return MockBackend(case_store=CaseStore(tmp_path / "cases.json"), hang_s=0.5)


@pytest.fixture
def make_ctx(tmp_path, settings, backend):
    def _make(persona="SYN-P01", failures=None):
        be = backend if failures is None else MockBackend(failures=failures, hang_s=0.5,
                                                          case_store=CaseStore(tmp_path / "cases.json"))
        state = CaseState(session_id="S-test0001", persona_id=persona)
        return AgentContext(state=state, backend=be, audit=AuditLog("S-test0001", tmp_path), settings=settings)
    return _make


@pytest.fixture
def make_agent(tmp_path, settings, backend):
    def _make(persona="SYN-P01", llm=None, failures=None, ui_lang="en"):
        be = backend if failures is None else MockBackend(failures=failures, hang_s=0.5,
                                                          case_store=CaseStore(tmp_path / "cases.json"))
        return ServiceAgent(llm or ScriptedLLM(), persona, backend=be, settings=settings, log_dir=tmp_path,
                            ui_lang=ui_lang)
    return _make
