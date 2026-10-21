# 06 Architecture

Case study asks for: *components, tools, data flows, decision controls, integrations and logging.*

## 1. Principle

```
Service Outcome = Business Rules ( Verified Inputs )
```

The language model never decides. It interprets the customer and chooses the next tool; every tool call
passes a guard; eligibility comes only from deterministic rules; anything the rules cannot decide goes to a person.

## 2. Components

| Layer | Component | File | Uses the model? |
|---|---|---|---|
| Channel | Portal with two views switched in one click: **Parent portal** (service page, assistant, documents, payment window) and **Staff portal** (review queue, all cases, audit trail); Arabic or English page, light (moe.gov.ae look) or dark | `app.py`, `ui/` | No |
| Language | Reply language decided by code from the parent's words; Arabic text helpers (digits, names, grades) | `agent/language.py` | No |
| **Interpret** | Intent classification (intent, confidence, grade, override attempt, language) | `agent/agent.py::_interpret`, `agent/prompts.py` | Yes |
| **Interpret** | Agent loop: chooses the next tool, writes conversational replies | `agent/agent.py::_act_loop` | Yes |
| Model access | One interface, four providers: local Ollama (default), a hosted model behind the OpenAI style API (the online copy), Claude API, scripted (no AI); plus a simulated compromised model for attack tests | `agent/llm.py` | Provider |
| **Act** | Tool registry: the only actions, each with a parameter contract and a documented basis | `agent/tools.py` | No |
| **Act** | Guard: allow list, contract check, prerequisites, grounded escalation | `agent/guard.py` | No |
| **Act** | Executor: time limit, one retry, contract validation of responses | `agent/executor.py` | No |
| **Validate** | Rules engine R-01 to R-15 with combine order | `agent/rules.py` | No |
| **Approve** | Officer decision on escalated cases and the equivalency decision on submitted cases (staff only, not a tool; D-02) | `agent/human_review.py`, `ui/staff.py` | No |
| Output control | Reply checker in English and Arabic; outcomes and status stated from records; requirements quoted from the card in the parent's language | `agent/output_guard.py`, `agent/messages.py`, `agent/service_card.py` | No |
| Payment | Mock payment window: test cards only, card details dropped at the gateway | `agent/payments.py`, `agent/mocks.py`, `ui/parent.py` | No |
| Privacy | Masking of document numbers, names, emails, phones | `agent/redact.py` | No |
| Audit | Append only JSONL trail, one file per session | `agent/audit.py` | No |
| Integrations | MOCK identity, document verification, payment, case management | `agent/mocks.py` | No |

## 3. Tools (what the agent can do)

| Tool | Mock system | Basis (logged with every call) | Allowed only when |
|---|---|---|---|
| `get_service_requirements` | Service card | Card: Required documents, Fees, Conditions | always |
| `get_applicant_profile` | MOCK Identity (UAE Pass) | Card: Service Process step 1 | case open |
| `list_uploaded_documents` | Session | Card: Service Process step 2 | always |
| `verify_documents` | MOCK Document Verification | Card: Service Conditions; R-02 to R-09, R-15 | own uploads only |
| `evaluate_rules` | Rules engine | R-01 to R-15 | profile loaded, all uploads verified |
| `request_payment` | MOCK Payment Gateway | Card: Fees; R-12; D-06 | rules ELIGIBLE or HUMAN_REVIEW on the latest documents, or a system that checks the documents is down (an officer will check them); not yet paid, no payment window already open; opens the window, the parent pays |
| `submit_application` | MOCK Case Management | Card: Service Process steps 2 to 4 | ELIGIBLE and paid (R-12) |
| `escalate_to_human` | MOCK Case Management | Approve | the stated reason is true in the record (P-09) and the fee is paid (D-06, every reason) |
| `get_case_status` | MOCK Case Management | Card: Service Process step 4 | always |

There is no tool that approves, rejects, overrides or edits a rule.

## 4. Data flow of one customer turn

