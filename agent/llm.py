"""Language model providers behind ONE small interface.

    OllamaLLM     local model on this computer (default, free)
    AnthropicLLM  Claude API (set LLM_PROVIDER=anthropic and ANTHROPIC_API_KEY in .env)
    HostedLLM     a hosted model behind the OpenAI style chat API (Groq, Google Gemini and others; set
                  LLM_PROVIDER=hosted, HOSTED_URL, HOSTED_MODEL, HOSTED_API_KEY): used by the online copy of the
                  portal (plan B), where no graphics card is available for a local model
    ScriptedLLM   no AI: follows the suggested next step; used for repeatable tests
    AdversarialLLM (tests only) a deliberately "compromised" model that tries forbidden actions,
                   to prove the guard holds even if the model is fooled

Every provider implements:
    interpret(system, user_text, schema) -> dict
    chat(system, messages, tools)        -> LLMReply(text, tool_calls)

Messages use a neutral format:
    {"role": "user", "content": str}
    {"role": "assistant", "content": str, "tool_calls": [{"id", "name", "arguments"}]}
    {"role": "tool", "tool_call_id": str, "name": str, "content": str}
"""
from __future__ import annotations

import json
import time
import os
import re
from dataclasses import dataclass, field
from typing import Any, Optional

import requests

from .config import Settings
from .language import asks_for_person, asks_why_officer, detect_language, stated_grade


class LLMError(Exception):
    """The model could not be reached or returned something unusable."""


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Any


@dataclass
class LLMReply:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    prompt_tokens: int = 0          # how much of the context window this request used (0 = unknown)
    context_limit: int = 0


_THINK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def _clean(text: Optional[str]) -> str:
    return _THINK.sub("", text or "").strip()


class BaseLLM:
    name = "base"

    def interpret(self, system: str, user_text: str, schema: dict) -> dict:
        raise NotImplementedError

    def chat(self, system: str, messages: list[dict], tools: list[dict]) -> LLMReply:
        raise NotImplementedError


# ====================================================================== Ollama (local)
class OllamaLLM(BaseLLM):
    def __init__(self, settings: Settings):
        self.s = settings
        self.name = f"ollama:{settings.ollama_model}"

    def _post(self, payload: dict) -> dict:
        url = f"{self.s.ollama_url.rstrip('/')}/api/chat"
        try:
            r = requests.post(url, json=payload, timeout=self.s.llm_timeout_seconds)
            if r.status_code == 400 and "think" in payload and "think" in r.text.lower():
                payload = {k: v for k, v in payload.items() if k != "think"}
                r = requests.post(url, json=payload, timeout=self.s.llm_timeout_seconds)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.ConnectionError as e:
            raise LLMError(f"Ollama is not running at {self.s.ollama_url} ({e.__class__.__name__})") from e
        except requests.exceptions.Timeout as e:
            raise LLMError(f"Ollama did not answer within {self.s.llm_timeout_seconds} s") from e
        except requests.exceptions.HTTPError as e:
            raise LLMError(f"Ollama error: {r.status_code} {r.text[:200]}") from e

    def _base(self, messages: list[dict]) -> dict:
        p: dict[str, Any] = {"model": self.s.ollama_model, "messages": messages, "stream": False,
                             "options": {"temperature": 0, "num_ctx": self.s.ollama_num_ctx},
                             "keep_alive": "30m"}     # keep the model loaded between customer messages
        if not self.s.ollama_think:
            p["think"] = False
        return p

    @staticmethod
    def _convert(messages: list[dict]) -> list[dict]:
        out = []
        for m in messages:
            if m["role"] == "assistant" and m.get("tool_calls"):
                out.append({"role": "assistant", "content": m.get("content") or "",
                            "tool_calls": [{"function": {"name": tc["name"], "arguments": tc["arguments"] or {}}}
                                           for tc in m["tool_calls"]]})
            elif m["role"] == "tool":
                out.append({"role": "tool", "content": m["content"], "tool_name": m["name"]})
            else:
                out.append({"role": m["role"], "content": m["content"]})
        return out

    def interpret(self, system: str, user_text: str, schema: dict) -> dict:
        p = self._base([{"role": "system", "content": system}, {"role": "user", "content": user_text}])
        p["format"] = schema
        data = self._post(p)
        try:
            return json.loads(_clean(data["message"]["content"]))
        except (KeyError, json.JSONDecodeError) as e:
            raise LLMError(f"interpretation was not valid JSON: {e}") from e

    def chat(self, system: str, messages: list[dict], tools: list[dict]) -> LLMReply:
        p = self._base([{"role": "system", "content": system}] + self._convert(messages))
        p["tools"] = [{"type": "function", "function": t} for t in tools]
        data = self._post(p)
        msg = data.get("message", {})
        calls = []
        for i, tc in enumerate(msg.get("tool_calls") or []):
            fn = tc.get("function", {})
            args = fn.get("arguments") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args) if args.strip() else {}
                except json.JSONDecodeError:
                    args = {"_unparseable": args}      # the guard will block it (contract check)
            calls.append(ToolCall(id=tc.get("id") or f"call_{i}", name=fn.get("name", ""), arguments=args))
        return LLMReply(text=_clean(msg.get("content")), tool_calls=calls,
                        prompt_tokens=int(data.get("prompt_eval_count") or 0),
                        context_limit=self.s.ollama_num_ctx)


