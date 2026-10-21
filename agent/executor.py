"""Runs tool calls safely.

run_tool():      model asks for a tool -> guard checks it -> handler runs -> result logged
call_backend():  one call to a MOCK system with the retry policy (P-03, ASSUMPTION A-07):
                 timeout / server error / malformed response -> retry once -> then ToolFailure
"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass, field
from typing import Any, Callable, Type

from pydantic import BaseModel, ValidationError

from .audit import AuditLog
from .config import Settings
from .mocks import BackendError, MockBackend, ToolTimeout
from .models import CaseState


# Backend calls run in worker threads so the executor can stop waiting after the time limit,
# exactly like an HTTP client timeout. A hung call keeps running in the background and is ignored.
_POOL = ThreadPoolExecutor(max_workers=8, thread_name_prefix="mock-call")


LANES = ("input", "interpret", "validate", "act", "approve")


class ToolFailure(Exception):
    """A backend call still failed after the retry policy."""

    def __init__(self, system: str, outcome: str, message: str):
        super().__init__(message)
        self.system, self.outcome, self.message = system, outcome, message


@dataclass
class AgentContext:
    state: CaseState
    backend: MockBackend
    audit: AuditLog
    settings: Settings
    trace: list[dict] = field(default_factory=list)   # short human-readable trace for the UI
    stats: dict = field(default_factory=lambda: {"tool_calls": 0, "tool_ok": 0, "guard_blocked": 0,
                                                  "backend_attempts": 0, "backend_failures": 0,
                                                  "recovered_by_retry": 0, "tool_failed": 0,
                                                  "override_attempts": 0, "replies_blocked": 0,
                                                  "doc_instructions": 0})

    def add_trace(self, title: str, note: str = "", kind: str = "info", lane: str = "act") -> None:
        """One line of the agent trace. `lane` is which of the case study's four responsibilities did it:
        interpret (the model), validate (fixed rules and checks, no AI), act (an authorised tool through the
        guard), approve (a person), or input (the customer)."""
        assert lane in LANES, lane
        self.trace.append({"title": title, "note": note, "kind": kind, "lane": lane})


def call_backend(ctx: AgentContext, system: str, operation: str, fn: Callable[[], Any],
                 contract: Type[BaseModel], basis: str) -> BaseModel:
    attempts = 1 + max(0, ctx.settings.tool_max_retries)
    last_outcome, last_msg = "", ""
    for attempt in range(1, attempts + 1):
        ctx.stats["backend_attempts"] += 1
        try:
            try:
                raw = _POOL.submit(fn).result(timeout=ctx.settings.tool_timeout_seconds)
            except FutureTimeout as e:
                raise ToolTimeout(f"{system} did not respond within {ctx.settings.tool_timeout_seconds:g} s") from e
            result = contract.model_validate(raw)
            ctx.audit.log("tool", "backend_call", basis, system=system, operation=operation,
                          attempt=attempt, outcome="ok")
            if attempt > 1:
                ctx.stats["recovered_by_retry"] += 1
                ctx.add_trace(f"{operation}() -> {last_outcome}, recovered", "mock tool, retried once, succeeded", "warn")
            return result
        except ToolTimeout as e:
            last_outcome, last_msg = "timeout", str(e)
        except BackendError as e:
            last_outcome, last_msg = "error", str(e)
        except ValidationError as e:
            last_outcome = "malformed"
            last_msg = f"response did not match the {contract.__name__} contract ({e.error_count()} problems)"
        ctx.stats["backend_failures"] += 1
        ctx.audit.log("tool", "backend_call", basis, system=system, operation=operation,
                      attempt=attempt, outcome=last_outcome, error=last_msg,
                      will_retry=attempt < attempts)
    ctx.add_trace(f"{operation}() -> {last_outcome}", f"mock tool, failed after {attempts} attempts; nothing guessed",
                  "error")
    raise ToolFailure(system, last_outcome, last_msg)


def run_tool(ctx: AgentContext, name: str, raw_args: Any, requested_by: str = "model") -> dict:
    """Guard -> handler -> log. Always returns a dict the model can read."""
    from .guard import check   # local import avoids a circular import
    from .tools import TOOLS

    ctx.stats["tool_calls"] += 1
    spec_basis = TOOLS[name].basis if name in TOOLS else "not an authorised tool"
    trigger = f"customer turn {ctx.state.turn}" if requested_by == "model" else f"policy {requested_by}"
    ctx.audit.log("model" if requested_by == "model" else "policy", "tool_requested",
                  basis=f"{spec_basis}; triggered by {trigger}", tool=name, arguments=raw_args)
    decision = check(ctx, name, raw_args)
    if not decision.allowed:
        ctx.stats["guard_blocked"] += 1
        ctx.audit.log("guard", "tool_blocked", basis=decision.policy, tool=name, reason=decision.reason)
        ctx.add_trace(f"BLOCKED {name}()", f"guard, {decision.policy}: {decision.reason}", "block")
        return {"status": "blocked", "reason": decision.reason, "policy": decision.policy}
    ctx.audit.log("guard", "tool_allowed", basis=decision.policy, tool=name)
    spec = TOOLS[name]
    try:
        result = spec.handler(ctx, decision.args)
        ctx.stats["tool_ok"] += 1
        status = "ok"
        if name in ctx.state.failed_systems:
            ctx.state.failed_systems.remove(name)          # the system answered again
    except ToolFailure as f:
        ctx.stats["tool_failed"] += 1
        result = {"status": "failed", "system": f.system, "error": f.outcome,
                  "advice": "The system is unavailable after a retry. Do not guess a result. "
                            "A Ministry officer checks the documents instead: the fee is paid first "
                            "(request_payment), then escalate_to_human with reason_code=system_unavailable."}
        status = "failed"
        if name not in ctx.state.failed_systems:
            ctx.state.failed_systems.append(name)          # grounds a system_unavailable escalation (P-09)
    ctx.audit.log("tool", "tool_result", basis=name, tool=name, status=status, result=_short(result))
    return result


def _short(obj: Any, limit: int = 1500) -> Any:
    text = json.dumps(obj, default=str)
    return obj if len(text) <= limit else text[:limit] + "...(truncated)"