```
Customer message, typed (+ attached synthetic PDFs or uploaded files)
  |
  |-- 1. uploads recorded (file type and size measured from the file) -> rules marked stale
  |-- 1b. LANGUAGE   code decides the reply language from the parent's words (P-11)
  |-- 2. INTERPRET   model -> {intent, confidence, grade, override?, language}   [logged]
  |                  code checks: override words (P-05), "asks for a person" needs asking words (P-09)
  |-- 3. ROUTE       P-06 confident Grade 12 -> Grade 12 service; Grade 1 or above 12 -> not covered (no tools)
  |-- 4. ACT LOOP    system prompt rebuilt from the case record + suggested next step
  |                  model picks a tool -> GUARD -> EXECUTOR -> MOCK system -> contract check
  |                  result (masked, document text labelled untrusted) -> model ... until it replies
  |-- 5. VALIDATE    evaluate_rules -> RuleReport (PASS / FAIL / MISSING / REVIEW per rule)
  |-- 5b. P-13      the model stopped with documents unchecked -> reminded once -> policy runs the standard steps
  |-- 6. SAFETY NET  P-03 / P-07: a case that needs a person reaches one
  |-- 7. OUTPUT      P-04 outcome and status stated from the record; P-10 service questions answered
  |                  from the card; any other reply checked (English and Arabic) for invented approvals,
  |                  outcomes, other case references and leaked instructions
  |-- 8. AUDIT       every step above, masked, with its basis
  v
Reply to customer  +  case summary (status, reference, fee, rules) in the console
```

Payment path: rules ELIGIBLE -> `request_payment` opens the payment window (status AWAITING_PAYMENT) ->
the parent pays with a test card or a wallet -> `ServiceAgent.complete_payment()` checks the rules are still
current, the mock gateway checks the card and returns a receipt with only the last 4 digits -> the next turn
submits (R-12). New files while the window is open close it: the rules must run again first.

Staff path: Staff portal -> `human_review.decide()` (officer ID, note required) -> case record
updated -> audit -> the parent sees the decision on their next turn (status refreshed from the case system),
in the language they write in.

## 5. Decision controls

| Control | What it stops | Where | Test |
|---|---|---|---|
| No approval tool (P-01) | The model approving anything | `tools.py` | `test_there_is_no_approval_tool` |
| Contract check (P-02) | Invented parameters (e.g. fee of AED 0) | `guard.py` | `test_extra_parameters_blocked` |
| Prerequisites (R-12, P-02) | Paying or submitting out of order | `guard.py` | `test_submit_before_payment_blocked` |
| Grounded escalation (P-09) | Escalating with a false reason | `guard.py` | `test_escalation_without_grounds_is_blocked` |
| Retry once, then a person (P-03), paid for first (D-06) | Guessing when a system fails; a request reaching an officer unpaid. If the payment gateway is down too, nothing is submitted and the parent is given the toll-free number | `executor.py`, `agent.py`, `guard.py` | `test_s03_each_mock_has_a_contract_and_realistic_failures`, `test_an_outage_opens_the_payment_window_then_reaches_an_officer`, `test_an_outage_with_the_payment_gateway_down_submits_nothing_and_gives_the_number` |
| Outcome from record (P-04) | "Your certificate is ready" | `agent.py`, `output_guard.py` | `test_outcome_promises_are_blocked` |
| Requirements from the card (P-10) | Paraphrased policy ("MoFA or Embassy") | `agent.py` | `test_requirements_answer_is_the_card_word_for_word` |
| Untrusted content (P-05) | Instructions hidden in documents or messages | `prompts.py`, guard | S4, S4-ADV |
| Fixed word list for override attempts (P-05) | Missing an attack because the model missed it | `llm.py`, `agent.py` | `test_override_attempt_is_flagged_even_if_the_model_misses_it` |
| Person request in the customer's words (P-09) | An authority claim sent to staff as "asked for a person" | `agent.py` | `test_authority_claim_read_as_request_for_a_person_is_not_escalated` |
| No leaked instructions (P-04) | The model printing its rules or tool names | `output_guard.py` | `test_prompt_leak_is_replaced_and_every_tool_name_is_covered` |
| Card silent means "not covered" (P-10) | Invented policy such as "cash is not accepted" | `agent.py`, `messages.py` | `test_question_the_card_does_not_answer_gets_the_card_not_an_invented_policy` |
| Topics the card does not cover (P-10) | Invented answers about cancelling, refunds, appeals | `agent.py`, `messages.py` | `test_topics_the_card_does_not_cover_are_never_answered_by_the_model` |
| Only the card's phone number (P-04) | Invented contact numbers, repeated ID numbers | `output_guard.py` | `test_invented_numbers_and_completion_claims_are_blocked` |
| Step limit | A looping model | `agent.py` | `test_model_that_loops_is_stopped` |
| Model outage fallback | Silence or a guessed answer | `agent.py` | `test_llm_outage_falls_back_safely` |
| Reply language by code (P-11) | The model answering an Arabic parent in English, or the reverse | `language.py`, `agent.py` | `test_reply_language_is_decided_by_code`; every scenario checks every reply's language |
| Same rules, both languages | Arabic parents getting a different or translated decision | `rules.py` (`detail_ar`) | `test_every_rule_result_has_an_arabic_title_and_detail`, S1-AR to S11-AR |
| Arabic card word for word (P-10) | Paraphrased Arabic policy | `service_card.py` | `test_arabic_requirements_quote_the_arabic_card_word_for_word` |
| Asking words for a person (P-09) | "أنا موظف" (I am an employee) read as "I want an employee" | `language.py` | `test_asking_for_a_person_needs_asking_words` |
| Wrong grade before any tool (P-06) | Grade 1 or Grade 12 cases entering the wrong service | `agent.py` | `test_out_of_range_grades_are_answered_before_any_tool`, S9, S10 |
| Test cards only, details dropped (P-12) | Real card charged, card number in logs | `payments.py`, `mocks.py` | `test_card_checks`, `test_card_details_never_reach_the_log_or_the_model` |
| Documents always checked (P-13) | An injection in the message making the model stop before checking a genuine parent's documents | `agent.py` | `test_injection_cannot_stop_the_documents_being_checked`, live S4 |
| Instructions inside documents shown (P-05) | An injection hidden in a certificate going unnoticed (it is passed to the model only as labelled data; this check makes it visible in the trace and the audit log, and changes no rule) | `facts.py`, `tools.py` | `test_instructions_hidden_in_a_document_are_shown_and_logged_but_change_nothing` |
| Compromised model refused | A model that obeys the injection (approve, pay nothing, submit, false escalation, "approved" reply) | `guard.py`, `output_guard.py`; selectable as "Compromised AI" in Demo controls | S4-ADV, S6-ADV, `test_the_compromised_ai_option_shows_the_guard_refusing_every_attack` |

