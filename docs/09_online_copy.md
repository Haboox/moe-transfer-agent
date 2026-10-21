# 09 The online copy (plan B)

A second way to show the prototype if the demo computer fails: the same portal, hosted on Streamlit Community
Cloud (free), reached through a private link. The local computer with its own model stays the main version, and
the recorded walkthrough is the last fallback.

## What runs where

| Part | Local (main) | Online copy (plan B) |
|---|---|---|
| Portal, rules, guard, mocks, payment window, staff portal, audit trail | This computer | Streamlit Community Cloud (United States), from a private GitHub repository |
| Language model | `qwen3:8b` on this computer (Ollama) | A hosted model behind the OpenAI style API (`LLM_PROVIDER=hosted`): Groq by default, Google Gemini as the alternative |
| Settings | `.env` | The app's **Secrets** box on Streamlit (never in the repository) |
| Data | Synthetic only | Synthetic only |
| Who can open it | This computer only (`--server.address localhost`) | Invited viewers only (Streamlit private app, sign in by email), plus an access code |

Everything decided by code behaves the same in both: the rules, the guard, escalation, the payment window, the
staff decisions, the fixed answers (time, the phone number for a person, questions outside the service), and the
reply checks. Only the free wording of the model's replies can differ, because it is a different model.

## Decision D-05: a hosted model for the online copy

**Why:** a free host has no graphics card, so the local model cannot run there.
**Allowed because:** every name, document and number in the prototype is synthetic, so nothing real leaves the
system; the model still has no internet tools of its own (P-17), and every action still passes the guard.
**Not for production:** a live service would use a model hosted under the Ministry's own agreements (90 day plan).

## Settings (Streamlit: App settings, Secrets)

```toml
LLM_PROVIDER = "hosted"
HOSTED_API_KEY = "the key from the model service"
HOSTED_URL = "https://api.groq.com/openai/v1"
HOSTED_MODEL = "openai/gpt-oss-120b"
HOSTED_FALLBACK_MODELS = "openai/gpt-oss-20b"   # used when the main model's allowance is used up
MOE_ONLINE = "1"                 # hides the local model option (there is none online)
APP_PASSCODE = "a code you choose" # asked before the portal opens; leave out for no code
```

For Google Gemini instead of Groq: `HOSTED_URL = "https://generativelanguage.googleapis.com/v1beta/openai"` and
a Gemini model name in `HOSTED_MODEL`, with a Gemini API key.

## Deploying (once)

1. Push this folder to a **private** GitHub repository (without `.env`; `.gitignore` already leaves it out).
2. On https://share.streamlit.io, sign in with GitHub, choose **Create app**, pick the repository, branch `main`
   and main file `app.py`. Under **Advanced settings** choose Python 3.13 and paste the secrets above.
3. Once it runs, **Share** the app with the email addresses that may view it.
4. Open the link the morning of the demo: an app with no visitors for 12 hours sleeps and takes up to a minute to
   wake.

## Limits to know

Groq's free plan, per model (October 2026): 30 requests and 8,000 tokens a minute, 1,000 requests and 200,000
tokens a day. One full parent session uses about 25,000 tokens, so about eight full demonstrations a day on the main
model, then the backup model takes over with its own allowance. **Demo controls shows the live state next to the
AI model:** "Ready, about N requests left today", "Main model resting; using the backup model", or "AI paused until
HH:MM" (Groq says exactly when to retry; the allowance comes back gradually, as a rolling window). While paused, the
portal still works without AI (answers from the service card and the case record, documents checked, payment,
submission, officer referral) and says so in the reply.

* Free model tiers limit tokens per minute and per day. One full parent session (question, documents, payment) uses
  about 12 model calls and 25,000 tokens (measured on the local logs). When a limit is reached the portal waits as
  the service asks (up to 30 seconds at a time) instead of failing.
* Each browser visit has its own case list (as locally), kept until the app restarts.
* The model in **Demo controls** can be switched to "No AI (scripted planner)" at any time if the hosted model is
  unavailable: the rules, documents, payment and staff portal still work.
