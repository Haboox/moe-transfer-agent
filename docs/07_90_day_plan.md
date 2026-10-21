# 07 Ninety Day Plan

Case study asks for: *milestones, dependencies, owned risks, success measures.*
Goal: move from this prototype to a controlled pilot of the agent on the real service with real staff,
without the agent ever deciding eligibility.

## Milestones

| Days | Milestone | Done when |
|---|---|---|
| 1 to 15 | **Confirm the rules with the service owner** | Every rule R-01 to R-15 and assumption A-01 to A-15 signed off or corrected by the Equivalency team; the differences between the Arabic and English cards (MoFA wording, document count, "decision" vs "certificate") settled and both cards aligned |
| 1 to 20 | **Baseline the current service** | Measured from case data: share of applications returned for missing documents, average processing time, top rejection reasons (replaces the card-based pain points in `01_current_state_map.md`) |
| 15 to 35 | **Security and data approvals** | Data classification agreed, hosting decision made (on-premise or approved cloud), threat model and penetration test of the agent and its tools scheduled |
| 20 to 45 | **Replace mocks with test integrations** | Identity, document verification, payment and case management connected in a test environment through the same tool contracts; contract tests pass against them |
| 30 to 50 | **Arabic review and accessibility** | The prototype already runs fully in Arabic (Arabic card, Arabic rule details, Arabic documents, right-to-left portal); the Ministry's Arabic language team reviews every fixed message, and an accessibility check (screen readers in Arabic and English, contrast) is passed |
| 40 to 60 | **Staff console and evaluation set** | Officers use the review screen on historical anonymised cases; an evaluation set of at least 200 real-pattern cases built with expected outcomes |
| 55 to 70 | **Shadow mode** | Agent runs beside officers on live applications without customer contact; its rule outcomes compared with officer decisions |
| 70 to 90 | **Limited pilot** | Agent available to a small share of applicants, every escalation and a sample of submissions reviewed daily; go or no-go report on day 90 |

## Dependencies

| Dependency | Needed for | Owner |
|---|---|---|
| Service owner time to review rules | Rule sign-off | Equivalency Services |
| API access to identity, verification, payment, case systems (test environments) | Replacing mocks | IT Integration |
| Hosting approval for the model | Any use beyond the prototype | Information Security |
| Anonymised historical cases | Baseline, evaluation set, shadow mode | Data Office |
| Officers available for review and feedback | Staff console, shadow mode | Equivalency Services |
| Legal and data protection review | Pilot | Legal |

## Owned risks

| Risk | Likelihood / impact | Owner | Mitigation already in the design | Further action |
|---|---|---|---|---|
| Model states an outcome or policy wrongly | Medium / High | AI Center of Excellence | Outcomes and requirements come from records (P-04, P-10); reply checker | Monitor every replaced reply; expand the evaluation set |
| Rule misread from the card | Medium / High | Equivalency Services | Each rule cites its source; assumptions labelled | Sign-off on day 15; rule changes need a test |
| Prompt injection through documents or chat | Medium / Medium | Information Security | No approve tool, guard, untrusted labelling, grounded escalation | Red-team exercise before the pilot |
| Backend outages | Medium / Medium | IT Integration | Time limit, one retry, escalation, no guessing | Agree service levels with system owners |
| Personal data exposure | Low / High | Data Office | Masking before logs and model; model sees no document numbers | Retention policy for logs; access control on the console |
| Local model too slow at scale | High / Medium | AI Center of Excellence | Provider is one setting | Load test in shadow mode; size hardware or approved hosted model |
| Arabic dialects and mixed Arabic-English messages misread | Medium / Medium | AI Center of Excellence | Language and grade checks by code; outcomes from records, so a misread can delay but not decide | Add Gulf, Levantine and Egyptian dialect samples to the evaluation set |
| Payment integration | Medium / High | IT Integration + Finance | Model cannot set the amount; card details never reach the agent | Connect the real MoE e-payment page in test; reconcile receipts daily in the pilot |
| Staff overloaded by escalations | Medium / Medium | Equivalency Services | Escalation only on true grounds (P-09); missing documents asked first | Track escalation rate weekly |

## Success measures (for the go or no-go decision on day 90)

| Measure | Target | How measured |
|---|---|---|
| Rule agreement with officers (shadow mode) | 100% on cases the rules decide | Agent rule outcome vs officer decision |
| Invented approvals or outcomes reaching a customer | Zero | Reply checker log, sample review |
| Correct escalation | 100% of cases needing a person reach one | Escalation log vs officer review |
| Applications returned for missing documents | Lower than the day 20 baseline | Case system data |
| Tool success (excluding injected failures) | 99% or better | Audit trail |
| Sensitive data in logs or replies | Zero | Automated leak checks on every log |
| Arabic and English parity | Same outcome for the same case in both languages, 100% | Paired scenario runs (S1 vs S1-AR ...) on every release |
| Applicant satisfaction | At or above the current channel | Post-service survey |