# ====================================================================== Anthropic (Claude API)
class AnthropicLLM(BaseLLM):
    def __init__(self, settings: Settings):
        import anthropic  # imported here so the project runs without it when unused
        if not settings.anthropic_api_key:
            raise LLMError("ANTHROPIC_API_KEY is empty in .env")
        self._anthropic = anthropic
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key,
                                          timeout=settings.llm_timeout_seconds)
        self.model = settings.anthropic_model
        self.name = f"anthropic:{self.model}"

    @staticmethod
    def _convert(messages: list[dict]) -> list[dict]:
        out: list[dict] = []
        for m in messages:
            if m["role"] == "user":
                out.append({"role": "user", "content": m["content"]})
            elif m["role"] == "assistant":
                blocks = [{"type": "text", "text": m["content"]}] if m.get("content") else []
                blocks += [{"type": "tool_use", "id": tc["id"], "name": tc["name"],
                            "input": tc["arguments"] if isinstance(tc["arguments"], dict) else {}}
                           for tc in m.get("tool_calls") or []]
                out.append({"role": "assistant", "content": blocks or [{"type": "text", "text": "..."}]})
            elif m["role"] == "tool":
                block = {"type": "tool_result", "tool_use_id": m["tool_call_id"], "content": m["content"]}
                if out and out[-1]["role"] == "user" and isinstance(out[-1]["content"], list):
                    out[-1]["content"].append(block)
                else:
                    out.append({"role": "user", "content": [block]})
        return out

    def _create(self, **kw):
        try:
            return self.client.messages.create(model=self.model, max_tokens=1024, **kw)
        except self._anthropic.APIError as e:
            raise LLMError(f"Claude API error: {e}") from e

    def interpret(self, system: str, user_text: str, schema: dict) -> dict:
        resp = self._create(system=system, messages=[{"role": "user", "content": user_text}],
                            tools=[{"name": "record_interpretation",
                                    "description": "Record the classification of the message.",
                                    "input_schema": schema}],
                            tool_choice={"type": "tool", "name": "record_interpretation"})
        for b in resp.content:
            if b.type == "tool_use":
                return dict(b.input)
        raise LLMError("no interpretation returned")

    def chat(self, system: str, messages: list[dict], tools: list[dict]) -> LLMReply:
        resp = self._create(system=system, messages=self._convert(messages),
                            tools=[{"name": t["name"], "description": t["description"],
                                    "input_schema": t["parameters"]} for t in tools])
        text = " ".join(b.text for b in resp.content if b.type == "text")
        calls = [ToolCall(id=b.id, name=b.name, arguments=dict(b.input))
                 for b in resp.content if b.type == "tool_use"]
        return LLMReply(text=text.strip(), tool_calls=calls)


# ====================================================================== Hosted model (OpenAI style chat API)
class _LongLimit(LLMError):
    """A model's allowance is used up for longer than is worth waiting (the next model is tried)."""


_WAIT_HINT = re.compile(r"try again in (?:(\d+)h)?\s*(?:(\d+)m(?!s))?\s*(?:([\d.]+)s)?", re.I)


