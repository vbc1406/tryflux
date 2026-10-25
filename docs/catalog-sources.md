# Catalog sources

Everything in `flux_os/models.json` was checked against the provider's own pages on **2026-10-25**.
No aggregator or blog was used for prices, limits or capabilities.

## How ratings are set

Providers publish different agentic benchmarks for different models (Terminal-Bench 4.0, FrontierCode,
DeepSWE, Humanity's Last Exam, GDPval, ...), and almost none publish all of them for every model. A
0-1 rating per task therefore cannot be computed from a formula. What the benchmarks do support is
**ordering**: if one model clearly beats another on the benchmark that maps to a task, it must be
rated higher on that task. This refresh enforced that ordering where a published number exists, and
left every other rating alone. The size of each adjustment is a judgement, not a derived number.
`tests/test_catalog_sanity.py` pins the orderings below.

Benchmark-to-task mapping used: reasoning = Humanity's Last Exam (with tools) and science evals;
code_generation / code_review = Terminal-Bench 4.0, FrontierCode, DeepSWE, CursorBench;
function_calling = the same agentic evals; analysis = GDPval-AA / Vals Index. The classic
GPQA / SWE-bench Verified / BFCL / MMLU-Pro / MRCR numbers are not in the 2026 model cards for the
current models, so they were not used.

### Published numbers behind the rating changes

| Comparison | Numbers | Source |
|---|---|---|
| Haiku 5.5 vs Haiku 4.5 vs GPT-6 Luna | Terminal-Bench 4.0 39.2 / 0.0 / 16.4; FrontierCode 1.1 46.4 / - / 42.4; HLE (no tools) 45.9 / 10.2 / -; GDPval-AA 1620 / 735 / 1437 | https://www.anthropic.com/news/claude-haiku-5-5 |
| Sonnet 5.5 vs Sonnet 5 vs Opus 5.5 | Terminal-Bench 4.0 70.6 / 10.3 / 66.4; CursorBench 55.5 / 34.1 / 57.8; HLE (tools) 64.5 / 54.9 / 67.7; GDPval-AA 1844 / 1449 / 1846 | https://www.anthropic.com/news/claude-sonnet-5-5 |
| Opus 5.5 vs Fable 5.1 vs Opus 5 vs GPT-6 Astra vs GPT-5.6 Sol | Terminal-Bench 4.0 66.4 / 55.8 / 52.3 / 57.9 / 37.3; FrontierCode 54.4 / 50.3 / 48.0 / 53.3 / 47.5; HLE (tools) 67.7 / 65.6 / 63.6 / 57.2 / -; GDPval-AA 1846 / 1735 / 1708 / 1542 / 1588 | https://www.anthropic.com/news/claude-opus-5-5 |
| GPT-6 Astra HLE (tools) | 57.2 (same figure in OpenAI's own table) | https://openai.com/index/gpt-6-astra/ (search-result excerpt) |
| GPT-6 Luna vs GPT-5.6 Luna / Sol | DeepSWE v1.1 66.6 (max effort); "exceeds GPT-5.6 Sol (medium) at one tenth of its cost" | https://openai.com/index/introducing-gpt-6-sol-and-luna/ |
| Gemini 4 Argon vs Astra / Fable 5.1 / Opus 5.5 | DeepSWE v1.1 77.9 / 74.1 / 67.4 / 74.2; Terminal-Bench 4.0 57.4 / 58.2 / 57.9 / 66.4; GraphWalks 256k-1M 84.2 / 71.8 / 65.0 / 66.8 | https://deepmind.google/models/model-cards/gemini-4-argon/ |
| gpt-oss-120b / 20b | MMLU 90.0 / 85.3; SWE-bench Verified 62.4 / 60.7 | https://console.groq.com/docs/model/openai/gpt-oss-120b , .../gpt-oss-20b |

Vendors disagree on competitors' numbers (Anthropic lists Astra at 57.9 and Fable 5.1 at 55.8 on
Terminal-Bench 4.0; Google lists 58.2 and 57.9). Each model's own vendor is treated as authoritative
for that model only where possible.

### Rating changes made (all ordinal)

- `claude-haiku-4-5-20251001`: code_generation, code_review, reasoning, function_calling, analysis, general, long_document lowered. It was an exact copy of Haiku 5.5's row.
- `claude-sonnet-5`: code_generation, code_review, reasoning, function_calling, analysis, general lowered. It was an exact copy of Sonnet 5.5's row. Code is now below Haiku 5.5 because Sonnet 5 scored below it on Terminal-Bench and FrontierCode.
- `claude-opus-5`: code_generation, code_review, reasoning, function_calling, analysis, general lowered slightly (copy of Opus 5.5's row).
- reasoning re-ordered to follow HLE-with-tools: Opus 5.5 0.96 > Fable 5.1 0.95 = Astra 0.95 > Opus 5 0.94 (Astra was 0.97, the top, despite scoring lowest of these on HLE; it still leads Terminal-Bench-Science in OpenAI's and Google's tables, so it was lowered to 0.95, not further).
- `gpt-6-luna` code_generation 0.85 and `gpt-5.6-luna` 0.83: GPT-6 Luna ahead of 5.6 Luna, both behind Haiku 5.5.

## Per-model sources

Price, context window, max output and capability flags come from the vendor pages below (all fetched
2026-10-25). "Prices" = Standard, non-batch, non-cached, shortest-context tier.

### Anthropic
- Prices: https://platform.claude.com/docs/en/about-claude/pricing
- Specs: https://platform.claude.com/docs/en/models/overview and per-model pages `.../models/<slug>/overview` (fable-5-1, opus-5-5, sonnet-5-5, haiku-5-5, opus-5, sonnet-5, opus-4-7, sonnet-4-6, haiku-4-5)
- Lifecycle: https://platform.claude.com/docs/en/about-claude/model-deprecations
- Ratings: the three announcement pages above. `claude-fable-5-1`, `claude-opus-4-7`, `claude-sonnet-4-6`: no new data beyond the Opus 5.5 table; ratings unchanged.

### OpenAI
- Prices: https://developers.openai.com/api/docs/pricing (and the per-model page for models that are no longer on the pricing table)
- Specs, endpoints, function calling / structured outputs: https://developers.openai.com/api/docs/models/<id> for gpt-6-astra, gpt-6.1-sol, gpt-6-luna, gpt-5.6-sol, gpt-5.6-terra, gpt-5.6-luna, gpt-5.5, gpt-5, gpt-5-mini, o3, gpt-4o, gpt-4o-mini
- Lifecycle: https://developers.openai.com/api/docs/deprecations
- Ratings: see table above. `gpt-6.1-sol` and `gpt-6-luna` (all tasks except code_generation) are still **provisional**: OpenAI's 6.1 Sol launch page only shows charts with no extractable numbers.

### Google
- Prices: https://ai.google.dev/gemini-api/docs/pricing
- Specs: https://ai.google.dev/gemini-api/docs/models/<id>
- Lifecycle: https://ai.google.dev/gemini-api/docs/deprecations
- Ratings: no new data for the four catalog models; unchanged.

### Groq
- Specs and prices: https://console.groq.com/docs/model/openai/gpt-oss-120b and `.../gpt-oss-20b`; lifecycle https://console.groq.com/docs/deprecations (neither model is listed).

### Mistral
- Specs and prices: https://docs.mistral.ai/models/mistral-large-3-25-12, `.../mistral-medium-3-5-26-04`, `.../mistral-small-4-0-26-03`; lifecycle https://docs.mistral.ai/getting-started/models/models_overview/ (Deprecated section).
- Mistral publishes no max-output limit and no benchmark table on these pages: `max_output_tokens` and all ratings for the three Mistral models are unverified and unchanged.

## Not added (confirmed facts, ratings missing)

- `gemini-4-argon`: stable, 1,048,576 context, 65,536 default output (up to 1,048,576 with long decode), function calling, structured outputs, image input. $2 / $10 through 2026-11-30, **$4 / $20 from 2026-12-01**. The model card has no per-task data for most of the 14 tasks.
- `gemini-3.5-flash-lite`: stable, 1,048,576 / 65,536, tools, structured outputs, image input, $0.30 / $2.50. Google names it the replacement for `gemini-3.1-flash-lite` (shutdown 2027-05-07).
- `gemini-3.6-flash`: listed at $0.75 / $3.75 (rising to $1.50 / $7.50 on 2027-01-01); the model page was not read.
- `claude-opus-4-8` ($5 / $25), Fable 5, Mythos 5 / 5.1: on the pricing page; not checked for API availability.
- `mistral-large-4` (public preview since 2026-10-06, $1.36 / $4.18, 1M context): the exact API id and max output are not stated.
