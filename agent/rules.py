"""Business rules engine. Deterministic: no language model is involved here.

Each rule:
  * has an ID and a source (service card section or labelled ASSUMPTION), see docs/02_rules_and_assumptions.md
  * takes the VERIFIED inputs (uploads + verification results + identity profile)
  * returns PASS / FAIL / MISSING / REVIEW / NOT_APPLICABLE with a plain-language detail
    in English AND Arabic (written here, by code, so both languages say exactly the same thing)

`evaluate()` runs all rules and `combine_outcome()` turns the results into one outcome.
The same rules run whatever language the customer or the documents use: Arabic certificates are
accepted like English ones (Card: Required documents), and names are compared in the script they share.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable

from .language import normalize_name
from .models import (Outcome, RuleReport, RuleResult, RuleStatus, UploadedDocument,
                     VerificationResult)

GRADE_MIN, GRADE_MAX = 2, 11                                  # Card: About this service
GCC_NATIONALITIES = {"uae", "united arab emirates", "emirati", "saudi arabia", "saudi",
                     "kuwait", "kuwaiti", "qatar", "qatari", "bahrain", "bahraini",
                     "oman", "omani"}                         # ASSUMPTION A-03
ACCEPTED_LANGUAGES = {"english", "arabic"}                    # Card: Required documents
MAX_FILE_MB = 5.0                                             # Card: Notes
ALLOWED_FORMATS = {"pdf"}                                     # Card: Notes
MAX_SUPPORTING_DOCS = 2                                       # Card: Required documents
SINGLE_FILE_TYPES = {"passport", "emirates_id", "uae_visa"}   # Card: Notes (merge into a single file)
KNOWN_DOC_TYPES = {"passport", "emirates_id", "uae_visa", "school_certificate",
                   "legal_translation", "supporting_document"}

DOC_AR = {"passport": "جواز السفر", "emirates_id": "الهوية الإماراتية", "uae_visa": "الإقامة",
          "school_certificate": "الشهادة المدرسية", "legal_translation": "الترجمة القانونية",
          "supporting_document": "مرفق داعم"}
LANG_AR = {"french": "الفرنسية", "english": "الإنجليزية", "arabic": "العربية", "german": "الألمانية",
           "spanish": "الإسبانية", "urdu": "الأردية", "hindi": "الهندية"}

TITLES = {  # rule_id -> (English, Arabic)
    "R-01": ("Grade is within 2 to 11", "الصف ضمن نطاق الصف الثاني إلى الحادي عشر"),
    "R-02": ("Valid passport provided", "جواز سفر ساري المفعول"),
    "R-03": ("Valid Emirates ID provided", "هوية إماراتية سارية المفعول"),
    "R-04": ("UAE visa (non-GCC nationals only)", "الإقامة سارية المفعول (لغير أبناء دول مجلس التعاون)"),
    "R-05": ("Certificates of the previous 2 years", "شهادات آخر سنتين دراسيتين"),
    "R-06": ("Legal translation for non-English/Arabic certificates", "ترجمة قانونية للشهادات بغير العربية أو الإنجليزية"),
    "R-07": ("Certificates attested by the education authority (country of issue)",
             "تصديق الشهادات من جهة التعليم في بلد الإصدار"),
    "R-08": ("Last certificate attested by MoFA and UAE Embassy/Attache",
             "تصديق آخر شهادة من وزارة الخارجية وسفارة الدولة أو ملحق التعليم"),
    "R-09": ("Certificates cover a complete academic year", "شهادات نهائية لعام دراسي كامل"),
    "R-10": ("Files are PDF and at most 5 MB", "الملفات بصيغة PDF وبحجم 5 ميجابايت كحد أقصى"),
    "R-11": ("At most 2 additional supporting documents", "مرفقان داعمان كحد أقصى"),
    "R-13": ("One file per requirement", "ملف واحد لكل متطلب"),
    "R-14": ("Certificate names match the passport", "تطابق الاسم في الشهادات مع جواز السفر"),
    "R-15": ("Documents verified as authentic", "التحقق من صحة المستندات"),
}


@dataclass
class VerifiedInputs:
    nationality: str
    uploads: list[UploadedDocument]
    verifications: dict[str, VerificationResult]
    application_date: date

    def docs(self, doc_type: str) -> list[UploadedDocument]:
        return [u for u in self.uploads if u.doc_type == doc_type]

    def certificates(self) -> list[VerificationResult]:
        """Verified certificates, highest grade first."""
        certs = [self.verifications[u.doc_id] for u in self.docs("school_certificate")
                 if u.doc_id in self.verifications and self.verifications[u.doc_id].grade is not None]
        return sorted(certs, key=lambda v: v.grade or 0, reverse=True)


def is_gcc(nationality: str) -> bool:
    return (nationality or "").strip().lower() in GCC_NATIONALITIES


def _res(rule_id: str, status: RuleStatus, en: str, ar: str, source: str, title: tuple | None = None) -> RuleResult:
    t_en, t_ar = title or TITLES[rule_id]
    return RuleResult(rule_id=rule_id, title=t_en, title_ar=t_ar, status=status, detail=en, detail_ar=ar,
                      source=source)


NONE_YET = ("No verified certificate yet.", "لا توجد شهادة تم التحقق منها بعد.")


# ------------------------------------------------------------------ rules
def r01_grade_scope(inp: VerifiedInputs) -> RuleResult:
    s = "Card: About this service"
    certs = inp.certificates()
    if not certs:
        return _res("R-01", RuleStatus.NOT_APPLICABLE, *NONE_YET, s)
    g = certs[0].grade
    if GRADE_MIN <= g <= GRADE_MAX:
        return _res("R-01", RuleStatus.PASS, f"Last grade passed is {g}.", f"آخر صف اجتازه الطالب هو الصف {g}.", s)
    return _res("R-01", RuleStatus.FAIL,
                f"Last grade passed is {g}; this service covers Grades 2 to 11 only.",
                f"آخر صف اجتازه الطالب هو الصف {g}؛ هذه الخدمة تشمل الصفوف من الثاني إلى الحادي عشر فقط.", s)


_ID_LABELS = {"passport": ("Passport", "جواز السفر"), "emirates_id": ("Emirates ID", "الهوية الإماراتية"),
              "uae_visa": ("UAE visa", "الإقامة")}


def _identity_doc_rule(rule_id: str, doc_type: str, source: str, inp: VerifiedInputs) -> RuleResult:
    en, ar = _ID_LABELS[doc_type]
    docs = inp.docs(doc_type)
    if not docs:
        return _res(rule_id, RuleStatus.MISSING, f"{en} copy has not been uploaded.",
                    f"لم يتم إرفاق نسخة من {ar}.", source)
    v = inp.verifications.get(docs[0].doc_id)
    if v is None:
        return _res(rule_id, RuleStatus.MISSING, f"{en} has not been verified yet.",
                    f"لم يتم التحقق من {ar} بعد.", source)
    if v.expiry is None:
        return _res(rule_id, RuleStatus.FAIL, f"{en} expiry date could not be read.",
                    f"تعذرت قراءة تاريخ انتهاء {ar}.", source)
    d = v.expiry.isoformat()
    if v.expiry < inp.application_date:
        return _res(rule_id, RuleStatus.FAIL, f"{en} expired on {d}; a valid one is required.",
                    f"انتهت صلاحية {ar} بتاريخ {d}؛ يلزم مستند ساري المفعول.", source)
    return _res(rule_id, RuleStatus.PASS, f"{en} valid until {d}.", f"صلاحية {ar} حتى {d}.", source)


def r02_passport(inp):
    return _identity_doc_rule("R-02", "passport", "Card: Required documents; A-01, A-02", inp)


def r03_emirates_id(inp):
    return _identity_doc_rule("R-03", "emirates_id", "Card: Required documents; A-01, A-02", inp)


def r04_visa(inp):
    source = "Card: Required documents; A-01, A-02, A-03"
    if is_gcc(inp.nationality):
        return _res("R-04", RuleStatus.NOT_APPLICABLE,
                    f"Student nationality ({inp.nationality}) is GCC; no visa required.",
                    "جنسية الطالب من دول مجلس التعاون الخليجي؛ لا تلزم الإقامة.", source)
    res = _identity_doc_rule("R-04", "uae_visa", source, inp)
    if not (inp.nationality or "").strip() and res.status != RuleStatus.PASS:
        # no nationality on the record: no GCC exemption can be shown, so the card's visa line applies
        res.detail += " The identity record shows no nationality, so the GCC exemption cannot apply."
        res.detail_ar += " لا يُظهر سجل الهوية أي جنسية، لذلك لا ينطبق إعفاء مواطني دول مجلس التعاون."
    return res


def r05_two_years(inp: VerifiedInputs) -> RuleResult:
    s = "Card: Required documents; A-04"
    certs = inp.certificates()
    uploaded = len(inp.docs("school_certificate"))
    if uploaded == 0:
        return _res("R-05", RuleStatus.MISSING, "No school certificates uploaded; the last two years are required.",
                    "لم يتم إرفاق أي شهادة مدرسية؛ يلزم إرفاق شهادات آخر سنتين دراسيتين.", s)
    unreadable = [u for u in inp.docs("school_certificate")
                  if u.doc_id in inp.verifications and inp.verifications[u.doc_id].grade is None]
    if unreadable:
        return _res("R-05", RuleStatus.MISSING,
                    "A certificate could not be read by the verification service; please attach the issued certificate "
                    "as a clear PDF.",
                    "تعذر على خدمة التحقق قراءة إحدى الشهادات؛ يرجى إرفاق الشهادة الصادرة بصيغة PDF واضحة.", s)
    if len(certs) < uploaded:
        return _res("R-05", RuleStatus.MISSING, "Some certificates are not verified yet.",
                    "لم يتم التحقق من بعض الشهادات بعد.", s)
    top = certs[0].grade
    grades = {c.grade for c in certs}
    if len(certs) == 1:
        return _res("R-05", RuleStatus.MISSING,
                    f"Only one certificate (Grade {top}); the Grade {top - 1} certificate is also required.",
                    f"تم إرفاق شهادة واحدة فقط (الصف {top})؛ تلزم أيضاً شهادة الصف {top - 1}.", s)
    if top - 1 not in grades:
        return _res("R-05", RuleStatus.FAIL,
                    f"Certificates must be for Grade {top} and Grade {top - 1} (consecutive years).",
                    f"يجب أن تكون الشهادات للصف {top} والصف {top - 1} (سنتان متتاليتان).", s)
    return _res("R-05", RuleStatus.PASS, f"Certificates for Grade {top} and Grade {top - 1} provided.",
                f"تم إرفاق شهادتي الصف {top} والصف {top - 1}.", s)


def r06_translation(inp: VerifiedInputs) -> RuleResult:
    s = "Card: Required documents"
    certs = inp.certificates()
    needing = [c for c in certs if (c.language or "").lower() not in ACCEPTED_LANGUAGES]
    if not needing:
        if certs:
            return _res("R-06", RuleStatus.NOT_APPLICABLE, "All certificates are in English or Arabic.",
                        "جميع الشهادات باللغة العربية أو الإنجليزية.", s)
        return _res("R-06", RuleStatus.NOT_APPLICABLE, *NONE_YET, s)
    # A translation counts only if it is INTO English or Arabic (the two languages the card accepts)
    translated = {v.translates_doc_id for v in inp.verifications.values()
                  if v.doc_type == "legal_translation" and v.translates_doc_id
                  and (v.translation_language or "english").lower() in ACCEPTED_LANGUAGES}
    missing = [c for c in needing if c.doc_id not in translated]
    if missing:
        en = ", ".join(f"Grade {c.grade} ({c.language})" for c in missing)
        ar = "، ".join(f"الصف {c.grade} ({LANG_AR.get((c.language or '').lower(), c.language)})" for c in missing)
        return _res("R-06", RuleStatus.MISSING,
                    f"Legal translation into Arabic or English required for: {en}.",
                    f"تلزم ترجمة قانونية إلى العربية أو الإنجليزية لشهادة: {ar}.", s)
    return _res("R-06", RuleStatus.PASS, "Legal translations provided.", "تم إرفاق الترجمات القانونية.", s)


def r07_edu_attestation(inp: VerifiedInputs) -> RuleResult:
    s = "Card: Service Conditions (bullet 1); A-14"
    certs = inp.certificates()
    if not certs:
        return _res("R-07", RuleStatus.NOT_APPLICABLE, *NONE_YET, s)
    bad = [c for c in certs if not (c.attestations and c.attestations.education_authority)]
    if bad:
        return _res("R-07", RuleStatus.FAIL,
                    "Missing education authority attestation on: " + ", ".join(f"Grade {c.grade}" for c in bad) + ".",
                    "ينقص تصديق جهة التعليم على شهادة: " + "، ".join(f"الصف {c.grade}" for c in bad) + ".", s)
    return _res("R-07", RuleStatus.PASS, "All certificates attested by the education authority.",
                "جميع الشهادات مصدقة من جهة التعليم.", s)


def r08_last_cert_attestation(inp: VerifiedInputs) -> RuleResult:
    s = "Card: Service Conditions (bullet 2); Arabic card: MoFA of the issuing country"
    certs = inp.certificates()
    if not certs:
        return _res("R-08", RuleStatus.NOT_APPLICABLE, *NONE_YET, s)
    last = certs[0]
    a = last.attestations
    missing_en, missing_ar = [], []
    if not (a and a.mofa):
        missing_en.append("Ministry of Foreign Affairs")
        missing_ar.append("وزارة الخارجية في بلد الإصدار")
    if not (a and a.uae_embassy):
        missing_en.append("UAE Embassy or Education Attache")
        missing_ar.append("سفارة دولة الإمارات أو ملحق التعليم")
    if missing_en:
        return _res("R-08", RuleStatus.FAIL,
                    f"Grade {last.grade} certificate is missing attestation by: {' and '.join(missing_en)}.",
                    f"ينقص شهادة الصف {last.grade} تصديق: {' و'.join(missing_ar)}.", s)
    return _res("R-08", RuleStatus.PASS, f"Grade {last.grade} certificate fully attested.",
                f"شهادة الصف {last.grade} مصدقة بالكامل.", s)


def r09_complete_year(inp: VerifiedInputs) -> RuleResult:
    s = "Card: Service Conditions (bullet 3)"
    certs = inp.certificates()
    if not certs:
        return _res("R-09", RuleStatus.NOT_APPLICABLE, *NONE_YET, s)
    bad = [c for c in certs if c.complete_year is not True]
    if bad:
        return _res("R-09", RuleStatus.FAIL,
                    "Incomplete or interim statement for: " + ", ".join(f"Grade {c.grade}" for c in bad)
                    + "; a final certificate is required.",
                    "إفادة فصلية أو غير مكتملة لشهادة: " + "، ".join(f"الصف {c.grade}" for c in bad)
                    + "؛ تلزم شهادة نهائية للعام الدراسي.", s)
    return _res("R-09", RuleStatus.PASS, "All certificates are final, complete-year certificates.",
                "جميع الشهادات نهائية لعام دراسي كامل.", s)


def r10_file_rules(inp: VerifiedInputs) -> RuleResult:
    s = "Card: Required documents, Notes"
    if not inp.uploads:
        return _res("R-10", RuleStatus.NOT_APPLICABLE, "No files uploaded yet.", "لم يتم إرفاق أي ملف بعد.", s)
    bad = [u for u in inp.uploads
           if u.file_format.lower() not in ALLOWED_FORMATS or u.size_mb > MAX_FILE_MB]
    if bad:
        files = ", ".join(f"{u.file_name} ({u.file_format}, {u.size_mb} MB)" for u in bad)
        return _res("R-10", RuleStatus.FAIL, "These files must be PDF and 5 MB or smaller: " + files + ".",
                    "يجب أن تكون هذه الملفات بصيغة PDF وبحجم 5 ميجابايت أو أقل: " + files + ".", s)
    return _res("R-10", RuleStatus.PASS, "All files are PDF and within 5 MB.",
                "جميع الملفات بصيغة PDF وضمن 5 ميجابايت.", s)


def r11_supporting_limit(inp: VerifiedInputs) -> RuleResult:
    s = "Card: Required documents"
    n = len(inp.docs("supporting_document"))
    if n > MAX_SUPPORTING_DOCS:
        return _res("R-11", RuleStatus.FAIL,
                    f"{n} supporting documents uploaded; the maximum is {MAX_SUPPORTING_DOCS}.",
                    f"تم إرفاق {n} مرفقات داعمة؛ الحد الأقصى مرفقان.", s)
    en = {0: "No supporting documents.", 1: "One supporting document."}.get(n, f"{n} supporting documents.")
    return _res("R-11", RuleStatus.PASS, en + f" The maximum is {MAX_SUPPORTING_DOCS}.",
                f"عدد المرفقات الداعمة: {n}، والحد الأقصى مرفقان.", s)


def r13_single_file(inp: VerifiedInputs) -> RuleResult:
    s = "Card: Required documents, Notes"
    dupes = [d for d in sorted(SINGLE_FILE_TYPES) if len(inp.docs(d)) > 1]
    grades = [c.grade for c in inp.certificates()]
    dup_grades = sorted({g for g in grades if grades.count(g) > 1})
    if dupes or dup_grades:
        en = [d.replace("_", " ") for d in dupes] + [f"Grade {g} certificate" for g in dup_grades]
        ar = [DOC_AR[d] for d in dupes] + [f"شهادة الصف {g}" for g in dup_grades]
        return _res("R-13", RuleStatus.FAIL,
                    "More than one file for: " + ", ".join(en) + ". Please merge them into a single file.",
                    "أكثر من ملف لـ: " + "، ".join(ar) + ". يرجى دمجها في ملف واحد.", s)
    return _res("R-13", RuleStatus.PASS, "One file per requirement.", "ملف واحد لكل متطلب.", s)


def _same_person(cert: VerificationResult, passport: VerificationResult) -> bool | None:
    """Compare in the script both documents share: Arabic with Arabic, Latin with Latin.
    None = no common script, so the rules cannot compare (a person must)."""
    if cert.holder_name_ar and passport.holder_name_ar:
        return normalize_name(cert.holder_name_ar) == normalize_name(passport.holder_name_ar)
    if cert.holder_name and passport.holder_name:
        return normalize_name(cert.holder_name) == normalize_name(passport.holder_name)
    return None


def r14_name_match(inp: VerifiedInputs) -> RuleResult:
    s = "ASSUMPTION A-05"
    passports = inp.docs("passport")
    pv = inp.verifications.get(passports[0].doc_id) if passports else None
    certs = inp.certificates()
    if pv is None or not certs:
        return _res("R-14", RuleStatus.NOT_APPLICABLE, "Passport or certificates not verified yet.",
                    "لم يتم التحقق من جواز السفر أو الشهادات بعد.", s)
    bad = [c for c in certs if _same_person(c, pv) is not True]
    if bad:
        return _res("R-14", RuleStatus.REVIEW,
                    "Name on " + ", ".join(f"Grade {c.grade} certificate" for c in bad)
                    + " does not match the passport; a person must review this.",
                    "الاسم في " + "، ".join(f"شهادة الصف {c.grade}" for c in bad)
                    + " لا يطابق جواز السفر؛ يجب أن يراجع ذلك موظف.", s)
    return _res("R-14", RuleStatus.PASS, "Names match.", "الأسماء متطابقة.", s)


def r15_authenticity(inp: VerifiedInputs) -> RuleResult:
    s = "ASSUMPTION A-06"
    unclear = [v for v in inp.verifications.values() if v.authenticity != "verified"]
    if unclear:
        def en(v):
            return f"Grade {v.grade} certificate" if v.grade is not None else v.doc_type.replace("_", " ")

        def ar(v):
            return f"شهادة الصف {v.grade}" if v.grade is not None else DOC_AR.get(v.doc_type, v.doc_type)
        return _res("R-15", RuleStatus.REVIEW,
                    "Authenticity could not be confirmed for: " + ", ".join(en(v) for v in unclear)
                    + "; a person must review this.",
                    "تعذر التأكد من صحة: " + "، ".join(ar(v) for v in unclear) + "؛ يجب أن يراجع ذلك موظف.", s)
    if not inp.verifications:
        return _res("R-15", RuleStatus.NOT_APPLICABLE, "Nothing verified yet.", "لم يتم التحقق من أي مستند بعد.", s)
    return _res("R-15", RuleStatus.PASS, "All documents verified as authentic.",
                "تم التحقق من صحة جميع المستندات.", s)


RULES: list[Callable[[VerifiedInputs], RuleResult]] = [
    r01_grade_scope, r02_passport, r03_emirates_id, r04_visa, r05_two_years, r06_translation,
    r07_edu_attestation, r08_last_cert_attestation, r09_complete_year, r10_file_rules,
    r11_supporting_limit, r13_single_file, r14_name_match, r15_authenticity,
]
# R-12 (fee paid before submission) is enforced by the guard at submission time: agent/guard.py


def combine_outcome(results: list[RuleResult]) -> Outcome:
    """Fixed precedence, see docs/02_rules_and_assumptions.md."""
    by_id = {r.rule_id: r for r in results}
    if by_id.get("R-01") and by_id["R-01"].status == RuleStatus.FAIL:
        return Outcome.WRONG_SERVICE
    if any(r.status in (RuleStatus.MISSING, RuleStatus.FAIL) for r in results):
        return Outcome.NEEDS_INFO
    if any(r.status == RuleStatus.REVIEW for r in results):
        return Outcome.HUMAN_REVIEW
    return Outcome.ELIGIBLE


def evaluate(inp: VerifiedInputs) -> RuleReport:
    results = [rule(inp) for rule in RULES]
    return RuleReport(outcome=combine_outcome(results), results=results)


def stated_grade_in_scope(grade: int | None) -> bool | None:
    """Pre-check on the grade the customer TELLS us (policy P-06). None = unknown."""
    if grade is None:
        return None
    return GRADE_MIN <= grade <= GRADE_MAX
