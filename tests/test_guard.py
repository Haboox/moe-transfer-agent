"""The guard blocks unauthorised tools, bad parameters and out-of-order actions (section 04, scenario 6)."""
from agent.executor import run_tool
from agent.models import UploadedDocument
from agent.tools import TOOLS


def _upload_all(ctx, persona_prefix="P01"):
    for d in ctx.backend.persona_documents(ctx.state.persona_id, "en"):
        fmt, size = ctx.backend.file_info(d)
        ctx.state.uploads.append(UploadedDocument(doc_id=d["doc_id"], doc_type=d["doc_type"],
                                                  file_name=d["file_name"], file_format=fmt, size_mb=size))


def test_there_is_no_approval_tool():
    assert not any("approve" in name or "reject" in name or "decide" in name for name in TOOLS)


def test_unknown_tool_blocked(make_ctx):
    ctx = make_ctx()
    out = run_tool(ctx, "approve_application", {})
    assert out["status"] == "blocked" and out["policy"] == "P-01"


def test_extra_parameters_blocked(make_ctx):
    ctx = make_ctx()
    out = run_tool(ctx, "get_applicant_profile", {"persona_id": "SYN-P02"})
    assert out["status"] == "blocked" and out["policy"] == "P-02"


def test_invalid_enum_blocked(make_ctx):
    ctx = make_ctx()
    out = run_tool(ctx, "escalate_to_human", {"reason_code": "approve_now"})
    assert out["status"] == "blocked"


def test_non_object_arguments_blocked(make_ctx):
    assert run_tool(make_ctx(), "get_case_status", "drop table")["status"] == "blocked"


def test_evaluate_before_profile_blocked(make_ctx):
    ctx = make_ctx()
    out = run_tool(ctx, "evaluate_rules", {})
    assert out["status"] == "blocked" and "profile" in out["reason"]


def test_evaluate_before_verification_blocked(make_ctx):
    ctx = make_ctx()
    run_tool(ctx, "get_applicant_profile", {})
    _upload_all(ctx)
    out = run_tool(ctx, "evaluate_rules", {})
    assert out["status"] == "blocked" and "verify" in out["reason"]


def test_payment_before_eligible_blocked(make_ctx):
    ctx = make_ctx()
    out = run_tool(ctx, "request_payment", {})
    assert out["status"] == "blocked" and out["policy"] == "R-12"


def test_submit_before_payment_blocked(make_ctx):
    ctx = make_ctx()
    run_tool(ctx, "get_applicant_profile", {})
    _upload_all(ctx)
    run_tool(ctx, "verify_documents", {})
    assert run_tool(ctx, "evaluate_rules", {})["outcome"] == "ELIGIBLE"
    out = run_tool(ctx, "submit_application", {})
    assert out["status"] == "blocked" and out["policy"] == "R-12"


def test_new_upload_makes_rules_stale_and_blocks_payment(make_ctx):
    ctx = make_ctx()
    run_tool(ctx, "get_applicant_profile", {})
    _upload_all(ctx)
    run_tool(ctx, "verify_documents", {})
    run_tool(ctx, "evaluate_rules", {})
    ctx.state.rules_stale = True                      # what an upload does
    assert run_tool(ctx, "request_payment", {})["status"] == "blocked"


def test_full_happy_sequence_allowed(make_ctx):
    ctx = make_ctx()
    for name in ["get_applicant_profile"]:
        assert run_tool(ctx, name, {})["status"] == "ok"
    _upload_all(ctx)
    for name in ["verify_documents", "evaluate_rules", "request_payment", "submit_application"]:
        assert run_tool(ctx, name, {})["status"] == "ok", name
    assert ctx.state.case_ref.startswith("SYN-")


def test_no_actions_after_submission(make_ctx):
    ctx = make_ctx()
    run_tool(ctx, "get_applicant_profile", {})
    _upload_all(ctx)
    for name in ["verify_documents", "evaluate_rules", "request_payment", "submit_application"]:
        run_tool(ctx, name, {})
    assert run_tool(ctx, "escalate_to_human", {"reason_code": "other"})["status"] == "blocked"
    assert run_tool(ctx, "get_case_status", {})["status"] == "ok"


def test_verify_only_own_uploads(make_ctx):
    ctx = make_ctx()
    _upload_all(ctx)
    out = run_tool(ctx, "verify_documents", {"doc_ids": ["P02-CERT-G8"]})
    assert out["status"] == "blocked"


def test_blocked_calls_are_logged_with_policy(make_ctx):
    ctx = make_ctx()
    run_tool(ctx, "approve_application", {})
    ev = [e for e in ctx.audit.events if e["event"] == "tool_blocked"]
    assert ev and ev[0]["basis"] == "P-01"


# ---------------- P-09: escalation must be grounded (found in a live run: the model escalated a
# prompt-injection message as "customer_request" although nobody asked for a person)
def test_escalation_without_grounds_is_blocked(make_ctx):
    ctx = make_ctx()
    for reason in ["customer_request", "name_mismatch", "verification_inconclusive",
                   "system_unavailable", "other"]:
        out = run_tool(ctx, "escalate_to_human", {"reason_code": reason})
        assert out["status"] == "blocked" and out["policy"] == "P-09", reason


def test_a_request_for_a_person_never_refers_a_case(make_ctx):
    """P-09 (21 October): asking for a person gets the toll-free number; the model cannot refer the case for it."""
    ctx = make_ctx()
    ctx.state.last_intent = {"intent": "request_human"}
    out = run_tool(ctx, "escalate_to_human", {"reason_code": "customer_request"})
    assert out["status"] == "blocked" and "toll-free" in out["reason"]


def test_escalation_allowed_when_rule_says_review(make_ctx):
    ctx = make_ctx(persona="SYN-P03")
    run_tool(ctx, "get_applicant_profile", {})
    _upload_all(ctx)
    run_tool(ctx, "verify_documents", {})
    assert run_tool(ctx, "evaluate_rules", {})["outcome"] == "HUMAN_REVIEW"
    # D-06: a request that needs an officer is paid for first, like any submitted request
    blocked = run_tool(ctx, "escalate_to_human", {"reason_code": "name_mismatch"})
    assert blocked["status"] == "blocked" and "fee must be paid" in blocked["reason"]
    assert run_tool(ctx, "request_payment", {})["status"] == "ok"
    assert run_tool(ctx, "escalate_to_human", {"reason_code": "name_mismatch"})["status"] == "ok"
    rec = ctx.backend.cases.get(ctx.state.case_ref)
    assert rec.receipt_id == ctx.state.receipt.receipt_id and rec.status.value == "PENDING_HUMAN_REVIEW"


def test_a_system_failure_reaches_an_officer_without_payment(make_ctx):
    ctx = make_ctx(persona="SYN-P05")
    run_tool(ctx, "get_applicant_profile", {})
    _upload_all(ctx)
    ctx.state.failed_verifications = {ctx.state.uploads[0].doc_id: "timeout"}
    assert ctx.state.receipt is None
    assert run_tool(ctx, "escalate_to_human", {"reason_code": "system_unavailable"})["status"] == "ok"