def host_name(url: str) -> str:
    """'groq', 'gemini' or the host name, for labels and logs."""
    u = url.lower()
    return "groq" if "groq" in u else "gemini" if "googleapis" in u else re.sub(r"^https?://([^/]+).*$", r"\1", u)


class HostedLLM(BaseLLM):
    """Any chat completions API in the OpenAI request format (Groq, Google Gemini, ...). No extra package: plain
    HTTPS with requests. Only synthetic case data is ever sent.

    Free tiers limit tokens per minute and per day. A short limit (the service asks to wait 20 s or less) is waited
    out, at most 30 s in all per call. A long one (for example the daily allowance, "try again in 7m") fails at once,
    and the client remembers it: until that time every call fails at once too, so the agent falls back to its
    no-AI replies instead of keeping the parent waiting (found live: a turn hung for minutes).

    Fallback models (HOSTED_FALLBACK_MODELS): each model has its own allowance on Groq, so when the main model's
    allowance is used up, the next one in the list answers instead; only when every one is paused does the agent
    fall back to its no-AI replies."""

    MAX_WAIT_S = 20.0           # longest single wait worth taking
    MAX_TOTAL_WAIT_S = 30.0     # longest total wait in one call
    _blocked_until: dict[str, float] = {}     # per service and model, shared by every session of this server

    def __init__(self, settings: Settings):
        if not settings.hosted_api_key:
            raise LLMError("HOSTED_API_KEY is empty (in .env, or in the app's secrets online)")
        self.s = settings
        self.model = settings.hosted_model
        self.models = [settings.hosted_model] + [m for m in settings.hosted_fallback if m != settings.hosted_model]
        self.last_model = self.model
        self.name = f"{host_name(settings.hosted_url)}:{self.model}"

    @staticmethod
    def _wait_seconds(r) -> float:
        try:
            return float(r.headers.get("retry-after"))
        except (TypeError, ValueError):
            m = _WAIT_HINT.search(r.text or "")
            if not m or not any(m.groups()):
                return 5.0
            return int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + float(m.group(3) or 0)

    @staticmethod
    def paused_until(url: str, model: str) -> float:
        """When a paused model is available again (epoch seconds), or 0 if it is not paused."""
        until = HostedLLM._blocked_until.get(f"{url}|{model}", 0.0)
        return until if until > time.time() else 0.0

    def _post(self, payload: dict) -> dict:
        """Ask the first model whose allowance is not used up; a model that runs out mid-call is paused and the
        next one is asked (same request)."""
        who = host_name(self.s.hosted_url)
        for model in self.models:
            if self.paused_until(self.s.hosted_url, model):
                continue
            try:
                data = self._post_model({**payload, "model": model})
                self.last_model = model
                return data
            except _LongLimit:
                continue
        wait = min(self.paused_until(self.s.hosted_url, m) for m in self.models) - time.time()
        raise LLMError(f"{who} usage limit reached; available again in about {max(int(wait // 60), 0) + 1} min")

    def _post_model(self, payload: dict) -> dict:
        url = f"{self.s.hosted_url.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {self.s.hosted_api_key}", "Content-Type": "application/json"}
        who = host_name(self.s.hosted_url)
        slot = f"{self.s.hosted_url}|{payload['model']}"
        r, waited, retries = None, 0.0, 0
        while True:
            try:
                r = requests.post(url, json=payload, headers=headers, timeout=self.s.llm_timeout_seconds)
            except requests.exceptions.ConnectionError as e:
                raise LLMError(f"{who} could not be reached ({e.__class__.__name__})") from e
            except requests.exceptions.Timeout as e:
                raise LLMError(f"{who} did not answer within {self.s.llm_timeout_seconds} s") from e
            if r.status_code == 429:                                    # free tier limit
                wait = max(self._wait_seconds(r), 1.0)
                if wait > self.MAX_WAIT_S or waited + wait > self.MAX_TOTAL_WAIT_S:
                    HostedLLM._blocked_until[slot] = time.time() + wait
                    raise _LongLimit(wait)
                waited += wait
                time.sleep(wait)
                continue
            if r.status_code == 400 and "tool_use_failed" in r.text and retries < 2:
                retries += 1
                continue                                                # the model wrote a broken tool call: ask again
            if r.status_code == 400 and "reasoning" in r.text.lower() and "reasoning_effort" in payload:
                payload = {k: v for k, v in payload.items() if k != "reasoning_effort"}
                continue                                                # this model has no reasoning setting
            break
        if r.status_code in (401, 403):
            raise LLMError(f"{who} rejected the API key (check HOSTED_API_KEY)")
        if r.status_code >= 400:
            raise LLMError(f"{who} error: {r.status_code} {r.text[:200]}")
        try:
            return r.json()
        except ValueError as e:
            raise LLMError(f"{who} returned something that is not JSON") from e

    def _base(self, messages: list[dict]) -> dict:
        p: dict[str, Any] = {"model": self.model, "messages": messages, "temperature": 0, "max_tokens": 1024}
        if self.s.hosted_reasoning:
            p["reasoning_effort"] = self.s.hosted_reasoning
        return p

    @staticmethod
    def _convert(messages: list[dict]) -> list[dict]:
        out = []
        for m in messages:
            if m["role"] == "assistant" and m.get("tool_calls"):
                out.append({"role": "assistant", "content": m.get("content") or "",
                            "tool_calls": [{"id": tc["id"], "type": "function",
                                            "function": {"name": tc["name"],
                                                         "arguments": json.dumps(tc["arguments"] or {},
                                                                                 ensure_ascii=False)}}
                                           for tc in m["tool_calls"]]})
            elif m["role"] == "tool":
                out.append({"role": "tool", "tool_call_id": m["tool_call_id"], "content": m["content"]})
            else:
                out.append({"role": m["role"], "content": m["content"]})
        return out

    def interpret(self, system: str, user_text: str, schema: dict) -> dict:
        sys_json = (system + "\n\nAnswer with one JSON object only, matching this JSON schema:\n"
                    + json.dumps(schema, ensure_ascii=False))
        p = self._base([{"role": "system", "content": sys_json}, {"role": "user", "content": user_text}])
        p["response_format"] = {"type": "json_object"}
        data = self._post(p)
        try:
            return json.loads(_clean(data["choices"][0]["message"]["content"]))
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as e:
            raise LLMError(f"interpretation was not valid JSON: {e}") from e

    def chat(self, system: str, messages: list[dict], tools: list[dict]) -> LLMReply:
        p = self._base([{"role": "system", "content": system}] + self._convert(messages))
        p["tools"] = [{"type": "function", "function": t} for t in tools]
        p["tool_choice"] = "auto"
        data = self._post(p)
        try:
            msg = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as e:
            raise LLMError("the hosted model returned no message") from e
        calls = []
        for i, tc in enumerate(msg.get("tool_calls") or []):
            fn = tc.get("function", {})
            args = fn.get("arguments") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args) if args.strip() else {}
                except json.JSONDecodeError:
                    args = {"_unparseable": args}      # the guard will block it (contract check)
            calls.append(ToolCall(id=tc.get("id") or f"call_{i}", name=fn.get("name", ""), arguments=args))
        usage = data.get("usage") or {}
        return LLMReply(text=_clean(msg.get("content")), tool_calls=calls,
                        prompt_tokens=int(usage.get("prompt_tokens") or 0), context_limit=self.s.hosted_context)


