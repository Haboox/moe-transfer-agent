# 07 Ninety Day Plan

The designed PDF of this plan is deliverable 05 (`05_90_Day_Plan.pdf`); this file holds the same content in plain text.
Case study asks for: *milestones, dependencies, owned risks, success measures.*

**Objective.** In 90 days, take the class transfer equivalency agent from a prototype on synthetic data to a limited pilot with real applicants, real officers and real Ministry systems, and decide on day 90, on evidence, whether to scale it. Along the way the agent gains real systems and real evidence, never decision power: the rules decide, the guard controls every action, and officers approve.

## Why now

* **The national direction.** On 18 May 2026 the UAE Cabinet set the aim of running half of federal government services and operations on agentic AI within two years, and asked every ministry to form a team, led by its minister, that sets targets and measures [1]. This plan gives that team one service with a measured, controlled path and measures it can reuse.
* **The rules for doing it responsibly.** The UAE Charter for the Development and Use of AI asks for human oversight, safety, data privacy, transparency, and governance and accountability [2]. The design already keeps an officer on every decision and logs every action; the plan keeps it that way.
* **A clear gain for parents and officers.** The published process has no step for fixing missing documents, so a gap is found only when an officer checks the file. The agent checks every rule before submitting: parents learn at once exactly what is missing, and officers receive complete requests.

## Phases and gates

| Phase | Work | Gate |
|---|---|---|
| Days 1 to 30: confirm and approve | The service owner confirms the rules; the current service is measured; data is classified and hosting in the UAE approved; test access to the four systems granted | G1, day 30: approved route to real data |
| Days 31 to 60: connect and harden | The four systems connected in test behind the same contracts; a hosted model chosen on a bilingual evaluation set; security testing; Arabic wording approved | G2, day 60: ready for shadow mode |
| Days 61 to 90: prove it | Shadow mode beside officers on live applications (days 61 to 75), then a limited, opt in pilot with real applicants (days 76 to 90) | G3, day 75: ready for applicants; G4, day 90: scale, extend or stop |

**Workstreams (Figure 1 in the PDF)**

| Workstream | Days |
|---|---|
| Governance and rules | 1 to 20: team, rules signed off; 21 to 90: weekly steering and change control |
| Data and evaluation | 1 to 25: baseline from case data; 26 to 55: bilingual evaluation set |
| Security and privacy | 1 to 30: classification, hosting route; 31 to 60: privacy and security testing; 61 to 75: pilot sign offs |
| Integrations | 5 to 30: test access requested; 31 to 55: 4 systems connected in test |
| Agent and model | 31 to 60: hosted model, monitoring, circuit breaker |
| Officers and Arabic | 31 to 55: Arabic review, staff console; 56 to 75: officer training |
| Shadow mode | 61 to 75: beside officers |
| Limited pilot | 76 to 90: small opt in group |

| Gate | Passes when | Decided by |
|---|---|---|
| G1, day 30 | rules and assumptions confirmed; baseline measured; data classified; hosting in the UAE approved; test access to the four systems granted | Steering group |
| G2, day 60 | four systems working in test and contract tests passing; every guardrail met on the evaluation set, in both languages; security testing with no open high finding; Arabic wording approved | Steering group with Information security |
| G3, day 75 | every disagreement with officers in shadow mode explained and closed; officers trained; privacy assessment closed; the switch off tested | Steering group with Legal |
| G4, day 90 | guardrails held every day of the pilot; measures met or explained; a recommendation to scale, extend or stop | Steering group |

If a gate is not met, the work before it continues and the dates move; nothing goes live early. The most likely delay is approvals (risk 1); then shadow mode runs longer and the pilot starts after day 90, and the day 90 decision is about starting it.

## Milestones

