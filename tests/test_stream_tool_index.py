"""Gemini streams parallel tool calls without an ``index``; flux-os must index them itself."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from flux_os import Catalog, FluxOS
from flux_os.providers import _ToolIndexer
from flux_os.server import create_app

GEMINI = "gemini-3.1-flash-lite"


def _chunk(delta: dict[str, Any], finish: str | None = None) -> str:
    chunk = {
        "id": "c",
        "object": "chat.completion.chunk",
        "created": 0,
        "model": GEMINI,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
    }
    return f"data: {json.dumps(chunk)}\n\n"


def _gemini_like(request: httpx.Request) -> httpx.Response:
    """What Google actually sends: one whole call per delta, no ``index`` field."""
    calls = [
        {
            "id": "call_1",
            "type": "function",
            "function": {"name": "get_weather", "arguments": '{"city":"Berlin"}'},
        },
        {
            "id": "call_2",
            "type": "function",
            "function": {"name": "get_weather", "arguments": '{"city":"Madrid"}'},
        },
    ]
    payload = (
        _chunk({"role": "assistant", "tool_calls": [calls[0]]})
        + _chunk({"tool_calls": [calls[1]]})
        + _chunk({}, "stop")  # Google says "stop" even after calling tools
        + "data: [DONE]\n\n"
    )
    return httpx.Response(200, content=payload, headers={"content-type": "text/event-stream"})


@pytest.fixture
def client(keys: None) -> httpx.AsyncClient:
    flux = FluxOS(catalog=Catalog.load(), transport=httpx.MockTransport(_gemini_like))
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(flux, api_key="")), base_url="http://flux"
    )


def _events(text: str) -> list[dict[str, Any]]:
    return [
        json.loads(line[5:])
        for line in text.splitlines()
        if line.startswith("data:") and "[DONE]" not in line
    ]


async def test_openai_stream_gets_distinct_indexes(client) -> None:
    body = {
        "model": GEMINI,
        "stream": True,
        "tools": [{"type": "function", "function": {"name": "get_weather", "parameters": {}}}],
        "messages": [{"role": "user", "content": "weather in Berlin and Madrid?"}],
    }
    r = await client.post("/v1/chat/completions", json=body)
    deltas = [
        tc for e in _events(r.text) for ch in e["choices"] for tc in ch["delta"].get("tool_calls") or []
    ]
    assert [tc["index"] for tc in deltas] == [0, 1]
    assert [tc["id"] for tc in deltas] == ["call_1", "call_2"]
    finishes = [ch["finish_reason"] for e in _events(r.text) for ch in e["choices"] if ch["finish_reason"]]
    assert finishes == ["tool_calls"]


async def test_anthropic_stream_keeps_both_calls(client) -> None:
    body = {
        "model": GEMINI,
        "max_tokens": 100,
        "stream": True,
        "tools": [{"name": "get_weather", "description": "w", "input_schema": {"type": "object"}}],
        "messages": [{"role": "user", "content": "weather in Berlin and Madrid?"}],
    }
    r = await client.post("/v1/messages", json=body)
    events = _events(r.text)
    starts = [e["content_block"] for e in events if e["type"] == "content_block_start"]
    assert [b["name"] for b in starts if b["type"] == "tool_use"] == ["get_weather", "get_weather"]
    args = "".join(e["delta"].get("partial_json", "") for e in events if e["type"] == "content_block_delta")
    assert args.count("Berlin") == 1 and args.count("Madrid") == 1
    stop = next(e for e in events if e["type"] == "message_delta")
    assert stop["delta"]["stop_reason"] == "tool_use"


def _delta(**tc: Any) -> dict[str, Any]:
    return {"choices": [{"delta": {"tool_calls": [tc]}}]}


def test_plain_stop_is_left_alone_without_tool_calls() -> None:
    ix = _ToolIndexer()
    event = {"choices": [{"delta": {"content": "hi"}, "finish_reason": "stop"}]}
    ix.fix(event)
    assert event["choices"][0]["finish_reason"] == "stop"


def test_indexer_continuations_and_explicit_indexes() -> None:
    ix = _ToolIndexer()
    events = [
        _delta(id="a", function={"name": "f", "arguments": ""}),
        _delta(function={"arguments": '{"x":'}),  # continuation of the call above
        _delta(function={"arguments": "1}"}),
        _delta(id="b", function={"name": "g", "arguments": "{}"}),
    ]
    for e in events:
        ix.fix(e)
    assert [e["choices"][0]["delta"]["tool_calls"][0]["index"] for e in events] == [0, 0, 0, 1]

    explicit = _ToolIndexer()
    seen = [_delta(index=2, id="x"), _delta(id="y")]  # providers that do send indexes are left alone
    for e in seen:
        explicit.fix(e)
    assert [e["choices"][0]["delta"]["tool_calls"][0]["index"] for e in seen] == [2, 3]
