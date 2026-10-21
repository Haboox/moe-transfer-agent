"""Unit tests for every business rule, run WITHOUT any language model (case study section 02)."""
from datetime import date

import pytest

from agent import rules
from agent.models import (Attestations, Outcome, RuleResult, RuleStatus, UploadedDocument,
                          VerificationResult)

TODAY = date(2026, 10, 12)
NAME = "Alpha Testchild"


def up(doc_id, doc_type, fmt="pdf", size=1.0):
    return UploadedDocument(doc_id=doc_id, doc_type=doc_type, file_name=f"{doc_id}.{fmt}",
                            file_format=fmt, size_mb=size)


def idv(doc_id, doc_type, expiry="2030-01-01", holder=NAME, authenticity="verified"):
    return VerificationResult(doc_id=doc_id, doc_type=doc_type, authenticity=authenticity,
                              holder_name=holder, number="MOCK-P-1", expiry=date.fromisoformat(expiry))


def certv(doc_id, grade, language="English", edu=True, mofa=True, embassy=True, complete=True,
          holder=NAME, authenticity="verified"):
    return VerificationResult(doc_id=doc_id, doc_type="school_certificate", authenticity=authenticity,
                              holder_name=holder, grade=grade, academic_year="2025-2026",
                              language=language, complete_year=complete, country_of_study="Testland",
                              attestations=Attestations(education_authority=edu, mofa=mofa, uae_embassy=embassy))


def build(nationality="India", passport=True, eid=True, visa=True, certs=((6, {}), (5, {})),
          extra_uploads=(), extra_verifs=None, passport_kw=None, uploads_override=None):
    uploads, ver = [], {}
    if passport:
        uploads.append(up("PASS", "passport")); ver["PASS"] = idv("PASS", "passport", **(passport_kw or {}))
    if eid:
        uploads.append(up("EID", "emirates_id")); ver["EID"] = idv("EID", "emirates_id")
    if visa:
        uploads.append(up("VISA", "uae_visa")); ver["VISA"] = idv("VISA", "uae_visa")
    for g, kw in certs:
        did = f"C{g}{'x' if f'C{g}' in ver else ''}"
        uploads.append(up(did, "school_certificate")); ver[did] = certv(did, g, **kw)
    uploads += list(extra_uploads)
    ver.update(extra_verifs or {})
    return rules.VerifiedInputs(nationality=nationality, uploads=uploads_override or uploads,
                                verifications=ver, application_date=TODAY)


def status(report, rule_id):
    return next(r.status for r in report.results if r.rule_id == rule_id)


def test_complete_application_is_eligible():
    rep = rules.evaluate(build())
    assert rep.outcome == Outcome.ELIGIBLE
    assert all(r.status in (RuleStatus.PASS, RuleStatus.NOT_APPLICABLE) for r in rep.results)


# ---------- R-01 grade scope
@pytest.mark.parametrize("top,expected", [(2, RuleStatus.PASS), (11, RuleStatus.PASS),
                                          (12, RuleStatus.FAIL), (1, RuleStatus.FAIL)])
def test_r01_grade_scope(top, expected):
    rep = rules.evaluate(build(certs=((top, {}), (top - 1, {}))))
    assert status(rep, "R-01") == expected


def test_r01_fail_gives_wrong_service():
    assert rules.evaluate(build(certs=((12, {}), (11, {})))).outcome == Outcome.WRONG_SERVICE


# ---------- R-02 / R-03 identity documents
def test_r02_missing_passport():
    rep = rules.evaluate(build(passport=False))
    assert status(rep, "R-02") == RuleStatus.MISSING and rep.outcome == Outcome.NEEDS_INFO


def test_r02_expired_passport():
    rep = rules.evaluate(build(passport_kw={"expiry": "2026-10-11"}))
    assert status(rep, "R-02") == RuleStatus.FAIL


def test_r02_expiring_today_is_still_valid():
    assert status(rules.evaluate(build(passport_kw={"expiry": "2026-10-12"})), "R-02") == RuleStatus.PASS


def test_r03_missing_emirates_id():
    assert status(rules.evaluate(build(eid=False)), "R-03") == RuleStatus.MISSING


# ---------- R-04 visa only for non-GCC
def test_r04_non_gcc_needs_visa():
    assert status(rules.evaluate(build(nationality="Egypt", visa=False)), "R-04") == RuleStatus.MISSING


@pytest.mark.parametrize("nat", ["Oman", "Saudi Arabia", "UAE", "kuwait", "Qatar", "Bahrain"])
def test_r04_gcc_does_not_need_visa(nat):
    rep = rules.evaluate(build(nationality=nat, visa=False))
    assert status(rep, "R-04") == RuleStatus.NOT_APPLICABLE and rep.outcome == Outcome.ELIGIBLE


# ---------- R-05 two consecutive years
def test_r05_only_one_certificate():
    assert status(rules.evaluate(build(certs=((6, {}),))), "R-05") == RuleStatus.MISSING


def test_r05_no_certificates():
    assert status(rules.evaluate(build(certs=())), "R-05") == RuleStatus.MISSING


def test_r05_non_consecutive_years():
    assert status(rules.evaluate(build(certs=((6, {}), (4, {})))), "R-05") == RuleStatus.FAIL


