"""The case study, line by line. Each test names the requirement it proves.

Source: "AI-Powered Government Service Agent - Candidate Case Study" (MoE, 2 pages).
Run just this file to show the panel the mapping:  python -m pytest tests/test_case_study_checklist.py -v
"""
import ast
import json
import re

import pytest

from agent import rules
from agent.config import ROOT, SERVICE_CARD_URL
from agent.executor import ToolFailure, call_backend
from agent.models import ApplicantProfile, CaseRecord, PaymentReceipt, VerificationResult
from agent.tools import TOOLS

DOCS = ROOT / "docs"


def _imports(module_file: str) -> set[str]:
    tree = ast.parse((ROOT / module_file).read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
        elif isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
    return names


# ------------------------------------------------------------ page 1: choose a transactional service
def test_p1_real_transactional_service_with_documents_validation_and_decision():
    card = (DOCS / "00_service_card.md").read_text(encoding="utf-8")
    assert SERVICE_CARD_URL in card                                    # real, published card
    for must in ["Required documents", "Service Conditions", "Fees", "Decision"]:
        assert must in card, must                                       # documents, validation, decision


def test_p1_every_business_rule_traces_to_the_card_or_a_labelled_assumption():
    inp = rules.VerifiedInputs(nationality="India", uploads=[], verifications={},
                               application_date=__import__("datetime").date(2026, 10, 12))
    results = rules.evaluate(inp).results
    doc = (DOCS / "02_rules_and_assumptions.md").read_text(encoding="utf-8")
    for r in results:
        assert re.match(r"R-\d\d$", r.rule_id)
        assert r.source.startswith("Card:") or r.source.startswith("ASSUMPTION"), r.rule_id
        assert f"| {r.rule_id} |" in doc, f"{r.rule_id} missing from the rules document"
    for a in re.findall(r"A-\d\d", " ".join(r.source for r in results)):
        assert f"| {a} |" in doc, f"assumption {a} not documented"


# ------------------------------------------------------------ page 1: real service, synthetic data
def test_p1_synthetic_data_only_every_record_labelled_and_no_real_identifiers():
    personas = json.loads((ROOT / "data/synthetic/personas.json").read_text(encoding="utf-8"))
    docs = json.loads((ROOT / "data/synthetic/documents.json").read_text(encoding="utf-8"))
    for rec in personas + docs:
        assert "SYNTHETIC" in rec["label"]
    blob = json.dumps(personas + docs)
    assert not re.search(r"\b784-?\d{4}-?\d{7}-?\d\b", blob), "real Emirates ID format found"
    for d in docs:
        num = d["registry"].get("number")
        assert num is None or num.startswith("MOCK-")


def test_p1_mock_systems_cover_identity_document_checks_payments_and_case_management():
    systems = {"identity": "get_applicant_profile", "verification": "verify_documents",
               "payment": "request_payment", "cases": "submit_application"}
    src = (ROOT / "agent/mocks.py").read_text(encoding="utf-8")
    for system, tool in systems.items():
        assert tool in TOOLS
        assert f'_inject("{system}")' in src, f"{system} mock has no failure injection"
    assert "MOCK" in src.split('"""')[1]                                # mocks labelled as MOCK


# ------------------------------------------------------------ page 1: an agent, not just a chatbot
def test_p1_agent_acts_through_tools_and_has_no_approval_tool():
    assert len(TOOLS) >= 5
    assert not any(w in n for n in TOOLS for w in ("approve", "reject", "decide", "override"))


# ------------------------------------------------------------ page 1: the decision must be explainable
def test_p1_four_responsibilities_are_separate_modules():
    assert not any("llm" in m for m in _imports("agent/rules.py")), "Validate must not use the model"
    assert not any("llm" in m for m in _imports("agent/guard.py")), "Act (guard) must not use the model"
    assert not any("llm" in m for m in _imports("agent/human_review.py")), "Approve must not use the model"
    assert not any("human_review" in m for m in _imports("agent/tools.py")), "model cannot reach Approve"


# ------------------------------------------------------------ key requirement: controlled, auditable
def test_key_every_tool_call_is_logged_with_its_basis(make_agent):
    a = make_agent("SYN-P01")
    docs = [d["doc_id"] for d in a.backend.persona_documents("SYN-P01", "en")]
    a.handle_turn("Grade 6 equivalency please", docs)
    requested = [e for e in a.ctx.audit.events if e["event"] == "tool_requested"]
    results = [e for e in a.ctx.audit.events if e["event"] in ("tool_result", "tool_blocked")]
    assert requested and len(requested) == len(results)                 # every call logged with its result
    for e in requested:
        assert "triggered by" in e["basis"]
        assert any(k in e["basis"] for k in ("Card:", "Rules", "R-", "Approve")), e["basis"]


def test_key_every_tool_has_a_documented_basis():
    for t in TOOLS.values():
        assert t.basis, t.name


# ------------------------------------------------------------ page 2, section 03: mocked contracts
@pytest.mark.parametrize("system,fn,contract", [
    ("identity", lambda b: b.identity_get_profile("SYN-P01"), ApplicantProfile),
    ("verification", lambda b: b.verification_verify("SYN-P01", "P01-PASSPORT"), VerificationResult),
    ("payment", lambda b: b.payment_charge("S-test0001", 50), PaymentReceipt),
    ("cases", lambda b: b.cases_create(session_id="S", student_ref="X", status="SUBMITTED"), CaseRecord),
])
@pytest.mark.parametrize("failure", ["timeout_always", "error_always", "malformed_always"])
def test_s03_each_mock_has_a_contract_and_realistic_failures(make_ctx, system, fn, contract, failure):
    ctx = make_ctx(failures={system: failure})
    with pytest.raises(ToolFailure) as e:
        call_backend(ctx, system, "op", lambda: fn(ctx.backend), contract, basis="test")
    assert e.value.outcome == failure.replace("_always", "")
    assert ctx.stats["backend_attempts"] == 2                           # one retry, then stop


# ------------------------------------------------------------ non-negotiable: repeatable tests
def test_nn_repeatable_same_inputs_same_results(make_agent):
    outcomes = []
    for _ in range(3):
        a = make_agent("SYN-P02")
        docs = ["P02-PASSPORT", "P02-EMIRATES_ID", "P02-CERT-G8", "P02-CERT-G7"]
        a.handle_turn("Grade 8 equivalency", docs)
        outcomes.append((a.state.status, tuple((r.rule_id, r.status) for r in a.state.rule_report.results)))
    assert len(set(outcomes)) == 1


# ------------------------------------------------------------ deliverables exist
@pytest.mark.parametrize("path", ["README.md", "docs/01_current_state_map.md", "docs/02_rules_and_assumptions.md",
                                  "docs/03_synthetic_data_and_mocks.md", "docs/04_agent_design.md",
                                  "docs/06_architecture.md", "docs/07_90_day_plan.md",
                                  "docs/00_service_card.md", "docs/00_service_card_ar.md", "docs/08_build_notes.md"])
def test_deliverable_documents_exist(path):
    assert (ROOT / path).exists() and (ROOT / path).stat().st_size > 500, path
