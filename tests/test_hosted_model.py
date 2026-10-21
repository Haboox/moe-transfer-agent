"""The hosted model client (Groq, Gemini..., used by the online copy) without the internet: requests is faked.

Proves the request format (OpenAI style tools and tool results), the reading of tool calls and JSON, and what
happens on a rate limit, a broken tool call, a wrong key and an unreachable service.
"""
from dataclasses import replace

import pytest
import requests

from agent import llm as llm_mod
from agent.config import get_settings
from agent.llm import HostedLLM, LLMError, host_name, make_llm

S = replace(get_settings(), llm_provider="hosted", hosted_api_key="test-key", hosted_model="test/model",
            hosted_url="https://api.groq.com/openai/v1", hosted_reasoning="", llm_timeout_seconds=5)


class FakeResponse:
    def __init__(self, status=200, body=None, text="", headers=None):
        self.status_code, self._body, self.headers = status, body, headers or {}
        self.text = text or (str(body) if body is not None else "")
        self.ok = status < 400

    def json(self):
        if self._body is None:
            raise ValueError("no json")
        return self._body


def ok_message(content="", tool_calls=None, prompt_tokens=120):
    return FakeResponse(200, {"choices": [{"message": {"content": content, "tool_calls": tool_calls}}],
                              "usage": {"prompt_tokens": prompt_tokens}})


@pytest.fixture
def calls(monkeypatch):
    """Queue of fake responses; records every request sent."""
    sent, queue = [], []

    def fake_post(url, json=None, headers=None, timeout=None):
        sent.append({"url": url, "json": json, "headers": headers})
        r = queue.pop(0)
        if isinstance(r, Exception):
            raise r
        return r
    monkeypatch.setattr(llm_mod.requests, "post", fake_post)
    monkeypatch.setattr(llm_mod.time, "sleep", lambda s: None)
    return sent, queue


def test_make_llm_picks_the_hosted_model_and_needs_a_key():
    assert isinstance(make_llm(S), HostedLLM)
    with pytest.raises(LLMError, match="HOSTED_API_KEY"):
        make_llm(replace(S, hosted_api_key=""))


def test_chat_sends_openai_style_tools_and_tool_results(calls):
    sent, queue = calls
    queue.append(ok_message(tool_calls=[{"id": "c9", "type": "function",
                                         "function": {"name": "evaluate_rules", "arguments": '{"case": "x"}'}}]))
    history = [{"role": "user", "content": "hello"},
               {"role": "assistant", "content": "", "tool_calls": [{"id": "c1", "name": "get_applicant_profile",
                                                                    "arguments": {}}]},
               {"role": "tool", "tool_call_id": "c1", "name": "get_applicant_profile", "content": "{\"ok\": true}"}]
    tools = [{"name": "evaluate_rules", "description": "d", "parameters": {"type": "object", "properties": {}}}]
    reply = HostedLLM(S).chat("SYSTEM", history, tools)
    body = sent[0]["json"]
    assert sent[0]["url"].endswith("/chat/completions")
    assert sent[0]["headers"]["Authorization"] == "Bearer test-key"
    assert body["model"] == "test/model" and body["temperature"] == 0
    assert body["messages"][0] == {"role": "system", "content": "SYSTEM"}
    assert body["messages"][2]["tool_calls"][0]["function"] == {"name": "get_applicant_profile", "arguments": "{}"}
    assert body["messages"][3] == {"role": "tool", "tool_call_id": "c1", "content": "{\"ok\": true}"}
    assert body["tools"][0] == {"type": "function", "function": tools[0]}
    assert "reasoning_effort" not in body
    assert reply.tool_calls[0].name == "evaluate_rules" and reply.tool_calls[0].arguments == {"case": "x"}
    assert reply.prompt_tokens == 120 and reply.context_limit == S.hosted_context


def test_unparseable_arguments_are_left_for_the_guard_to_block(calls):
    _, queue = calls
    queue.append(ok_message(tool_calls=[{"id": "c1", "function": {"name": "submit_application",
                                                                  "arguments": "{not json"}}]))
    reply = HostedLLM(S).chat("s", [{"role": "user", "content": "x"}], [])
    assert reply.tool_calls[0].arguments == {"_unparseable": "{not json"}


