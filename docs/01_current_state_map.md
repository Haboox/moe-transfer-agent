# 01 Service Selection and Current State

## Service chosen

**Request for Equivalency Certificate for a Class Transfer from Outside the UAE (Grades 2 to 11)**
Source: `docs/00_service_card.md` (English card, copied from moe.gov.ae on 2026-10-10) and
`docs/00_service_card_ar.md` (Arabic card, saved on 2026-10-13). The service is offered in both languages,
so the agent is too.

### Why this service

| Case study requirement | How this service meets it |
|---|---|
| Real, published MoE e-service | Listed in the MoE e-services catalogue with its own service card |
| Transactional, not information only | Applicant submits documents, pays AED 50, receives a decision |
| Documents | 5 to 9 documents on the English card, 4 to 12 on the Arabic card (passport, Emirates ID, visa, two certificates, translations, supporting documents) |
| Validation | File rules, validity of ID documents, attestation chain, completeness of certificates |
| A decision | "General Education Certificate Equivalency Decision" |
| Small enough to explain | One document list for every applicant, no per curriculum branches |

### Services considered and rejected

| Service | Reason not chosen |
|---|---|
| Equivalency of Grade 12 certificate from abroad | 10+ curriculum branches, each with its own documents and grade thresholds |
| Equivalency of Grade 12 certificate within the UAE | Same curriculum branching |
| Attestation and transfer certificate services | One document and "Service Conditions: None", so almost nothing to validate |
| Class transfer equivalency within the UAE | Two purposes and attestation depends on the emirate; more branching than needed |
| Public school registration | Many applicant categories and a long document matrix |

## Current state journey (from the service card)

| Step | Who | What happens today (card wording) |
|---|---|---|
| 1 | Applicant | "Log in using UAE Pass" |
| 2 | Applicant | "Fill out the application and upload the required documents" |
| 3 | Applicant | "Pay the applicable fees" (AED 50) |
| 4 | MoE staff (implied) | Applications are reviewed; card states a service time of 30 working days |
| 5 | Applicant | "Receive the General Education Certificate Equivalency Decision via the email registered in the UAE Pass" |

## Pain points

These are **observations drawn from the card's own content**, not measured data. A real project
would confirm them with MoE service data (see the 90 day plan).

| # | Pain point | Evidence on the card | Who feels it |
|---|---|---|---|
| PP-1 | Applicant must work out which of 5 to 9 documents apply to them | Visa only "for non-GCC Nationals"; translation only "if the certificate was issued in language other than English or Arabic"; "5-9 documents" | Customer |
| PP-2 | Two separate attestation chains are easy to miss | "Attest all certificates from the Ministry of Education, educational authorities or councils in the country of study" and "Attest the last certificate ... from the Ministry of Foreign Affairs and the UAE Embassy" | Customer, staff |
| PP-3 | The published process has no step for fixing missing documents | Service Process lists 4 steps with no correction loop | Customer, staff |
| PP-4 | Long wait for the decision | "30 working days" | Customer |
| PP-5 | Applicants can pick the wrong service | The catalogue has separate equivalency services for Grade 12, transfers inside the UAE, and transfers from abroad | Customer, staff |
| PP-6 | Staff manually check every file against the same list | Every rule on the card is checkable from the documents | Staff |
| PP-7 | File format errors | "The accepted file format is PDF, and the size limit for each file is 5 MB"; "merge them into a single file" | Customer |
| PP-8 | The two language versions of the card differ | English: MoFA "in the country of study"; Arabic: MoFA "in the country that issued the certificate". English: "5-9 documents", Arabic: "4 to 12". English step 4: a *decision*; Arabic: the *certificate* | Customer (which version to trust), staff (which rule to apply) |
| PP-9 | Arabic and English speakers need the same answer | The service has an Arabic and an English card; parents write in either, or mix them | Customer |

## Target state: steps the agent will own

| # | Step | Owner | Pain points addressed |
|---|---|---|---|
| 1 | Understand the request, in Arabic or English, and confirm it is the right service (redirect Grade 12; Grade 1 is not covered) | Agent (model interprets, policy routes, code decides the reply language) | PP-5, PP-9 |
| 2 | Load the applicant profile from the identity system | Agent through mock identity tool | PP-1 |
| 3 | Explain exactly which documents apply to this applicant | Agent, grounded in the card | PP-1, PP-7 |
| 4 | Verify each uploaded document (attestations, validity, authenticity) | Agent through mock verification tool | PP-2, PP-6 |
| 5 | Run the business rules | Rules engine (deterministic, no model) | PP-2, PP-6, PP-7 |
| 6 | Ask for anything missing, then check again | Agent | PP-3 |
| 7 | Open the payment window for the AED 50 fee; the parent pays (card or wallet) | Agent through mock payment tool; the parent pays | |
| 8 | Create the case and give a reference | Agent through mock case tool, only after rules pass and fee paid | PP-4 (complete cases only) |
| 9 | Send anything the rules cannot decide to a human, with a summary | Agent and policy layer | PP-6 |

### Steps that stay with humans

* Any case the rules cannot decide (name mismatch, inconclusive verification, systems unavailable). A parent who asks for a person is given the toll-free number.
* The final decision on those escalated cases (Staff review screen).

### Out of scope for the prototype

* Real UAE Pass login, real payment (the payment window accepts only test cards), real email delivery, real document OCR.
* The 30 working day processing time (outcomes are immediate in the prototype).