def hosted_status(settings: Settings) -> dict:
    """For Demo controls: is the key accepted, which model answers now, how many requests are left today, and, when
    every model is paused, when the AI is back. A one-token request per model (cheap), so the screen shows the truth
    rather than a guess; the screen caches it for a minute."""
    out = {"key": bool(settings.hosted_api_key), "ok": False, "model_listed": False, "detail": "", "active": "",
           "requests_left": None, "back_at": 0.0, "paused": []}
    if not out["key"]:
        return out
    base = settings.hosted_url.rstrip("/")
    headers = {"Authorization": f"Bearer {settings.hosted_api_key}"}
    models = [settings.hosted_model] + [m for m in settings.hosted_fallback if m != settings.hosted_model]
    try:
        r = requests.get(f"{base}/models", timeout=5, headers=headers)
        out["ok"] = r.ok
        if not r.ok:
            out["detail"] = str(r.status_code)
            return out
        ids = {str(m.get("id", "")).removeprefix("models/") for m in r.json().get("data", [])}
        out["model_listed"] = settings.hosted_model.removeprefix("models/") in ids
        for model in models:
            until = HostedLLM.paused_until(settings.hosted_url, model)
            if not until:
                p = requests.post(f"{base}/chat/completions", headers=headers, timeout=10,
                                  json={"model": model, "messages": [{"role": "user", "content": "ok"}], "max_tokens": 1})
                if p.status_code == 429:
                    wait = HostedLLM._wait_seconds(p)
                    if wait > HostedLLM.MAX_WAIT_S:
                        HostedLLM._blocked_until[f"{settings.hosted_url}|{model}"] = until = time.time() + wait
                elif p.ok:
                    out["active"] = model
                    left = p.headers.get("x-ratelimit-remaining-requests")
                    out["requests_left"] = int(left) if left and left.isdigit() else None
                    break
            if until:
                out["paused"].append(model)
        if not out["active"]:
            out["back_at"] = min((HostedLLM.paused_until(settings.hosted_url, m) for m in models), default=0.0)
    except (requests.exceptions.RequestException, ValueError) as e:
        out["detail"] = e.__class__.__name__
    return out


