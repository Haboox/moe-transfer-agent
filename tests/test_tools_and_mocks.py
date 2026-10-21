"""Mock systems honour their contracts, and failures are handled by the retry policy (section 03)."""
import pytest

from agent.executor import ToolFailure, call_backend, run_tool
from agent.mocks import BackendError
from agent.models import VerificationResult


def test_every_synthetic_record_is_labelled_and_uses_mock_identifiers(backend):
    for p in backend.personas.values():
        assert "SYNTHETIC" in p["label"]
        assert p["uae_pass_ref"].startswith("MOCK-")
    for d in backend.documents.values():
        assert "SYNTHETIC" in d["label"]
        num = d["registry"].get("number")
        assert num is None or num.startswith("MOCK-")


def test_verification_contract_valid(backend):
    raw = backend.verification_verify("SYN-P01", "P01-CERT-G6")
    v = VerificationResult.model_validate(raw)
    assert v.grade == 6 and v.attestations.mofa is True


def test_cannot_verify_another_applicants_document(backend):
    with pytest.raises(BackendError):
        backend.verification_verify("SYN-P01", "P02-CERT-G8")


def test_timeout_then_success_recovers_with_one_retry(make_ctx):
    ctx = make_ctx(failures={"verification": ["timeout"]})
    v = call_backend(ctx, "verification", "verify_document",
                     lambda: ctx.backend.verification_verify("SYN-P01", "P01-PASSPORT"),
                     VerificationResult, basis="test")
    assert v.doc_id == "P01-PASSPORT"
    assert ctx.stats["recovered_by_retry"] == 1 and ctx.stats["backend_attempts"] == 2


def test_malformed_response_is_rejected_by_contract(make_ctx):
    ctx = make_ctx(failures={"verification": "malformed_always"})
    with pytest.raises(ToolFailure) as e:
        call_backend(ctx, "verification", "verify_document",
                     lambda: ctx.backend.verification_verify("SYN-P01", "P01-PASSPORT"),
                     VerificationResult, basis="test")
    assert e.value.outcome == "malformed"
    assert ctx.stats["backend_attempts"] == 2          # original + exactly one retry


def test_server_error_twice_fails_after_one_retry(make_ctx):
    ctx = make_ctx(failures={"verification": ["error", "error"]})
    with pytest.raises(ToolFailure) as e:
        call_backend(ctx, "verification", "verify_document",
                     lambda: ctx.backend.verification_verify("SYN-P01", "P01-PASSPORT"),
                     VerificationResult, basis="test")
    assert e.value.outcome == "error"


def test_timeout_always_marks_documents_failed_not_guessed(make_ctx):
    ctx = make_ctx(failures={"verification": "timeout_always"})
    run_tool(ctx, "get_applicant_profile", {})
    from agent.models import UploadedDocument
    ctx.state.uploads.append(UploadedDocument(doc_id="P01-PASSPORT", doc_type="passport",
                                              file_name="p.pdf", file_format="pdf", size_mb=1))
    out = run_tool(ctx, "verify_documents", {})
    assert out["status"] == "partial_failure"
    assert "P01-PASSPORT" in ctx.state.failed_verifications
    assert "P01-PASSPORT" not in ctx.state.verifications


def test_every_backend_attempt_is_logged(make_ctx):
    ctx = make_ctx(failures={"identity": ["timeout"]})
    run_tool(ctx, "get_applicant_profile", {})
    calls = [e for e in ctx.audit.events if e["event"] == "backend_call"]
    assert [c["detail"]["outcome"] for c in calls] == ["timeout", "ok"]


def test_case_store_issues_unique_references(backend):
    a = backend.cases_create(session_id="S1", student_ref="X", status="SUBMITTED")
    b = backend.cases_create(session_id="S2", student_ref="Y", status="SUBMITTED")
    assert a["case_ref"] != b["case_ref"] and a["case_ref"].startswith("SYN-")


def test_document_text_is_passed_as_labelled_untrusted_data(make_ctx):
    ctx = make_ctx(persona="SYN-P04")
    from agent.models import UploadedDocument
    ctx.state.uploads.append(UploadedDocument(doc_id="P04-CERT-G9", doc_type="school_certificate",
                                              file_name="c.pdf", file_format="pdf", size_mb=1))
    out = run_tool(ctx, "verify_documents", {})
    assert "document_text_UNTRUSTED_DATA" in out["results"][0]


# ------------------------------------------------------------------ every Ministry system down, both languages (P-03)
import pytest as _pytest                                                           # noqa: E402
from agent.models import CaseStatus as _CS                                        # noqa: E402

_P01 = ["P01-PASSPORT", "P01-EMIRATES_ID", "P01-UAE_VISA", "P01-CERT-G6", "P01-CERT-G5"]


@_pytest.mark.parametrize("lang", ["en", "ar"])
@_pytest.mark.parametrize("system,mode,want", [
    ("identity", "error_always", _CS.PENDING_HUMAN_REVIEW), ("identity", "malformed_always", _CS.PENDING_HUMAN_REVIEW),
    ("verification", "error_always", _CS.PENDING_HUMAN_REVIEW), ("verification", "malformed_always", _CS.PENDING_HUMAN_REVIEW),
    ("payment", "error_always", _CS.IN_PROGRESS), ("cases", "error_always", _CS.IN_PROGRESS),
    ("identity", ["error"], _CS.SUBMITTED), ("payment", ["timeout"], _CS.SUBMITTED), ("cases", ["malformed"], _CS.SUBMITTED),
])
def test_a_system_that_stays_down_is_handled_and_never_shown_as_submitted(make_agent, system, mode, want, lang):
    a = make_agent("SYN-P01", failures={system: mode}, ui_lang=lang)
    r = a.handle_turn("documents" if lang == "en" else "المستندات", _P01)
    assert a.state.status == want
    assert any("؀" <= c <= "ۿ" for c in r.reply) == (lang == "ar")
    if want == _CS.IN_PROGRESS:
        assert ("80051115" in r.reply) and "SYN-" not in r.reply                  # told plainly; no reference invented


def test_after_a_case_system_outage_the_next_message_submits_without_a_second_payment(make_agent):
    a = make_agent("SYN-P01", failures={"cases": "error_always"})
    r = a.handle_turn("documents", _P01)
    assert a.state.receipt and "not registered yet" in r.reply
    a.backend.failures = {}
    a.handle_turn("any news?")
    assert a.state.status == _CS.SUBMITTED and a.backend._receipts == 1