| | Day | Milestone | Done when | Owner |
|---|---|---|---|---|
| M1 | 5 | Team and governance in place | steering group named, weekly meeting set, an owner for every risk and dependency | AI CoE |
| M2 | 20 | Service rules confirmed | R-01 to R-15 and A-01 to A-20 confirmed or corrected by the service owner; the differences between the English and Arabic cards settled; every change shipped with its test | Service owner |
| M3 | 25 | Current service measured | monthly volume by grade and country; share of requests returned for missing or wrong documents; time to decision; main return reasons; calls about this service | Data and privacy |
| M4 | 30 | Approved route to real data (G1) | data classified; hosting in the UAE approved; test access granted to the four systems; privacy assessment started | Information security |
| M5 | 55 | Systems connected in test | four adapters behind the existing contracts; the prototype's contract and failure tests pass against them; a circuit breaker per system | IT integration |
| M6 | 55 | Model chosen on evidence | shortlisted models hosted in the UAE scored on an evaluation set of at least 200 past cases with officer outcomes, in both languages, covering every rule result; every guardrail met | AI CoE |
| M7 | 60 | Ready for shadow mode (G2) | security testing with no open high finding; Arabic wording approved; accessibility to WCAG 2.1 AA in both languages | Information security |
| M8 | 70 | Officers ready | staff console used on past cases; referral procedure written; officers trained | Service owner |
| M9 | 75 | Shadow mode complete (G3) | every disagreement with officers explained and closed; privacy assessment closed; the switch off tested | AI CoE |
| M10 | 90 | Pilot report and decision (G4) | guardrails held every day; measures compared with the baseline; recommendation to scale, extend or stop | Steering group |

M6: the shortlist includes Arabic capable models developed in the UAE, such as Falcon Arabic (Technology Innovation Institute) [10] and Jais (Inception) [11], beside the open model the prototype uses. The agent reaches every model through one interface, so each is tested on the same evaluation set, tool calling included, and the choice is made on measured results. M7: WCAG 2.1 AA is the level the UAE Design System asks of federal entities [7].

**Proposed core team:** product owner from the equivalency service (part time); AI engineer, owner of the agent (full time); integration engineer (full time); test engineer (full time); security reviewer (part time); Arabic content reviewer and data analyst (part time).

## Dependencies

| | The plan needs | By | From | If it is late | Fallback |
|---|---|---|---|---|---|
| 1 | Service owner time to confirm the rules and assumptions | day 20 | Service owner | every later step slips | confirm the rules that decide most cases first |
| 2 | Past cases with outcomes, anonymised, and volume data | day 25 | Data and privacy | a weaker baseline and evaluation set | build the evaluation set with officers from recent cases |
| 3 | Approved hosting in the UAE for the model and the agent | day 30 | Information security, IT | no real data can be used | an open model on an environment already approved |
| 4 | Test access to identity, verification, payment and case management | day 30 | IT integration, system owners | integration slips | connect the ready systems first; keep mocks for the rest in test |
| 5 | Arabic wording review | day 55 | Communications | G2 slips | pilot in the reviewed language first |
| 6 | Privacy and legal sign off | day 72 | Legal, Data and privacy | no pilot | extend shadow mode |
| 7 | Officers' time for shadow review and the pilot | days 61 to 90 | Service owner | fewer cases compared | a smaller daily sample, a longer shadow mode |
| 8 | Payment reconciliation procedure | day 72 | Finance | pilot without payment | pilot the checking and guidance; payment in the current channel |

**Hosting (dependency 3).** The model and the agent run inside the UAE on an environment the Ministry has approved, for example the federal cloud run by TDRA (FEDnet) [5]. Under the National Cloud Security Policy of the UAE Cyber Security Council [3], data classified confidential or restricted must stay within the UAE [4]. The federal personal data law excludes government entities and government data [8], so the privacy assessment follows the Ministry's own data policies.

**Sign in (dependency 4).** The service already signs parents in with UAE Pass, so the assistant should sit inside the Ministry's existing signed in session. If it needs its own UAE Pass client, onboarding runs in four phases: initiation, development in staging, an assessment with recorded test scenarios, and go live [6]. That request would start in week 1.

The critical path runs through dependencies 1, 3 and 4 to G2, and dependency 6 to G3.

## Owned risks (likelihood x impact, 1 to 5)

