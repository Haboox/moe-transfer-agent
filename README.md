# MoE AI Service Agent: Class Transfer Equivalency (Proof of Concept)

A working AI agent that takes one real Ministry of Education e-service from first enquiry to a simulated,
rule compliant outcome: it chooses its own tools, enforces rules it cannot override, and escalates what it
should not decide. It works in **Arabic and English**.

**Service:** Request for Equivalency Certificate for a Class Transfer from Outside the UAE (Grades 2 to 11).
Service card [in English](https://moe.gov.ae/en/eservices/servicecard/Pages/CertEquivalentMove.aspx) and
[in Arabic](https://moe.gov.ae/ar/eservices/servicecard/Pages/CertEquivalentMove.aspx), copied word for word in
`docs/00_service_card.md` and `docs/00_service_card_ar.md`.

> **Prototype, synthetic data only.** Every person, document, number, payment and system the agent touches is
> invented and labelled SYNTHETIC or MOCK. Names are fictional. No real Ministry system is called.

---

## Set up and run (about 10 minutes, plus the AI model download)

### What you need

| | |
|---|---|
| Computer | macOS (Apple Silicon or Intel), Windows 10 or 11, or Linux |
| Internet | Only for the first setup (packages and the AI model). After that everything runs offline |
| Disk space | About 1 GB, plus about 5 GB for the local AI model |
| Memory | 8 GB is enough for the portal; the local AI model works best with 16 GB |
| Python | 3.12, 3.13 or 3.14. **If the computer has none, setup offers to get one** for this project only |
| Ollama | The free program that runs the AI model locally. **Optional**: setup explains how to get it, and without it the portal runs in "scripted" mode (no AI) |

### macOS or Linux

1. Unzip the folder (double-click the zip on a Mac).
2. Open **Terminal** (Mac: press Cmd+Space, type Terminal, press Enter).
3. Type `cd ` (with a space after it), drag the unzipped `moe-transfer-agent` folder into the Terminal window,
   and press Enter.
4. Run the setup once:

   ```bash
   bash setup.sh
   ```

5. Start the portal (every time you want to use it):

   ```bash
   bash run_app.sh
   ```

   The portal opens in your browser at **http://localhost:8501**. Keep Terminal open while you use it, and press
   **Ctrl+C** in Terminal to stop it.

### Windows

1. Unzip the folder (right click the zip, **Extract All**).
2. Double-click **`setup.bat`** once. If Windows shows "Windows protected your PC", click **More info**, then
   **Run anyway** (the file is a plain text script you can open in Notepad first).
3. Double-click **`run_app.bat`** every time you want to use the portal. It opens in your browser at
   **http://localhost:8501**. Keep the black window open while you use it; close it to stop the portal.

### What setup does

Running setup again is always safe: it keeps what is already done.

| Step | What happens | Questions it may ask |
|---|---|---|
| 1. Python | Finds Python 3.12 or newer and creates the project's own environment in `.venv` (nothing is installed system wide) | If no suitable Python is found: "Download uv and Python 3.13 now?" Answer **y**, and a private copy of Python is downloaded for this project only (no admin rights needed) |
| 2. Packages | Installs the exact tested versions in `requirements.txt` into `.venv` | |
| 3. Settings | Copies `.env.example` to `.env` (an existing `.env` is kept) | |
| 4. Tests | Runs the 493 automated tests (no AI needed, about 2 minutes) | |
| 5. AI model | Starts Ollama if it is installed and offers to download the model `qwen3:8b` (about 5 GB) | "Download qwen3:8b now?" If Ollama is missing it offers to open the download page, and to use the portal without AI for now |

### The AI model

The agent can run with three kinds of model, set by `LLM_PROVIDER` in `.env`, or switched on the page in
**Demo controls → AI model**:

| `LLM_PROVIDER` | What runs | Needs |
|---|---|---|
| `ollama` (default) | `qwen3:8b` on this computer; nothing leaves the machine | [Ollama](https://ollama.com/download) and the model (setup downloads it) |
| `hosted` | A hosted model behind the OpenAI style API (Groq by default, or Google Gemini); used by the online copy | `HOSTED_API_KEY` in `.env`; see `docs/09_online_copy.md` |
| `anthropic` | The Claude API | An API key in `ANTHROPIC_API_KEY` in `.env` |
| `scripted` | No AI: a fixed planner that follows the suggested next step | Nothing; used for repeatable tests |

To add the local model later: install Ollama from https://ollama.com/download (on a Mac, drag it to Applications and
open it once), set `LLM_PROVIDER=ollama` in `.env`, and run setup again. A reply takes from a few seconds to about a
minute, depending on the computer.

### If something goes wrong

| Problem | What to do |
|---|---|
| "Python 3.12 or newer was not found" and you prefer your own install | Install Python 3.13 from https://www.python.org/downloads/ and run setup again |
| "permission denied" when running a `.sh` file | Start it with `bash`, as above: `bash setup.sh`, `bash run_app.sh` |
| Package install failed | Check the internet connection (and proxy, if any) and run setup again; it continues where it stopped |
| Demo controls shows the AI as "Not running" | Open the Ollama app, then press **Check again**; or switch the AI model to `scripted` |
| "is not downloaded" | Run setup again and answer **y** to the download, or run `ollama pull qwen3:8b` |
| The portal opened at http://localhost:8502 instead of 8501 | Another copy is already running on 8501: close the other window (or press Ctrl+C there) and start again |
| The first reply is slow | The model loads into memory on first use (up to a minute or two); later replies are faster |
| Windows: the portal stops responding and the black window's title starts with "Select" | A click inside the black window pauses it. Press **Esc** in that window |
| You want an empty case list | Stop the portal and delete the files inside `runtime/` (the mock case store). `logs/` holds the audit logs |

### Manual setup (if you prefer)

```bash
python3 -m venv .venv                  # Windows: py -3.13 -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                   # Windows: copy .env.example .env
python -m pytest                       # all tests, no AI needed
python scripts/start_ai.py --setup     # optional: start Ollama and download the model
streamlit run app.py                   # http://localhost:8501
```

---

## The portal

One page, switched in one click at the top:

| Control | What it does |
|---|---|
| **Parent portal / Staff portal** | The parent's service page (assistant, documents, payment window) or the officer's screen (decisions, all cases, audit trail) |
| **عربي / English** | Page language. The documents switch to that language's edition. The assistant always replies in the language the parent writes in |
| **Light / dark** | Light follows the moe.gov.ae service page; dark for presenting |
| **Demo controls** | Not part of a real portal: which synthetic parent is signed in (an **open test** with no preset case, first and default, then 15 prepared situations), which AI model runs, which system failure to simulate, and whether to show how the agent decided (rules check, agent trace) |

A quick tour: in **Demo controls**, pick *Arin Velanthar* and press **Start new session**; tick the documents,
press **Attach selected**, pay in the payment window with the test card already filled in, and the request is
submitted (test cards that fail on purpose: 4000 0000 0000 0002 is declined, 4000 0000 0000 9995 has insufficient
funds). Then pick *Salem Al Qarwani* (a name mismatch): the case goes to an officer. Open **Staff portal** to see
both cases, the evidence behind the referral, and the audit trail, and record the officer's decision.

## The decision is explainable

```
Service Outcome = Business Rules ( Verified Inputs )
```

| Responsibility | Done by | Code | Tested by |
|---|---|---|---|
| **Interpret**: understand the request, gather inputs, explain | Language model (plus code checks for language, grades, override and person requests) | `agent/agent.py`, `agent/prompts.py`, `agent/llm.py`, `agent/language.py` | `tests/test_data_and_interpret.py`, `tests/test_bilingual_and_payments.py`, `scripts/check_llm.py` |
| **Validate**: deterministic rules, no model | Rules engine R-01 to R-15, results in English and Arabic | `agent/rules.py` | `tests/test_rules.py` |
| **Act**: only authorised tools with permitted parameters | Tools, guard, executor, mocks, payment window | `agent/tools.py`, `agent/guard.py`, `agent/executor.py`, `agent/mocks.py`, `agent/payments.py` | `tests/test_guard.py`, `tests/test_tools_and_mocks.py` |
| **Approve**: a person decides what the rules cannot, and issues every equivalency decision | Staff portal | `agent/human_review.py`, `ui/staff.py` | `tests/test_privacy_and_outputs.py`, `tests/test_app_ui.py` |

The model has no approve tool and cannot take payment. A case is submitted only when the rules return ELIGIBLE on
the latest verified documents and the parent has paid in the payment window. Submitting is the agent's last action:
an officer issues the equivalency decision on every case (exceptions and ready cases), so the agent never assumes
the authority to approve (decision D-02). The parent is told the published service time of 30 working days.
Outcomes, status and requirements shown to the parent come from the case record and the service card, never from
the model's own wording. The agent has no internet access by design, and the date and time come from the
computer's clock (policy P-17).

## Tests and checks

| Command (macOS / Linux) | Windows | What it runs | AI needed |
|---|---|---|---|
| `bash run_tests.sh` | `run_tests.bat` | All 493 automated tests, about 2 minutes | No |
| `bash run_live_checks.sh` | `run_live_checks.bat` | The 8 main scenarios (S1, S3, S4, S6 in English and Arabic) with the real model | Yes |
| `bash run_live_checks.sh all` | `run_live_checks.bat all` | All 42 scenarios, 78 chat probes and 56 stress conversations with the real model (a few hours on a small GPU) | Yes |

Single scripts, from the project folder with the environment active (`source .venv/bin/activate`, Windows
`.venv\Scripts\activate`):

```bash
python scripts/run_scenarios.py --provider scripted          # all 42 scenarios, repeatable, no AI
python scripts/run_scenarios.py --provider ollama --lang ar  # live model, Arabic edition only
python scripts/probe_chat.py --provider scripted             # 78 tricky chat messages, every reply checked
python scripts/stress_test.py                                # 56 everyday and extreme conversations
python scripts/fuzz_chat.py                                  # 120 random conversations (seeded, repeatable)
python scripts/check_llm.py                                  # how well and how fast the local model does this agent's tasks
```

Reports: `docs/05_test_results_<provider>.md` (expected, actual, pass or fail, metrics, per language), with the
audit log of every run in `logs/scenario_runs/`, `logs/probes/` and `logs/stress/`.

### The six mandatory scenarios, in English and Arabic

| ID (English / Arabic) | Case study scenario | Applicant |
|---|---|---|
| S1 / S1-AR, S12 / S12-AR | Successful request from start to submission (S12: GCC national, no visa needed) | SYN-P01, SYN-P11 |
| S2, S11, S13, S14, S16, S17 / -AR | Incomplete request, missing information (missing visa; term statement; expired passport and JPG; translation sent later; a missing year; S17: the parent removes the wrong files and attaches the right ones) | SYN-P02, P10, P12, P13, P15 |
| S3, S15 / -AR | Exceptional case needing escalation (lineage name on a certificate; authenticity cannot be confirmed) | SYN-P03, SYN-P14 |
| S4, S4-ADV / -AR | Misleading input or prompt injection (chat and hidden in a document) | SYN-P04 |
| S5a, S5b / -AR | Backend failure: timeout then recovery; malformed responses | SYN-P05 |
| S6, S6-ADV / -AR | Rule bypass or unauthorised approval | SYN-P06 |
| S7, S8, S9, S10, S18 / -AR | Extras: Grade 12 belongs to another service; translations; Grade 1 stated; Grade 1 on the certificates; Grade 1 finished and joining Grade 2, with the parent's follow-up | SYN-P07, SYN-P08, SYN-P09 |

ADV variants replace the model with a simulated compromised model that obeys the injection: the guard,
rules and reply checks must hold anyway. Every scenario also checks that no sensitive data reaches replies or logs,
and that every reply is in the parent's language.

### What the 493 tests prove

| File | What it proves |
|---|---|
| `test_case_study_checklist.py` | The case study line by line: real service, traceable rules, labelled synthetic data, mocks with contracts and failures, no approval tool, separate responsibilities, every tool call logged with its basis, repeatability, deliverables present |
| `test_rules.py` | Every rule, pass and fail paths, outcome order |
| `test_guard.py` | Unknown tools, bad parameters, wrong order, grounded escalation |
| `test_tools_and_mocks.py`, `test_data_and_interpret.py` | Contracts, real timeouts, retries, synthetic files, interpretation limits |
| `test_privacy_and_outputs.py` | Masking, reply checks, staff only decisions |
| `test_scenarios.py` | All 42 scenarios from start to finish in both languages, plus model outage and loops |
| `test_bilingual_and_payments.py` | Arabic and English parity: reply language by code, Arabic grades and names, Arabic card word for word, Arabic reply checks, translations into Arabic, extreme grades, both document editions describe the same facts; no demo wording, rule IDs or child's name in what the parent sees; GCC nationals need no visa; the payment window (test cards only, card details never logged) |
| `test_stress.py`, `test_fuzz.py` | The 56 stress conversations and 120 random conversations: greetings, thanks, emoji, typed ID numbers, dialects, mixed languages, injections, authority claims, wrong grades, every new case; each reply checked for language, internal codes, demo wording, promises and leaks |
| `test_app_ui.py` | The portal runs in both languages and both views; the parent journey reaches payment and submission |
| `test_hosted_model.py` | The hosted model client without internet: request format, tool calls, JSON, rate limit waits, wrong key, the key never in an error |
| `test_unseen_inputs.py` | Inputs a panel may try: empty or huge messages, scripts, other applicants' files, fake references, invented tool arguments, expired documents |

## Documentation

| Case study section | Document |
|---|---|
| 01 Service selection and current state | `docs/01_current_state_map.md`, the cards `docs/00_service_card.md` and `docs/00_service_card_ar.md` |
| 02 Requirements, policies and rules | `docs/02_rules_and_assumptions.md` |
| 03 Synthetic data and mock integrations | `docs/03_synthetic_data_and_mocks.md` |
| 04 Agent design and build | `docs/04_agent_design.md` |
| 05 Scenario testing and results | `docs/05_test_results_ollama.md` (live model), `docs/05_test_results_scripted.md`, live chat probes and stress conversations in `docs/live_results/` |
| 06 Architecture and delivery plan | `docs/06_architecture.md`, `docs/07_90_day_plan.md` |
| Online copy (plan B): hosting, settings, decision D-05 | `docs/09_online_copy.md` |
| Build history and decisions | `docs/08_build_notes.md` |

## Project structure

```
setup.sh, setup.bat            one-time setup (macOS/Linux, Windows)
run_app.sh, run_app.bat        start the portal
run_tests.sh, run_tests.bat    automated tests (no AI)
run_live_checks.sh, .bat       checks with the real AI model
app.py            entry point: header, language and theme switches, demo controls, the two views
ui/               the screens: parent.py (assistant, documents, payment window), staff.py, audit_view.py,
                  i18n.py (every word in English and Arabic), theme.py (light and dark), session.py
agent/            the agent: agent.py (one turn), rules.py, tools.py, guard.py, executor.py, llm.py, prompts.py,
                  language.py, messages.py, guide.py, facts.py, service_card.py, output_guard.py, payments.py,
                  mocks.py, models.py, redact.py, audit.py, human_review.py, receipt.py, countries.py,
                  scenarios.py, config.py
assets/           Ministry logos (English and Arabic), favicon, PDF fonts
static/fonts/     web fonts (Inter, Noto Kufi Arabic; SIL Open Font License) so the page works offline
data/synthetic/   personas.json, documents.json and the synthetic PDFs, English and Arabic editions
docs/             the documents listed above
scripts/          start_ai.py, run_scenarios.py, probe_chat.py, stress_test.py, fuzz_chat.py, check_llm.py,
                  generate_synthetic_data.py
tests/            493 tests
logs/, runtime/   audit logs and the mock case store, created at runtime
.env.example      settings (copied to .env by setup); .env is never shared because it can hold an API key
```
