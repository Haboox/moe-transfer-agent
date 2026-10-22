# 07 Ninety Day Plan

The designed PDF of this plan is deliverable 05 (`05_90_Day_Plan.pdf`); this file holds the same content in plain text.
Case study asks for: *milestones, dependencies, owned risks, success measures.*

**Objective.** In 90 days, take the agent from a prototype on synthetic data to a controlled pilot on the real service, with real officers and a small share of real applicants, and decide on day 90, on evidence, whether to scale. The agent never gains decision power along the way: rules decide, the guard acts, officers approve.

## Gates

| Gate | Day | Passes when |
|---|---|---|
| G1 | 30 | rules signed off; baseline measured; hosting decided; data classification agreed; test access granted |
| G2 | 55 | four systems integrated in test, contract tests pass; evaluation set scores meet the guardrails; red team findings with no open high |
| G3 | 72 | shadow mode agrees with officers on every case the rules decide; Arabic reviewed; DPIA closed; officers trained |
| G4 | 90 | pilot guardrails held every day; success measures met or explained; recommendation to scale, extend or stop |

## Milestones

| | Day | Milestone | Done when | Owner |
|---|---|---|---|---|
| M1 | 5 | Mobilised | Steering group named, weekly cadence set, RACI agreed, this plan's risk register adopted | AI Center of Excellence |
| M2 | 15 | Service rules signed off | R-01 to R-15 and A-01 to A-20 confirmed or corrected by the service owner; the English and Arabic cards aligned (MoFA wording, document count, "decision" or "certificate"); every change shipped with its test | Equivalency Services |
| M3 | 20 | Current service baselined | From case data: share returned for missing documents, processing time, top rejection reasons, volume by grade and country, calls to the toll free number about this service | Data Office |
| M4 | 30 | Approvals in place (G1) | Data classification agreed; hosting decided (on premise or approved cloud); DPIA started; test environment access for the four systems | Information Security |
| M5 | 45 | Integrated in test | Identity, verification, payment and case management connected through the existing contracts; the prototype's contract and failure tests pass against them; circuit breaker added | IT Integration |
| M6 | 50 | Evaluation set ready | At least 200 anonymised cases with officer outcomes, in both languages, covering every rule result; the agent meets the guardrails on all of them | AI Center of Excellence |
| M7 | 55 | Security tested, Arabic reviewed (G2) | Red team exercise and penetration test, no open high finding; Arabic fixed messages approved by the Ministry; accessibility check passed in both languages | Information Security |
| M8 | 60 | Officers ready | Staff console used on historical cases; referral procedure written; officers trained | Equivalency Services |
| M9 | 72 | Shadow mode complete (G3) | The agent runs beside officers on live applications with no parent contact; agreement on every rule decided case; every disagreement explained | AI Center of Excellence |
| M10 | 90 | Pilot report, go or no go (G4) | Assistant offered to a small share of applicants; every referral and a daily sample reviewed; measures against the day 20 baseline; recommendation | Steering group |

## Dependencies

| | Dependency | Needed by | Owner | If late | Fallback |
|---|---|---|---|---|---|
| D1 | Service owner time to review the rules | day 15 | Equivalency Services | every later step slips | sign off the highest volume rules first |
| D2 | Anonymised historical cases with outcomes, and volume data | day 20 | Data Office | weaker baseline and evaluation | extend the synthetic set from case patterns |
| D3 | Approved hosting for the model and the agent | day 30 | Information Security and IT | no real data can be processed | a smaller model on an already approved environment |
| D4 | Test APIs for identity, verification, payment and case management | day 20 | IT Integration and system owners | integration slips | integrate the ready systems; keep mocks for the rest in test |
| D5 | Arabic language review | day 50 | Ministry communications | G2 slips | pilot in the reviewed language only |
| D6 | Legal and data protection review | day 65 | Legal | no pilot | extend shadow mode |
| D7 | Officers for shadow review and the pilot | days 55 to 90 | Equivalency Services | fewer cases compared | smaller daily sample, longer shadow |
| D8 | Payment reconciliation procedure | day 65 | Finance | pilot without payment | pilot the check and guidance steps first |