| | Risk | Score | Owner | Already in the design | Next | Warning sign |
|---|---|---|---|---|---|---|
| 1 | Approvals for hosting, security and privacy take longer than planned | 4 x 4 = 16 | Information security | Synthetic data only until approval; the agent is not tied to one model and already runs a local open one | Requests started in week 1; use an environment already approved for the Ministry if one fits | no hosting decision by day 25 |
| 2 | Real systems arrive late, or differ from the mock contracts | 4 x 4 = 16 | IT integration | Mocks sit behind contracts with realistic failures; every answer is checked | Contract tests from day 31; connect the ready systems first | no test access by day 30 |
| 3 | A rule is misread, or the English and Arabic cards disagree | 3 x 5 = 15 | Service owner | Every rule cites its card source; 20 labelled assumptions; the card differences documented; rules unit tested | Sign off by day 20; every change ships with its test | any shadow disagreement on a case the rules decided |
| 4 | Prompt injection or misuse through documents or chat | 3 x 4 = 12 | Information security | No approval tool; guard and contracts; document text treated as data; compromised model tests | Red team and penetration test before shadow mode | security events rising |
| 5 | The model states something wrong: an outcome, a requirement or a fact | 2 x 5 = 10 | AI CoE | Outcomes and requirements written from the record and the card; reply checker; fixed answers | Daily sample review in shadow mode and the pilot; every replaced reply investigated | replaced replies rising week to week |
| 6 | Personal data exposed in replies or logs | 2 x 5 = 10 | Data and privacy | Masking before logs; the model never gets names, card data or full numbers; leak search | Privacy assessment; retention and access rules for logs; leak alerts | any leak search finding |
| 7 | Ministry systems go down during the pilot | 3 x 3 = 9 | IT integration | Time limit, one retry, never guess; paid referral; the toll free number | Circuit breaker per system; service levels agreed with system owners | failure rate per system |
| 8 | Replies too slow or too costly on the hosted model | 3 x 3 = 9 | AI CoE | Fixed replies need no model call; a step limit; the model is one setting | Load test in shadow mode; size the hosting | 95th percentile reply time above target |
| 9 | Arabic dialects or mixed messages misread | 3 x 3 = 9 | AI CoE | Language and grade read by code; outcomes from the record, so a misread can delay but never decide | Gulf, Levantine and Egyptian phrasing in the evaluation set | clarification questions by language |
| 10 | Parents or staff do not trust or use the assistant | 3 x 3 = 9 | Service owner | Replies show their source; the toll free number always offered; officers decide every case | Usability sessions in both languages; a short survey | drop off before submission |
| 11 | Payment reconciliation errors | 2 x 4 = 8 | Finance | One receipt per case; the agent never handles card data | Daily reconciliation in the pilot | unmatched receipts |
| 12 | Officers receive too many referrals | 2 x 3 = 6 | Service owner | Referral only on grounds true in the record; missing items asked for first | Weekly review of the referral share | referral share above today's share of exceptions |

Security testing covers the OWASP Top 10 for LLM Applications [9]; `docs/06_architecture.md` and deliverable 03 map each item to the prototype.

## Success measures

Guardrails must hold every day of shadow mode and the pilot: one breach pauses the pilot until the cause is fixed and a test is added. Service measures are compared with the day 25 baseline at the day 90 decision. Targets marked proposed are confirmed with the service owner at G1, once the baseline is known.

**Guardrails: must hold every day**

| Measure | Target | How it is measured | How often |
|---|---|---|---|
| An outcome, approval or requirement not backed by the record reaching a parent | zero | reply checker log; daily sample review | daily |
| A case submitted without passing rules and a paid fee, or referred without grounds or a fee | zero | automatic check of the audit trail | daily |
| A document number or a name in a reply or a log | zero | leak search on every log | daily |
| Different outcomes for the same case in Arabic and English | zero | paired evaluation cases | every release |

**Shadow mode and pilot quality**

| Measure | Target | How it is measured | How often |
|---|---|---|---|
| Disagreements with officers on cases the rules decide | every one explained and closed before G3 | shadow comparison | every case |
| Cases needing a person that reach one | all of them | referral log against officer review | weekly |
| Referrals the officer agrees were needed | 9 in 10 or more (proposed) | officer feedback on each referral | weekly |

**Service, against the baseline**

| Measure | Target | How it is measured | How often |
|---|---|---|---|
| Requests submitted through the agent that come back for a document the rules check | none: the agent cannot submit them | case management data | weekly |
| Officer time per complete request | lower than the baseline | case management timestamps | weekly |
| Calls to the toll free number about this service | lower than the baseline | contact centre data | monthly |
| Requests started that end submitted or referred | higher than the baseline | audit trail | weekly |

**Reliability and experience**

| Measure | Target | How it is measured | How often |
|---|---|---|---|
| Tool calls that succeed, real outages excluded | 99% or more (proposed) | audit trail | daily |
| Reply time, 95th percentile | 15 seconds or less (proposed) | timings in the audit trail | daily |
| Parent satisfaction | at or above the current channel | short survey, both languages | weekly |
| Accessibility | WCAG 2.1 AA, both languages | accessibility review | before G2 |

## Governance