def test_interpret_asks_for_json_and_reads_it(calls):
    sent, queue = calls
    queue.append(ok_message(content='<think>hm</think>{"intent": "ask_question", "language": "en"}'))
    out = HostedLLM(S).interpret("SYS", "how much is the fee?", {"type": "object"})
    assert out == {"intent": "ask_question", "language": "en"}
    assert sent[0]["json"]["response_format"] == {"type": "json_object"}
    assert "JSON schema" in sent[0]["json"]["messages"][0]["content"]


def test_interpret_rejects_text_that_is_not_json(calls):
    _, queue = calls
    queue.append(ok_message(content="sure, the fee is 50"))
    with pytest.raises(LLMError, match="not valid JSON"):
        HostedLLM(S).interpret("SYS", "x", {"type": "object"})


def test_rate_limit_is_waited_out_once_then_answers(calls):
    sent, queue = calls
    queue += [FakeResponse(429, text="rate limit", headers={"retry-after": "3"}), ok_message(content="hi")]
    assert HostedLLM(S).chat("s", [{"role": "user", "content": "x"}], []).text == "hi"
    assert len(sent) == 2


def test_rate_limit_that_lasts_becomes_an_llm_error(calls):
    _, queue = calls
    queue += [FakeResponse(429, text="rate limit")] * 4
    with pytest.raises(LLMError, match="429"):
        HostedLLM(S).chat("s", [{"role": "user", "content": "x"}], [])


def test_a_broken_tool_call_is_asked_again(calls):
    sent, queue = calls
    queue += [FakeResponse(400, text='{"error": {"code": "tool_use_failed"}}'), ok_message(content="ok")]
    assert HostedLLM(S).chat("s", [{"role": "user", "content": "x"}], []).text == "ok"
    assert len(sent) == 2


def test_reasoning_setting_is_sent_and_dropped_if_the_model_has_none(calls):
    sent, queue = calls
    queue += [FakeResponse(400, text="reasoning_effort is not supported with this model"), ok_message(content="ok")]
    HostedLLM(replace(S, hosted_reasoning="none")).chat("s", [{"role": "user", "content": "x"}], [])
    assert sent[0]["json"]["reasoning_effort"] == "none" and "reasoning_effort" not in sent[1]["json"]


def test_wrong_key_and_no_connection_are_clear_errors(calls):
    _, queue = calls
    queue.append(FakeResponse(401, text="invalid api key"))
    with pytest.raises(LLMError, match="rejected the API key"):
        HostedLLM(S).chat("s", [{"role": "user", "content": "x"}], [])
    queue.append(requests.exceptions.ConnectionError("down"))
    with pytest.raises(LLMError, match="could not be reached"):
        HostedLLM(S).chat("s", [{"role": "user", "content": "x"}], [])


def test_the_key_never_appears_in_an_error_message(calls):
    _, queue = calls
    queue.append(FakeResponse(500, text="server error"))
    with pytest.raises(LLMError) as e:
        HostedLLM(S).chat("s", [{"role": "user", "content": "x"}], [])
    assert "test-key" not in str(e.value)


def test_the_wait_comes_from_the_header_or_the_message(monkeypatch):
    assert HostedLLM._wait_seconds(FakeResponse(429, text="x", headers={"retry-after": "12"})) == 12
    assert HostedLLM._wait_seconds(FakeResponse(429, text="Please try again in 7.5s.")) == 7.5
    assert HostedLLM._wait_seconds(FakeResponse(429, text="Please try again in 1m2.5s.")) == 62.5
    assert HostedLLM._wait_seconds(FakeResponse(429, text="slow down")) == 5.0


def test_waits_are_capped_at_30_seconds(calls, monkeypatch):
    _, queue = calls
    slept = []
    monkeypatch.setattr(llm_mod.time, "sleep", slept.append)
    queue += [FakeResponse(429, text="x", headers={"retry-after": "300"}), ok_message(content="ok")]
    HostedLLM(S).chat("s", [{"role": "user", "content": "x"}], [])
    assert slept == [30.0]


def test_host_names_for_labels():
    assert host_name("https://api.groq.com/openai/v1") == "groq"
    assert host_name("https://generativelanguage.googleapis.com/v1beta/openai/") == "gemini"
    assert host_name("https://example.org/v1") == "example.org"
    assert HostedLLM(S).name == "groq:test/model"