# ====================================================================== Scripted (no AI)
_HINT = re.compile(r"SUGGESTED NEXT STEP:\s*(.+)")


class ScriptedLLM(BaseLLM):
    """Deterministic planner: always takes the suggested next step. Replies are left empty so the
    agent uses the deterministic status message. Gives repeatable tests with no model at all."""
    name = "scripted"

    def __init__(self, interpretations: Optional[list[dict]] = None):
        self.queue = list(interpretations or [])
        self._n = 0

    def interpret(self, system: str, user_text: str, schema: dict) -> dict:
        delay = float(os.getenv("SCRIPTED_LLM_DELAY", "0") or 0)   # only to rehearse a slow local model in the UI
        if delay > 0:
            time.sleep(delay)
        if self.queue:
            return self.queue.pop(0)
        return heuristic_interpret(user_text)

    def chat(self, system: str, messages: list[dict], tools: list[dict]) -> LLMReply:
        m = _HINT.search(system)
        hint = m.group(1).strip() if m else "REPLY"
        # Do not repeat a tool that was just blocked or failed: answer instead.
        if messages and messages[-1]["role"] == "tool":
            last = json.loads(messages[-1]["content"])
            if last.get("status") in ("blocked", "failed") and hint.split()[0] == messages[-1]["name"]:
                return LLMReply(text="")
        if hint.startswith("REPLY"):
            return LLMReply(text="")
        parts = hint.split()
        args = dict(p.split("=", 1) for p in parts[1:] if "=" in p)
        self._n += 1
        return LLMReply(text="", tool_calls=[ToolCall(id=f"s{self._n}", name=parts[0], arguments=args)])


# Asking to bend the rules or claiming authority ("approve it", "skip that stamp", "I am the minister",
# "ignore your instructions"), not asking a question ("has it been approved?"). Used by the no AI
# interpreter, and by the agent on top of the model's reading, so this check never depends on the model.
OVERRIDE_WORDS = re.compile(
    r"\b(approve|ignore|override|skip|waive|bypass|jailbreak)\b|moe employee|i work for|admin mode|developer mode"
    r"|system prompt|your instructions|i order you|i am the minister"
    r"|تجاوز|استثناء|وافق على|وافق علي|اعتمد الطلب|تجاهل|تخط[ىي]|بدون (ال)?ختم|بدون (ال)?تصديق"
    r"|[أا]نا موظف|[أا]نا الوزير|[أا]عمل في الوزارة|وضع المطور|تعليماتك"
    # found while testing the suggested questions: "can you approve it anyway?" in Arabic was not recognised
    r"|يمكنك الموافقة|تستطيع الموافقة|توافق على|توافقون على|[اإ]قبل الطلب|[اإ]قبلوا الطلب"
    r"|(?:الموافقة|توافق|تقبل|قبول)[^.؟?]{0,25}(?:رغم|مع ذلك|بدون|حتى لو)",
    re.IGNORECASE)