| Work | AI CoE | Service owner | IT integration | Information security | Data and privacy | Legal | Finance |
|---|---|---|---|---|---|---|---|
| Agent, guard, policies, evaluation | A R | C | C | C |  |  |  |
| Service rules and assumptions | R | A |  |  |  | C |  |
| Integrations and contracts | C |  | A R | C |  |  | C |
| Hosting and security testing | R |  | C | A | C | C |  |
| Data, baseline, privacy assessment | R | C |  | C | A | C |  |
| Officer procedures and training | C | A R |  |  |  |  |  |
| Payment reconciliation |  | C | C |  |  |  | A R |
| Gate decisions | R | A | C | C | C | C | C |

A: accountable. R: responsible. C: consulted. The steering group is chaired by the service owner and reports to the Ministry's agentic AI team.

* **Weekly steering:** progress against milestones, dependencies, risk warning signs, decisions needed.
* **Daily pilot review:** every referral and a sample of submissions; the guardrail dashboard; incidents.
* **Change control:** a rule change needs the service owner's sign off and its test; a model or prompt change reruns the evaluation set and every scenario in both languages before release.
* **Incident response:** one switch takes the assistant offline; the session's audit trail is reviewed; a test reproduces the cause before it returns.
* **After day 90:** if the decision is go, widen the pilot, then reuse the same pattern (rules, guard, contracts, officer) for the next transactional service, starting with its rules.

## If a constraint changes

| If | Then | Why it still works |
|---|---|---|
| The model must run on Ministry hardware | run an open model on Ministry servers; dependency 3 becomes hardware sizing | the prototype already runs an open model locally; the model is one setting |
| No generative AI in the first release | run the same journey without a model; replies come from the card and the record | the scripted planner completes all 42 scenarios; rules, payment and referrals are unchanged |
| Arabic first | pilot in Arabic once the wording is approved; English follows | every scenario has an Arabic edition that passes |
| The payment system is not ready | pilot the checking and guidance; parents pay and submit in the current channel | payment sits behind its own contract and step |
| 45 days instead of 90 | stop at shadow mode; the day 45 decision is whether to start the pilot | shadow mode needs no parent facing approval |
| A second service is added | write and test its rules from its card; reuse everything else | the agent, guard, contracts, audit and officer step are not specific to this service |

## Sources

Facts about the UAE context come from these sources. Dates, targets marked proposed, team sizes and risk scores are planning judgements, to be confirmed with the Ministry at G1.

1. UAE Cabinet meeting of 18 May 2026: agentic AI in government services, implementation teams in every ministry. https://mediaoffice.ae/en/news/2026/may/18-05/mohammed-bin-rashid-chairs-uae-cabinet-meeting
2. UAE Charter for the Development and Use of Artificial Intelligence, 10 June 2024. https://uaelegislation.gov.ae/en/policy/details/the-uae-charter-for-the-development-and-use-of-artificial-intelligence
3. National Cloud Security Policy, UAE Cyber Security Council. https://u.ae/en/about-the-uae/digital-uae/digital-transformation/strategies-policies-and-initiatives/National-Cloud-Security-Policy
4. Al Tamimi, New data sovereignty rules for cloud consumers and providers in the UAE (version 2.0 of the policy), October 2026. https://www.tamimi.com/law-update/the-technology-issue-2026/articles/new-data-sovereignty-rules-for-cloud-consumers-and-providers-in-the-uae/
5. MoHRE, first federal entity to move its data centre to TDRA's federal cloud network (FEDnet), April 2024. https://mohre.gov.ae/en/media-centre/news/24/4/2024/mohre-becomes-first-federal-entity-to-transfer-data-centre-systems-services-to-tdras-federal-cloud-network-infrastructure.aspx
6. UAE PASS developer documentation: onboarding in four phases. https://docs.uaepass.ae
7. UAE Design System, accessibility guidance: WCAG 2.1 level AA for federal entities. https://designsystem.gov.ae/guidelines/accessibility
8. Baker McKenzie, UAE key data laws: the federal personal data law excludes government entities and government data. https://resourcehub.bakermckenzie.com/en/resources/global-data-and-cyber-handbook/emea/uae/topics/key-data-and-cybersecurity-laws
9. OWASP Top 10 for LLM Applications 2025. https://genai.owasp.org/llm-top-10/
10. The National, Falcon Arabic released by the Technology Innovation Institute, 21 May 2025. https://www.thenationalnews.com/future/technology/2025/05/21/arabic-ai-language-model-uae/
11. Inception (G42), Jais, an Arabic language model released as open source, 30 August 2023. https://inceptionai.ai/2023/08/30/meet-jais-the-worlds-most-advanced-arabic-llm-open-sourced-by-g42/index.html
