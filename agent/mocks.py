"""MOCK backend systems. None of these connect to anything real.

    MOCK Identity (UAE Pass / ICP)        -> identity_get_profile
    MOCK Document Verification Service    -> verification_verify
    MOCK Payment Gateway                  -> payment_charge (customer pays at once, used by tests and scenarios)
                                             payment_open + payment_pay (interactive payment window in the app)
    MOCK Case Management                  -> CaseStore

Realistic timing: every call takes `latency_s` seconds (default 0.3 s). A "timeout" makes the system
hang for `hang_s` seconds (default 6 s); the executor stops waiting after TOOL_TIMEOUT_SECONDS (3 s).

Failure injection (for scenario 5 and the demo):
    failures = {"verification": ["timeout"]}          first call hangs past the time limit, later calls work
    failures = {"verification": ["error", "error"]}   first two calls return a server error
    failures = {"verification": "malformed_always"}   every call returns a broken response
    failures = {"verification": "timeout_always"}     every call times out
Supported systems: identity, verification, payment, cases.
"""
from __future__ import annotations

import json
import re
import time
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .countries import COUNTRIES
from .config import DATA_DIR, ROOT, RUNTIME_DIR
from .models import CaseRecord, CaseStatus
from .payments import CardError, card_brand, check_card


class ToolTimeout(Exception):
    """The mock system did not answer within the time limit (raised by the executor)."""


class BackendError(Exception):
    """The mock system answered with an error, like HTTP 503 (simulated)."""


def load_synthetic(data_dir: Path = DATA_DIR) -> tuple[dict, dict]:
    personas = json.loads((data_dir / "personas.json").read_text(encoding="utf-8"))
    docs = json.loads((data_dir / "documents.json").read_text(encoding="utf-8"))
    return {p["persona_id"]: p for p in personas}, {d["doc_id"]: d for d in docs}


class CaseStore:
    """MOCK Case Management system: a JSON file so the staff screen sees every session's cases."""

    def __init__(self, path: Path = RUNTIME_DIR / "cases.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict[str, dict]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8") or "{}")

    def _save(self, data: dict) -> None:
        self.path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def create(self, record: dict[str, Any]) -> CaseRecord:
        data = self._load()
        ref = f"SYN-{1000 + len(data) + 1}"
        record.setdefault("created_at", datetime.now(timezone.utc).isoformat(timespec="seconds"))
        rec = CaseRecord(case_ref=ref, **record)
        data[ref] = rec.model_dump(mode="json")
        self._save(data)
        return rec

    def get(self, case_ref: str) -> Optional[CaseRecord]:
        raw = self._load().get(case_ref)
        return CaseRecord(**raw) if raw else None

    def update(self, case_ref: str, **changes: Any) -> CaseRecord:
        data = self._load()
        rec = CaseRecord(**data[case_ref]).model_copy(update=changes)
        data[case_ref] = rec.model_dump(mode="json")
        self._save(data)
        return rec

    def list(self, status: Optional[CaseStatus] = None) -> list[CaseRecord]:
        recs = [CaseRecord(**r) for r in self._load().values()]
        return [r for r in recs if status is None or r.status == status]


# Open test: a signed-in parent with no preset case. The presenter chooses the nationality on the (mock) UAE Pass
# record and builds any case from the whole synthetic document library or from uploaded files. Mixing documents of
# different applicants is allowed on purpose: the rules then show what they do with it (for example R-14 names).
OPEN_ID = "SYN-OPEN"


def open_persona(nationality: str = "") -> dict:
    """nationality "" = none selected yet: the record shows no nationality, so no visa exemption applies (R-04)."""
    return {"persona_id": OPEN_ID, "label": "SYNTHETIC DATA - FOR PROTOTYPE ONLY - NOT A REAL PERSON OR DOCUMENT",
            "story": "Open test: no preset case. Pick any documents from the library, upload your own files and "
                     "write anything, to build your own scenario.",
            "story_ar": "اختبار مفتوح: بلا حالة جاهزة. اختر أي مستندات من المكتبة أو ارفع ملفاتك واكتب ما تشاء لبناء "
                        "السيناريو الخاص بك.",
            "uae_pass_ref": "MOCK-UAEPASS-OPEN", "applicant_display_name": "Parent (synthetic UAE Pass account)",
            "student": {"student_ref": "SYN-STU-OPEN", "given_name": "Open", "family_name": "Test",
                        "given_name_ar": "اختبار", "family_name_ar": "مفتوح", "nationality": nationality,
                        "nationality_ar": COUNTRIES.get(nationality, nationality)}}


