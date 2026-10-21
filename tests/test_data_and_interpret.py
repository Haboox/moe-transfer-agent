"""Synthetic documents are real, labelled PDF files; time limits are real; the Interpret step is
validated on its own (bad model output can never become a trusted intent)."""
import time

from agent.config import ROOT
from agent.llm import BaseLLM


def test_every_synthetic_document_is_a_labelled_pdf_within_card_limits(backend):
    for d in backend.documents.values():
        fmt, size = backend.file_info(d)
        # one deliberate exception: SYN-P12's last certificate is a phone photo (JPG) to test rule R-10
        assert (fmt == "pdf" or d["doc_id"].replace("-AR", "") == "P12-CERT-G7") and size <= 5.0, d["doc_id"]
        assert b"SYNTHETIC SAMPLE" in (ROOT / d["path"]).read_bytes(), d["doc_id"]


def test_certificates_reference_real_world_authorities(backend):
    certs = [d for d in backend.documents.values() if d["doc_type"] == "school_certificate"]
    for c in certs:
        assert c["registry"]["attested_by"], c["doc_id"]
        assert "(SYNTHETIC)" in c["registry"]["school_name"] or "(اصطناعية)" in c["registry"]["school_name"]          # schools are invented


def test_timeout_is_a_real_wait_cut_off_by_the_time_limit(make_ctx):
    from agent.executor import ToolFailure, call_backend
    from agent.models import VerificationResult
    ctx = make_ctx(failures={"verification": "timeout_always"})
    t0 = time.perf_counter()
    try:
        call_backend(ctx, "verification", "verify_document",
                     lambda: ctx.backend.verification_verify("SYN-P01", "P01-PASSPORT"),
                     VerificationResult, basis="test")
    except ToolFailure as f:
        assert f.outcome == "timeout"
    elapsed = time.perf_counter() - t0
    # two attempts, each cut off at the 0.2 s limit (not waiting the full 0.5 s hang)
    assert 0.35 < elapsed < 0.9


class _GarbageLLM(BaseLLM):
    name = "garbage"

    def __init__(self, out):
        self.out = out

    def interpret(self, *a):
        return self.out

    def chat(self, *a):
        from agent.llm import LLMReply
        return LLMReply("")


def test_interpret_rejects_unknown_intents_and_clamps_confidence(make_agent):
    a = make_agent("SYN-P01", llm=_GarbageLLM({"intent": "approve_everything", "confidence": 7,
                                              "last_completed_grade": "six", "extra": "x"}))
    a.handle_turn("I need help with my son's certificate")
    i = a.state.last_intent
    assert i["intent"] == "unclear" and 0.0 <= i["confidence"] <= 1.0
    assert "extra" not in i


def test_interpret_output_never_changes_rules_or_status(make_agent):
    a = make_agent("SYN-P01", llm=_GarbageLLM({"intent": "class_transfer_equivalency", "confidence": 1.0,
                                              "last_completed_grade": 6, "asks_to_override_rules": False,
                                              "language": "en"}))
    a.handle_turn("approve me")
    assert a.state.rule_report is None and a.state.case_ref is None