# ---------- R-06 translation
def test_r06_french_without_translation():
    rep = rules.evaluate(build(certs=((6, {"language": "French"}), (5, {}))))
    assert status(rep, "R-06") == RuleStatus.MISSING


def test_r06_french_with_translation():
    tr = VerificationResult(doc_id="T6", doc_type="legal_translation", authenticity="verified",
                            translates_doc_id="C6")
    rep = rules.evaluate(build(certs=((6, {"language": "French"}), (5, {})),
                               extra_uploads=[up("T6", "legal_translation")], extra_verifs={"T6": tr}))
    assert status(rep, "R-06") == RuleStatus.PASS and rep.outcome == Outcome.ELIGIBLE


def test_r06_arabic_needs_no_translation():
    assert status(rules.evaluate(build(certs=((6, {"language": "Arabic"}), (5, {})))), "R-06") \
        == RuleStatus.NOT_APPLICABLE


# ---------- R-07 / R-08 attestation
def test_r07_education_authority_missing_on_older_certificate():
    assert status(rules.evaluate(build(certs=((6, {}), (5, {"edu": False})))), "R-07") == RuleStatus.FAIL


def test_r08_last_certificate_needs_mofa():
    assert status(rules.evaluate(build(certs=((6, {"mofa": False}), (5, {})))), "R-08") == RuleStatus.FAIL


def test_r08_last_certificate_needs_embassy():
    assert status(rules.evaluate(build(certs=((6, {"embassy": False}), (5, {})))), "R-08") == RuleStatus.FAIL


def test_r08_older_certificate_does_not_need_mofa():
    """The card asks MoFA + Embassy only on 'the last certificate that the student passed'."""
    assert status(rules.evaluate(build(certs=((6, {}), (5, {"mofa": False, "embassy": False})))), "R-08") \
        == RuleStatus.PASS


# ---------- R-09 complete year
def test_r09_interim_statement_rejected():
    assert status(rules.evaluate(build(certs=((6, {"complete": False}), (5, {})))), "R-09") == RuleStatus.FAIL


# ---------- R-10 file rules
def test_r10_non_pdf():
    inp = build()
    inp.uploads[0] = up("PASS", "passport", fmt="jpg")
    assert status(rules.evaluate(inp), "R-10") == RuleStatus.FAIL


def test_r10_too_large():
    inp = build()
    inp.uploads[0] = up("PASS", "passport", size=5.1)
    assert status(rules.evaluate(inp), "R-10") == RuleStatus.FAIL


def test_r10_exactly_5mb_ok():
    inp = build()
    inp.uploads[0] = up("PASS", "passport", size=5.0)
    assert status(rules.evaluate(inp), "R-10") == RuleStatus.PASS


# ---------- R-11 supporting documents
def test_r11_three_supporting_documents():
    extra = [up(f"SUP{i}", "supporting_document") for i in range(3)]
    assert status(rules.evaluate(build(extra_uploads=extra)), "R-11") == RuleStatus.FAIL


def test_r11_two_supporting_documents_ok():
    extra = [up(f"SUP{i}", "supporting_document") for i in range(2)]
    assert status(rules.evaluate(build(extra_uploads=extra)), "R-11") == RuleStatus.PASS


# ---------- R-13 one file per requirement
def test_r13_two_passport_files():
    inp = build(extra_uploads=[up("PASS2", "passport")])
    assert status(rules.evaluate(inp), "R-13") == RuleStatus.FAIL


def test_r13_two_certificates_same_grade():
    assert status(rules.evaluate(build(certs=((6, {}), (6, {}), (5, {})))), "R-13") == RuleStatus.FAIL


# ---------- R-14 / R-15 need a human
def test_r14_name_mismatch_goes_to_human():
    rep = rules.evaluate(build(certs=((6, {"holder": "Alfa Testkid"}), (5, {}))))
    assert status(rep, "R-14") == RuleStatus.REVIEW and rep.outcome == Outcome.HUMAN_REVIEW


def test_r14_name_comparison_ignores_case_and_spacing():
    assert status(rules.evaluate(build(certs=((6, {"holder": "  alpha   TESTCHILD "}), (5, {})))), "R-14") \
        == RuleStatus.PASS


def test_r15_inconclusive_authenticity_goes_to_human():
    rep = rules.evaluate(build(certs=((6, {"authenticity": "inconclusive"}), (5, {}))))
    assert status(rep, "R-15") == RuleStatus.REVIEW and rep.outcome == Outcome.HUMAN_REVIEW


# ---------- combining results
def _r(rid, st):
    return RuleResult(rule_id=rid, title="t", status=st, detail="d", source="s")


def test_missing_info_is_asked_before_human_review():
    out = rules.combine_outcome([_r("R-02", RuleStatus.MISSING), _r("R-14", RuleStatus.REVIEW)])
    assert out == Outcome.NEEDS_INFO


def test_wrong_service_beats_everything():
    out = rules.combine_outcome([_r("R-01", RuleStatus.FAIL), _r("R-02", RuleStatus.MISSING)])
    assert out == Outcome.WRONG_SERVICE


def test_every_rule_has_a_source():
    for r in rules.evaluate(build()).results:
        assert r.source.startswith(("Card:", "ASSUMPTION")), r.rule_id


def test_stated_grade_precheck():
    assert rules.stated_grade_in_scope(12) is False
    assert rules.stated_grade_in_scope(7) is True
    assert rules.stated_grade_in_scope(None) is None
