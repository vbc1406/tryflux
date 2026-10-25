"""Guards against catalog mistakes that silently skew routing."""

from __future__ import annotations

import pytest

from flux_os import Catalog, Router

KEYS = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "GROQ_API_KEY", "MISTRAL_API_KEY")
EASY = [{"role": "user", "content": "hi"}]


def _router(monkeypatch: pytest.MonkeyPatch, *keys: str) -> Router:
    for key in KEYS:
        monkeypatch.delenv(key, raising=False)
    for key in keys:
        monkeypatch.setenv(key, "test-key")
    return Router(Catalog.load())


@pytest.mark.parametrize("key", KEYS)
@pytest.mark.parametrize("mode", ["auto", "cheap", "fast"])
def test_easy_prompt_never_lands_on_the_priciest_model(
    monkeypatch: pytest.MonkeyPatch, key: str, mode: str
) -> None:
    # flux-fast once sent "hi" to claude-fable-5-1 ($10/$50) because its latency_ms was listed below Haiku's
    router = _router(monkeypatch, key)
    pool = router.pool()
    d = router.route(EASY, mode=mode)
    priciest = max(pool, key=lambda m: m.output_cost)
    assert d.model.output_cost < priciest.output_cost or len(pool) == 1, (key, mode, d.model.id)


def test_catalog_entries_are_well_formed() -> None:
    models = Catalog.load().models
    ids = [m.id for m in models]
    assert len(ids) == len(set(ids)), "duplicate model ids"
    for m in models:
        assert m.input_cost > 0 and m.output_cost > 0, m.id
        assert m.context_window > 0 and m.max_output_tokens > 0 and m.latency_ms > 0, m.id
        assert all(0 <= v <= 1 for v in m.quality.values()), m.id


def test_retired_models_are_not_in_the_catalog() -> None:
    # OpenAI shuts o4-mini down on 2026-10-23 (https://developers.openai.com/api/docs/deprecations)
    assert Catalog.load().get("o4-mini") is None


@pytest.mark.parametrize(
    ("model", "kept"),
    [
        ("claude-sonnet-5", False),
        ("claude-opus-4-7", False),
        ("claude-haiku-5-5", False),
        ("claude-fable-5-1", False),
        ("claude-sonnet-4-6", True),
        ("claude-haiku-4-5-20251001", True),
    ],
)
async def test_sampling_params_follow_what_each_claude_model_accepts(
    keys, fake, model: str, kept: bool
) -> None:
    # Claude 4.7+ answer 400 to a non-default temperature / top_p, which would fail a request that
    # an OpenAI-style client sent with temperature=0.2
    import httpx

    from flux_os import FluxOS

    flux = FluxOS(catalog=Catalog.load(), transport=httpx.MockTransport(fake.handler))
    body = {"model": model, "messages": EASY, "temperature": 0.2, "max_tokens": 20}
    await flux.dispatch(body)
    sent = fake.calls[-1]["body"]
    assert ("temperature" in sent) is kept, model


@pytest.mark.parametrize(
    ("name", "dropped"),
    [
        ("claude-opus-4-8", True),
        ("claude-opus-5-5", True),
        ("claude-sonnet-6-0", True),
        ("claude-sonnet-4-6", False),
        ("claude-opus-4-5-20251101", False),
        ("claude-3-7-sonnet-20250219", False),
    ],
)
def test_passthrough_claude_names_drop_sampling_only_when_required(name: str, dropped: bool) -> None:
    m = Catalog.load().resolve_passthrough(name)
    assert m is not None and bool(m.drop_params) is dropped, name


def test_pricier_models_are_not_listed_faster_than_much_cheaper_siblings() -> None:
    # the flux-fast bug in general form: a latency below a provider-mate that costs a tenth as much
    # puts the expensive model first in latency-ranked modes
    models = Catalog.load().models
    for a in models:
        for b in models:
            if a.provider == b.provider and b.output_cost >= 10 * a.output_cost:
                assert b.latency_ms >= a.latency_ms, (b.id, a.id)


def test_models_past_their_announced_shutdown_are_removed() -> None:
    # dates from each provider's deprecation page, checked 2026-10-25; the catalog's own "updated"
    # stamp decides, so the test fails when the catalog is refreshed past a date without removing the model
    import json
    from datetime import date
    from importlib import resources

    updated = date.fromisoformat(
        json.loads(resources.files("flux_os").joinpath("models.json").read_text())["updated"]
    )
    shutdown = {
        "gpt-5": date(2026, 12, 11),
        "gpt-5-mini": date(2026, 12, 11),
        "o3": date(2026, 12, 11),
        "gpt-4o": date(2027, 1, 14),
        "gpt-4o-mini": date(2027, 1, 14),
        "gemini-3.1-flash-lite": date(2027, 5, 7),
    }
    catalog = Catalog.load()
    for model_id, when in shutdown.items():
        assert catalog.get(model_id) is None or updated < when, model_id


@pytest.mark.parametrize(
    ("newer", "older"),
    [
        ("claude-haiku-5-5", "claude-haiku-4-5-20251001"),
        ("claude-sonnet-5-5", "claude-sonnet-5"),
        ("claude-opus-5-5", "claude-opus-5"),
        ("gpt-6-luna", "gpt-5.6-luna"),
    ],
)
def test_a_successor_is_not_rated_below_its_predecessor_on_code_and_reasoning(newer: str, older: str) -> None:
    # published benchmarks (see docs/catalog-sources.md) put each of these ahead on agentic coding and
    # on Humanity's Last Exam; identical or inverted copies of the predecessor's row hid that
    catalog = Catalog.load()
    n, o = catalog.get(newer), catalog.get(older)
    assert n is not None and o is not None
    for task in ("code_generation", "code_review", "reasoning", "function_calling"):
        assert n.quality[task] >= o.quality[task], (newer, older, task)