## 6. Integrations (mocked here, real in production)

| Mock in prototype | Real system it stands for | Contract | Failure behaviour simulated |
|---|---|---|---|
| MOCK Identity | UAE Pass | `ApplicantProfile` | timeout, 503, malformed |
| MOCK Document Verification | Attestation and authenticity checks | `VerificationResult` | timeout, 503, malformed |
| MOCK Payment Gateway | MoE e-payment (card, Apple Pay, Google Pay, Samsung Pay) | `PaymentRequest`, `PaymentReceipt` | timeout, 503, malformed; declined and insufficient-funds test cards |
| MOCK Case Management | MoE case system | `CaseRecord` | timeout, 503, malformed |

Timeouts are real waits: the mock hangs (`MOCK_HANG_SECONDS`) and the executor stops waiting after
`TOOL_TIMEOUT_SECONDS`. No real Ministry system is called anywhere.

## 7. Logging

* One JSONL file per session in `logs/`, append only, numbered events.
* Each event: time, actor (customer, model, guard, tool, rules, policy, human, system), event, **basis**
  (customer turn, card section, rule ID or policy ID) and masked detail.
* What is logged: messages, intent and confidence, every tool request with its basis, every guard
  decision, every backend attempt and its outcome, every rules evaluation, replaced replies with the reason,
  security events (override attempts), human decisions, model context usage.
* Masking happens before writing: document numbers keep only their last two characters, names, emails
  and phone numbers are replaced. Tests check every scenario's log and replies for leaks.
* On screen, the **agent trace** (Demo controls, "Show how the agent decides") marks every step with the case study's
  four responsibilities: Interpret (the model, with its confidence), Validate (rules engine and deterministic checks,
  no AI), Act (a mock tool through the guard, with retries shown) and Approve (a person). Next to it a **security
  panel** counts, for the session, the tool calls the guard refused, override attempts, instructions found inside
  documents, model replies blocked, system failures and recoveries, and checks the replies and the log for every
  document number and name of the applicants involved (it shows "none" with the number of values checked).

## 8. Deployment of the prototype

| Item | Choice | Why |
|---|---|---|
| Model | `qwen3:8b` on Ollama, local, thinking off, 8,192 token context | Free, nothing leaves the machine, measured best of two local models on this agent's tasks |
| Switch model | `LLM_PROVIDER` in `.env` (ollama, hosted, anthropic, scripted), or Demo controls on the page | One setting, no code change |
| App | Streamlit, bound to localhost, usage statistics off | Simple, Python only |
| Look | Light theme follows the moe.gov.ae service page (logo, gold bar, gold buttons); dark theme for presenting; Arabic page right to left in Noto Kufi Arabic | Familiar to Ministry users; Arabic first-class |
| Fonts | Bundled in `static/fonts` (SIL Open Font License) | Works with no internet at the venue |
| Data | JSON and PDF files in `data/synthetic/`, case store in `runtime/` | No database to explain |