class MockBackend:
    def __init__(self, failures: Optional[dict] = None, case_store: Optional[CaseStore] = None,
                 data_dir: Path = DATA_DIR, latency_s: float = 0.0, hang_s: float = 6.0,
                 interactive_payments: bool = False, open_nationality: str = ""):
        self.personas, self.documents = load_synthetic(data_dir)
        self.personas[OPEN_ID] = open_persona(open_nationality)
        self.latency_s, self.hang_s = latency_s, hang_s
        self.failures = failures or {}
        self.calls: Counter = Counter()
        self.cases = case_store or CaseStore()
        self._receipts = 0
        # False: the customer completes the hosted payment page at once (assumption A-10; tests, scenarios).
        # True:  the app opens a payment window and the customer pays there (card or wallet, all simulated).
        self.interactive_payments = interactive_payments
        self._open_payments: dict[str, int] = {}

    # -------------------------------------------------- failure injection
    def _inject(self, system: str) -> str:
        plan = self.failures.get(system)
        n = self.calls[system]
        self.calls[system] += 1
        if plan is None:
            time.sleep(self.latency_s)
            return "ok"
        if isinstance(plan, str):
            mode = plan.replace("_always", "")
        else:
            mode = plan[n] if n < len(plan) else "ok"
        if mode == "timeout":
            time.sleep(self.hang_s)          # answers far too late; the executor has already given up
            return "ok"
        time.sleep(self.latency_s)
        if mode == "error":
            raise BackendError(f"{system} returned HTTP 503 Service Unavailable (simulated)")
        return mode  # "ok" or "malformed"

    # -------------------------------------------------- MOCK identity
    def identity_get_profile(self, persona_id: str) -> dict:
        mode = self._inject("identity")
        p = self.personas[persona_id]
        if mode == "malformed":
            return {"uae_pass_ref": p["uae_pass_ref"], "student": "??"}
        return {"uae_pass_ref": p["uae_pass_ref"],
                "applicant_display_name": p["applicant_display_name"],
                "student": dict(p["student"])}

    # -------------------------------------------------- real files uploaded from the computer
    UPLOAD_TYPES = {"passport", "emirates_id", "uae_visa", "school_certificate", "legal_translation",
                    "supporting_document"}

    def register_file(self, persona_id: str, data: bytes, file_name: str, doc_type: str, edition: str = "en",
                      upload_dir: Optional[Path] = None) -> str:
        """A real file chosen on the computer. If it is byte for byte one of this applicant's synthetic documents
        (for example downloaded from the portal and uploaded again), the verification service knows it. Any other
        file is unknown to the mock verification service: it is kept for the format and size checks (R-10) and
        verified as inconclusive, so a person decides (R-15). Nothing in the file is ever executed or trusted."""
        import hashlib
        if doc_type not in self.UPLOAD_TYPES:
            raise ValueError("unknown document type")
        digest = hashlib.sha256(data).hexdigest()
        for d in self.persona_documents(persona_id):
            p = ROOT / d["path"]
            if p.exists() and p.stat().st_size == len(data) and hashlib.sha256(p.read_bytes()).hexdigest() == digest:
                return d["doc_id"]
        # the parent's file name is never used: it could carry text aimed at the model; only the extension is kept
        ext = re.sub(r"[^a-z0-9]", "", Path(file_name or "").suffix.lower())[:5]
        safe = f"upload_{digest[:8]}" + (f".{ext}" if ext else "")
        folder = (upload_dir or RUNTIME_DIR / "uploads") / persona_id
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / safe
        path.write_bytes(data)
        doc_id = f"UP-{digest[:10].upper()}"
        try:
            rel = path.relative_to(ROOT).as_posix()
        except ValueError:
            rel = str(path)
        self.documents[doc_id] = {"doc_id": doc_id, "persona_id": persona_id, "edition": edition, "label": "UPLOADED",
                                  "doc_type": doc_type, "file_name": safe, "path": rel,
                                  "registry": {"authenticity": "inconclusive", "unknown": True},
                                  "extracted_text": ""}
        return doc_id

    # -------------------------------------------------- MOCK document verification
    def verification_verify(self, persona_id: str, doc_id: str) -> dict:
        mode = self._inject("verification")
        doc = self.documents.get(doc_id)
        if doc is None or (doc["persona_id"] != persona_id and persona_id != OPEN_ID):
            raise BackendError(f"document {doc_id} not found for this applicant (simulated 404)")
        if mode == "malformed":
            return {"doc_id": doc_id, "authenticity": 42, "unexpected": "<html>Gateway error</html>"}
        reg = doc["registry"]
        if reg.get("unknown"):
            # a file the verification service has no record of: nothing can be confirmed or read from it
            return {"doc_id": doc_id, "doc_type": doc["doc_type"], "authenticity": "inconclusive", "extracted_text": ""}
        out = {"doc_id": doc_id, "doc_type": doc["doc_type"],
               "authenticity": reg.get("authenticity", "verified"),
               "extracted_text": doc.get("extracted_text", "")}
        if doc["doc_type"] in {"passport", "emirates_id", "uae_visa"}:
            out.update(holder_name=reg["holder_name"], holder_name_ar=reg.get("holder_name_ar"),
                       number=reg["number"], expiry=reg["expiry"])
        elif doc["doc_type"] == "school_certificate":
            out.update(holder_name=reg.get("holder_name"), holder_name_ar=reg.get("holder_name_ar"), grade=reg["grade"],
                       academic_year=reg["academic_year"], language=reg["language"],
                       complete_year=reg["complete_year"], country_of_study=reg["country_of_study"],
                       grade_label=reg.get("grade_label"), school_name=reg.get("school_name"),
                       issued=reg.get("issued"), attested_by=reg.get("attested_by", []),
                       attestations={"education_authority": reg["attested_education_authority"],
                                     "mofa": reg["attested_mofa"],
                                     "uae_embassy": reg["attested_uae_embassy"]})
        elif doc["doc_type"] == "legal_translation":
            out.update(translates_doc_id=reg["translates_doc_id"], translation_language=reg.get("translation_language"))
        return out

    # -------------------------------------------------- MOCK payment gateway
    def payment_charge(self, session_id: str, amount_aed: int) -> dict:
        mode = self._inject("payment")
        self._receipts += 1
        if mode == "malformed":
            return {"receipt": None}
        return {"receipt_id": f"MOCK-RCPT-{session_id[-4:]}-{self._receipts:02d}",
                "amount_aed": amount_aed, "status": "PAID", "simulated": True, "method": "card"}

    def payment_open(self, session_id: str, amount_aed: int) -> dict:
        """Opens a payment window (like a hosted payment page). The customer pays in the app."""
        mode = self._inject("payment")
        if mode == "malformed":
            return {"payment": "?"}
        pid = f"MOCK-PAY-{session_id[-4:]}-{len(self._open_payments) + 1:02d}"
        self._open_payments[pid] = amount_aed
        return {"payment_id": pid, "amount_aed": amount_aed, "status": "PENDING", "simulated": True}

    def payment_pay(self, payment_id: str, method: str, card: Optional[dict] = None,
                    today: Optional[date] = None) -> dict:
        """The customer pays in the payment window. Card details are checked and then dropped:
        only the brand and last 4 digits are returned. Raises CardError when the payment is refused."""
        if payment_id not in self._open_payments:
            raise CardError("unknown_payment")
        if method == "card":
            check_card(card or {}, today or date.today())      # raises CardError (declined, invalid ...)
            last4 = "".join(ch for ch in card["number"] if ch.isdigit())[-4:]
            brand = card_brand(card["number"])
        elif method in ("apple_pay", "google_pay", "samsung_pay"):
            last4, brand = None, method
        else:
            raise CardError("unknown_method")
        amount = self._open_payments.pop(payment_id)
        self._receipts += 1
        return {"receipt_id": f"MOCK-RCPT-{payment_id[-7:]}-{self._receipts:02d}", "amount_aed": amount,
                "status": "PAID", "simulated": True, "method": method if method != "card" else f"card ({brand})",
                "card_last4": last4}

    # -------------------------------------------------- MOCK case management
    def cases_create(self, **record: Any) -> dict:
        mode = self._inject("cases")
        if mode == "malformed":
            return {"case": "created?"}          # nothing was stored; safe to retry
        return self.cases.create(record).model_dump(mode="json")

    @staticmethod
    def file_info(doc: dict) -> tuple[str, float]:
        """Real file check on the uploaded synthetic file: format from its first bytes, size on disk."""
        path = ROOT / doc["path"]
        head = path.read_bytes()[:5]
        fmt = "pdf" if head.startswith(b"%PDF-") else (path.suffix.lstrip(".").lower() or "unknown")
        return fmt, round(path.stat().st_size / (1024 * 1024), 3)

    def persona_documents(self, persona_id: str, edition: Optional[str] = None) -> list[dict]:
        """Files the synthetic customer has available to upload (used by the UI and scenarios).
        edition: "en" (English edition) or "ar" (Arabic edition); None = both."""
        if persona_id == OPEN_ID:      # the whole library, plus the files uploaded in the open test
            return [d for d in self.documents.values() if (edition is None or d.get("edition", "en") == edition)
                    and (not d["doc_id"].startswith("UP-") or d["persona_id"] == OPEN_ID)]
        return [d for d in self.documents.values() if d["persona_id"] == persona_id
                and (edition is None or d.get("edition", "en") == edition)]
