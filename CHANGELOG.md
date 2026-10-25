# Changelog

## Unreleased

### Changed
- Catalog refresh, 2026-10-25. Every price in `models.json` matched the provider's official page, so no price changed. Sources and the rating method are in `docs/catalog-sources.md`.
- Quality ratings: `claude-haiku-4-5`, `claude-sonnet-5` and `claude-opus-5` were exact copies of their successors' rows. They are now rated below `claude-haiku-5-5`, `claude-sonnet-5-5` and `claude-opus-5-5` on code, reasoning and tool use, following the published Terminal-Bench 4.0 / FrontierCode / HLE numbers. Reasoning now follows HLE-with-tools (Opus 5.5 > Fable 5.1 = Astra > Opus 5; Astra was top at 0.97). `gpt-6-luna` is rated above `gpt-5.6-luna` and below `claude-haiku-5-5` on code generation. Ordering is sourced; the size of each adjustment is a judgement.
- Because of that, the README's hardest example (the Rust hash map) now routes to `gpt-oss-120b` (Groq) instead of `gpt-6-luna`; the README lines were updated, not the test.
- `gemini-3.8-flash` is listed at 36 s (was 20 s): it measured 36 to 94 s on a trivial tool call on Google's free tier. Re-measure on a paid key.
- `claude-sonnet-4-6` max output is 128,000 (was 64,000); `mistral-large-3` and `mistral-medium-3.5` accept image input (Mistral's model pages list it). README disclaimer date is 2026-10-25.
- README no longer says tool calls work "across every provider". It now states what the mocked tests cover and that no provider has been checked live.
- Added `tests/test_live_astra.py` (function call, streaming function call, tool loop against the real API). They skip without `OPENAI_API_KEY` and have not been run. OpenAI's model page lists function calling for Astra, but a live run on 2026-10-25 got a 400 from Chat Completions when tools were sent. `gpt-6-astra` stays `tools: false`; the tests document the behaviour. Its `function_calling` rating (0.93) is the model's general ability and has no effect on routing while tools are excluded.

### Fixed
- Streamed tool calls now always carry an `index`. Gemini's OpenAI-compatible stream omits it and sends each parallel call whole, so OpenAI-format clients merged two calls into one invalid JSON string, and the Anthropic Messages path kept only the first call and ended the turn with `end_turn` (an agent loop stopped). Found in a live run; the mocked Gemini stream had always included `index`, so the suite never saw it.
- Two gpt-oss-on-Groq glitches now reroute like any other model failure instead of reaching the client as a 400: "model called a tool" (a tool that was never offered; about 1 in 4 `/v1/responses` turns in a live run) and "tool call validation failed" (the model leaked `<|channel|>commentary` into a tool name).
- Removed `gemini-2.5-pro` from the catalog: Google now answers 404 "no longer available to new users", so it only wasted a reroute attempt. Pinning `gemini-2.5-pro` still passes through for keys that have access.
- `gemini-3.8-flash` is listed at 20 s instead of 0.7 s. On Google's free tier it took 27 to 85 s for a trivial request, which made `flux-fast` pick it. Re-measure on a paid key.
- `flux-fast` (and `X-Flux-Mode: fast`) no longer sends every request to `claude-fable-5-1` when an Anthropic key is set. Its `latency_ms` was listed below Haiku's, so the most expensive model won every latency ranking, even for "hi". It is now listed as Anthropic's slowest model.
- Removed `o4-mini`, which OpenAI shuts down on 2026-10-23.
- Claude 4.7 and later (every 4.7+/5.x entry in the catalog, and unlisted `claude-*` names that match) accept only default sampling values, so a client's `temperature=0.2` or `top_p` made Anthropic answer 400, which is not rerouted. `drop_params` now applies on the Anthropic path too (it only did for OpenAI-shaped providers), and those models drop `temperature` / `top_p`. Claude Sonnet 4.6 and Haiku 4.5 still receive them.
- `/openapi.json` is no longer served; it was reachable without the API key.

### Security
- `FLUX_OS_DISABLE=<model id>` (and `FLUX_OS_ONLY_MODELS`) now also cover pass-through spellings of the same model: `openai/gpt-4o`, `OPENAI/gpt-4o` and `GPT-4o` are refused when `gpt-4o` is disabled, and `openai/gpt-5-mini` is accepted when `gpt-5-mini` is allow-listed. Matching is case-insensitive. Before, a client with the API key could reach a model the operator had switched off by prefixing its provider.
- A client hanging up mid-request (aborted or half-open POSTs) no longer writes a `ClientDisconnect` stack trace to the server log per connection. It answers 499 quietly, so a flood of half-open connections can't flood the log.
- **Classifier ReDoS**: the multi-part-list regex (`^\s*...` with `re.M`) was quadratic on runs of newlines or whitespace, so one 60 KB request stalled the server for 10 to 16 seconds. It is linear now, and pattern matching reads at most 12k characters from each end of a prompt (a 1 MB prompt routed in 1.3 s before, about 35 ms now).
- **Pinned models bypassed `FLUX_OS_DISABLE` / `FLUX_OS_ONLY_MODELS`.** Sending `model: "gpt-5"` or `"claude-opus-4-7"` (or any pass-through name) reached the provider even when the operator had switched it off. Pins are now checked against the same lists.
- **Browser CSRF and DNS rebinding against a keyless loopback server.** A web page could POST `text/plain` JSON to `localhost:8000` (no CORS preflight) and spend the user's credits. Without `FLUX_OS_API_KEY`, `flux-os serve` on loopback now refuses requests whose `Host` or `Origin` is not a loopback name (extend with `FLUX_OS_ALLOWED_HOSTS`).
- A `model` containing CR/LF or other control characters is rejected with 400 (it aborted the response after the upstream call was made); `x-flux-*` header values are printable ASCII.
- `service_tier`, `store`, `plugins`, `models`, `route`, `provider`, `transforms` and `base_url` are no longer forwarded from clients, and `n` above 8 is rejected (they raise the operator's bill or change retention).
- Upstream error text in the server log is masked (key-shaped strings and the configured key values).
- `docker compose up` now fails fast with a clear message when `FLUX_OS_API_KEY` is unset, instead of restart-looping. Dependabot also watches the Docker base image; `.dockerignore` excludes `.env.*`, keys, tests and examples.
- `gpt-6-astra` is no longer marked `tools: true`. OpenAI requires the Responses API for
  GPT-6 Astra tool calling, and flux-os only speaks Chat Completions to OpenAI, so tool
  requests routed to Astra would have failed upstream. Requests that include tools now skip
  Astra; requests without tools can still use it. Pinning `model="gpt-6-astra"` with tools is
  still honoured as-is and will hit that upstream limit until a Responses adapter exists.

### Added
- Catalog refreshed against each provider's docs on 2026-10-22: `claude-haiku-5-5` ($0.10/$0.50), `claude-sonnet-5-5` ($2/$10), `claude-opus-5-5` ($4/$20), `gpt-6-luna` ($0.10/$0.50) and `gpt-6.1-sol` ($2/$10). The two GPT-6 entries are `tools: false` (Responses-only tool calling, like `gpt-6-astra`). **Their quality ratings are provisional**: each copies its predecessor's ratings (`gpt-6.1-sol` is `gpt-6-astra` minus 0.02) until there is benchmark data. `gpt-6-luna` is cheaper than `gpt-oss-120b`, so with OpenAI and Groq keys it now takes some traffic that went to Groq.
- `tests/test_catalog_sanity.py` also pins: no model is listed faster than a provider-mate that costs a tenth as much, no model stays in the catalog past an announced shutdown date, and a successor is never rated below its predecessor on code and reasoning.
- `tests/test_catalog_sanity.py`: easy prompts never land on the priciest model in any mode, and catalog entries are well formed.

### Deprecation watch (still routable, remove when they shut down)
- `gpt-5`, `gpt-5-mini`, `o3`: 2026-12-11. `gpt-4o`, `gpt-4o-mini`: 2027-01-14. `claude-haiku-4-5-20251001`: retirement "not sooner than" 2026-10-15.
- `gemini-3.8-flash` list price doubles on 2027-01-01 ($0.75/$3.75 to $1.50/$7.50).
- `gpt-5.6-sol` is on promotional pricing ($4/$20) "at least through 2026-11-21". OpenAI describes it as 20% / 33% off, which implies a regular $5/$30.
- `gemini-3.1-flash-lite`: shutdown 2027-05-07 (replacement `gemini-3.5-flash-lite`, not yet in the catalog).
- Not yet announced for shutdown, earliest possible retirement: `claude-opus-4-7` 2027-04-16, `claude-opus-5` 2027-07-24, `claude-fable-5-1` 2027-09-01, `claude-opus-5-5` 2027-09-22, `claude-sonnet-5-5` 2027-09-28, `claude-haiku-5-5` 2027-10-07. `claude-haiku-5-5` is $0.50/$2.50 for prompts over 100k tokens (catalog lists the $0.10/$0.50 base tier); `gemini-3.1-pro-preview` is $4/$18 over 200k; GPT-6/5.6 models are 2x input / 1.5x output over 272k.

## 0.2.0
Fixes from a routing evaluation (real providers, stub upstreams).

### Fixed
- Anthropic Messages path no longer breaks Gemini 3 tool loops: the `thought_signature` round-trips on `tool_use` blocks (streaming and not, parallel calls too) and is remembered server-side for clients that strip unknown fields. A "missing thought_signature" 400 is now reroutable.
- Type-invalid input (`"model": 5`, `"max_tokens": "abc"`, ...) returns 400, not 500, on every endpoint.
- Empty replies from reasoning models that spend all of `max_tokens` on hidden reasoning (`finish_reason: length`) now reroute, or return a clear error. Non-streaming only.
- Catalog: gpt-oss-120b reasoning rating 0.86, gpt-oss-20b 0.80 (the 120b leads on MMLU, GPQA, HLE and Tau-Bench in OpenAI's model card).

### Added
- Reroute observability: a stderr line per reroute, an `x-flux-attempts` header, `x-flux-*` headers on upstream errors.
- Quality-bar tolerance band, `FLUX_OS_QUALITY_TOLERANCE` (default 0.02; `0` restores the strict bar).
- Pinned catalog models whose context window the input exceeds now fail with a loud 400 (`FLUX_OS_ALLOW_OVERSIZE=1` opts out).
- Unknown tool_call_ids are logged once.

### Behaviour change to know about
- The 0.02 tolerance sends noticeably more traffic to the cheapest adequate model than 0.1.0 did.

### Docs
- README examples are now checked by tests; notes on single-instance tool loops, mid-loop reroutes, and tier-gated models.