## Owned risks

| | Risk | Likelihood | Impact | Owner | Already in the design | Further action | Early warning |
|---|---|---|---|---|---|---|---|
| R1 | The model states an outcome, a requirement or a policy wrongly | 2 | 5 | AI Center of Excellence | Outcomes and status written from the record; card quoted word for word; reply checker | Weekly sample review of replies; every replaced reply investigated | replaced replies above 2% of turns |
| R2 | A rule is misread from the card, or the two card versions disagree | 3 | 5 | Equivalency Services | Every rule cites its card source; 20 assumptions labelled; rules unit tested | Sign off by day 15; a rule change ships with its test | any shadow disagreement on a rule decided case |
| R3 | Prompt injection through documents or chat | 3 | 4 | Information Security | No approval tool; guard and contracts; document text labelled untrusted; compromised model tests | Red team and penetration test before the pilot | security events per day |
| R4 | Integrations late, or real systems differ from the mock contracts | 4 | 4 | IT Integration | Mocks already behind real shaped contracts with failure modes | Contract tests from week 3; integrate the two ready systems first | contract test failures |
| R5 | Ministry system outages during the pilot | 3 | 3 | IT Integration | Time limit, one retry, never guess; paid referral to an officer | Circuit breaker per system; service levels agreed with system owners | backend failure rate |
| R6 | Personal data exposure | 2 | 5 | Data Office | Masking before logs; the model never sees names, card data or full numbers; leak scans | DPIA; log retention and access control; leak alerts | any leak scan finding |
| R7 | The model is too slow or too costly at scale | 4 | 3 | AI Center of Excellence | Provider is one setting; fixed replies need no model call | Load test in shadow mode; size hosting | 95th percentile reply above 10 s |
| R8 | Arabic dialects or mixed messages misread | 3 | 3 | AI Center of Excellence | Language and grades read by code; outcomes from the record, so a misread delays but never decides | Gulf, Levantine and Egyptian samples in the evaluation set | clarification rate by language |
| R9 | Officers overloaded by referrals | 3 | 3 | Equivalency Services | Referral only on grounds true in the record; missing items asked first; referrals paid for | Track referral share weekly; tune with the service owner | referral share above baseline plan |
| R10 | Payment reconciliation errors | 2 | 4 | Finance | One receipt per case; the agent never handles card data | Daily reconciliation in the pilot | unmatched receipts |
| R11 | Parents or staff do not trust the assistant | 3 | 3 | Equivalency Services | Clear labelling; toll free number always offered; officer decides every case | Usability sessions in both languages; satisfaction survey | drop off before submission |

## Success measures

Guardrails must hold every day of shadow mode and the pilot; one breach pauses the pilot until the cause is fixed and a test is added.

| Measure | Target by day 90 | How measured |
|---|---|---|
| Invented approvals or outcomes reaching a parent | zero | reply checker log and sample review |
| Actions outside the rules (submission without ELIGIBLE and fee, unpaid or ungrounded referral) | zero | automated audit trail checks |
| Document numbers or names in replies or logs | zero | automated leak scan on every log |
| Agreement with officers on cases the rules decide | 100% | shadow and pilot comparison |
| Arabic and English parity on paired cases | 100% same outcome | paired scenario runs on every release |
| Applications returned for missing documents | at least 30% below the day 20 baseline | case management data |
| Cases needing a person that reach one | 100% | referral log against officer review |
| Referrals the officer agrees were needed | 90% or more | officer feedback on each referral |
| Officer handling time per complete case | lower than baseline | case management timestamps |
| Calls to the toll free number about this service | lower than baseline | contact centre data |
| Tool success, excluding real outages | 99% or more | audit trail |
| Reply time, 95th percentile | 10 seconds or less | per turn timing in the audit trail |
| Assistant availability in service hours | 99% or more | monitoring |
| Parent satisfaction | at or above the current channel | short survey after the service, both languages |
| Requests started that end submitted or referred | higher than baseline | audit trail funnel |