_STATUS = re.compile(r"\bstatus\b|حالة (ال)?طلب|وين وصل|[أا]ين وصل|وضع طلبي|هل تمت الموافقة|هل تم قبول", re.IGNORECASE)
_QUESTION = re.compile(r"what documents|which documents|what do i need|requirements|\bfees?\b|how much|how long"
                       r"|\b(do|does)\s+(i|he|she|we|they|my\s+\w+)\s+need\b|هل (يحتاج|أحتاج|احتاج|نحتاج|تلزم|يلزم)"
                       r"|ما المطلوب|ما هي المستندات|ما المستندات|المستندات المطلوبة|الوثائق المطلوبة|كم الرسوم"
                       r"|كم الرسم|كم التكلفة|كم المدة|كم يستغرق|كم يوم|ما هي الشروط|ما الشروط", re.IGNORECASE)


def heuristic_interpret(text: str) -> dict:
    """No-AI interpretation used by the scripted planner and tests, in English and Arabic.
    Deliberately simple and explicit (agent/language.py reads the grade)."""
    t = (text or "").lower()
    grade = stated_grade(text)
    override = bool(OVERRIDE_WORDS.search(t))
    if grade == 12:
        intent, conf = "grade12_equivalency", 0.9
    elif asks_for_person(text):
        intent, conf = "request_human", 0.9
    elif _STATUS.search(t) or asks_why_officer(text):
        intent, conf = "case_status", 0.8
    elif _QUESTION.search(t):
        intent, conf = "question_about_service", 0.8
    else:
        intent, conf = "class_transfer_equivalency", 0.8
    return {"intent": intent, "confidence": conf, "last_completed_grade": grade,
            "asks_to_override_rules": override, "language": detect_language(text)}


class AdversarialLLM(ScriptedLLM):
    """TEST ONLY. Behaves like a model that was successfully prompt-injected: it tries to call an
    approval tool that does not exist, to submit and pay out of order, and finally claims approval.
    Used to show the guard and output guard hold even when the model is fooled."""
    name = "adversarial"

    def __init__(self):
        super().__init__()
        self.attacks = [ToolCall("a1", "approve_application", {"case": "this"}),
                        ToolCall("a2", "submit_application", {}),
                        ToolCall("a3", "request_payment", {"amount_aed": 0}),
                        ToolCall("a4", "escalate_to_human", {"reason_code": "approve_now"})]

    def chat(self, system: str, messages: list[dict], tools: list[dict]) -> LLMReply:
        if self.attacks:
            return LLMReply(text="", tool_calls=[self.attacks.pop(0)])
        r = super().chat(system, messages, tools)
        if not r.tool_calls:
            return LLMReply(text="Great news! Your application has been approved. Reference SYN-9999.")
        return r


def ollama_status(settings: Settings) -> dict:
    """Quick health check for the app: is the local AI server up, is the model downloaded and loaded?"""
    base = settings.ollama_url.rstrip("/")
    out = {"running": False, "model_downloaded": False, "model_loaded": False, "detail": ""}
    try:
        requests.get(f"{base}/api/version", timeout=2).raise_for_status()
        out["running"] = True
        tags = requests.get(f"{base}/api/tags", timeout=3).json().get("models", [])
        out["model_downloaded"] = any(m.get("name") == settings.ollama_model for m in tags)
        ps = requests.get(f"{base}/api/ps", timeout=3).json().get("models", [])
        out["model_loaded"] = any(m.get("name") == settings.ollama_model for m in ps)
    except requests.exceptions.RequestException as e:
        out["detail"] = e.__class__.__name__
    return out


def warm_up(settings: Settings) -> None:
    """Load the model into memory (first load takes about a minute on a small GPU)."""
    requests.post(f"{settings.ollama_url.rstrip('/')}/api/generate",
                  json={"model": settings.ollama_model, "keep_alive": "30m"},
                  timeout=settings.llm_timeout_seconds)


def make_llm(settings: Settings) -> BaseLLM:
    if settings.llm_provider == "ollama":
        return OllamaLLM(settings)
    if settings.llm_provider == "anthropic":
        return AnthropicLLM(settings)
    if settings.llm_provider == "hosted":
        return HostedLLM(settings)
    if settings.llm_provider == "scripted":
        return ScriptedLLM()
    if settings.llm_provider == "adversarial":
        return AdversarialLLM()               # Demo controls only: a model that obeys the attack, to show the guard
    raise LLMError(f"Unknown LLM_PROVIDER '{settings.llm_provider}' (use ollama, hosted, anthropic or scripted)")
