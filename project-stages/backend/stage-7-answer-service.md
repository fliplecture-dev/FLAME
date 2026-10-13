# B7 answer service handoff (development, 2026-09-27)

Status: **PARTIAL**. B7.1–B7.6 are complete in development; B7.7 remains partial. The API loads the server-only key and `gpt-6-luna`, the only permitted project model (200,000 TPM and 500 RPM, per owner). The owner confirms a USD $5/month project hard spend limit. One direct gateway call and rollback-only Study and open Curiosity answer/replay checks succeeded. B8 answer-quality evaluation has not run; no educator acceptance is claimed.

## Implemented path

- `POST /api/v1/sessions/{id}/ask` requires a member session, `Idempotency-Key`, mode and exact Study context or null Curiosity context. Open Curiosity requires no topic check and accepts general learning questions in any subject or language. The BFF sends the request and renders a labelled generated text block.
- The service claims an answer request, enforces 100 new logical requests per member per rolling day by default, validates published curriculum for Study or builds the open under-15 Curiosity prompt, then calls OpenAI outside the database transaction. The Responses request uses `store=false`, no tools, a 1,500-token output ceiling by default, a 12-second timeout and at most one transport/rate retry. The adapter accepts completed text output, including multiple text parts after reasoning items, and rejects refusals, tool output and incomplete responses.
- Monthly project spend-limit responses stop immediately with a safe `provider_budget_exceeded` code and the member UI explains the pause. The service validates text length/control characters and obvious fabricated authority claims, assigns server-owned IDs/provenance, and commits one user/assistant turn, Study resolved IDs when applicable, prompt/profile/model version, token usage and latency. Terminal failures replay a safe code under the same key; stale claims are fenced. It does not log private prompts or the API key.
- B8 capability handling returns an explicit unsupported outcome for defined unavailable capabilities before a model call. Ordinary answer quality still needs educator review.

## Local key and model template

Copy `.env.example` to `development/apps/flame-api/.env` if the file does not exist. If it already exists, add these lines there. The local API `.env` now has these settings. Keep the key out of Git and chat:

```dotenv
FLAME_LLM_OPENAI_API_KEY=<your-OpenAI-project-API-key>
FLAME_LLM_MODEL=gpt-6-luna
FLAME_LLM_TIMEOUT_SECONDS=12
FLAME_LLM_MAX_OUTPUT_TOKENS=1500
FLAME_LLM_DAILY_REQUEST_LIMIT=100
```

Run the API from `development/apps/flame-api` so its settings load that `.env`. Configure the key only on the API server; the web BFF and browser never need it. The key and model must both be set or both absent. The existing `.env.example` keeps the key/model values commented so copying it never starts paid calls by accident. The local API `.env` stores the key/model and the 100-request and 1,500-token numeric settings; the key was not displayed during verification.

## Model and spend decision

The owner confirmed `gpt-6-luna` is the only allowed project model. Its project rate limits are 200,000 tokens per minute (TPM) and 500 requests per minute (RPM); the wildcard default does not override this model-specific setting. These are traffic ceilings, not a monthly cost cap. If educator review finds quality inadequate, a different model would require a separate owner/project access decision. At the [published model rates](https://developers.openai.com/api/docs/models) checked on 2026-09-27, Luna is $0.10 per million input tokens and $0.50 per million output tokens. For illustration, 1,000 input plus 300 output tokens costs about $0.00025, before any applicable discounts or other usage. Actual prompts, retries and model usage vary. The owner confirms a **USD $5 monthly project hard spend limit** for controlled testing. This platform setting was reported by the owner, not independently read from the OpenAI dashboard. The [OpenAI project hard spend limit](https://developers.openai.com/api/docs/guides/spend-limits) covers every API call billed to that project, including retries and other users; a spend alert only notifies. FLAME's daily per-member request limit, output-token ceiling and timeout bound individual behavior but are **not** an aggregate monetary ceiling. Current recorded input/output tokens enable cost estimates after a successful turn; failed requests may still incur provider usage that the local request row cannot measure. The owner should verify current model prices and configure a project hard spend limit in the OpenAI API platform. Enforcement may lag slightly. The chosen amount and pricing snapshot belong in the acceptance record, never the secret itself.

## Remaining B7 and B8 gates

1. Complete B7.7 live timeout/cancellation and restored-session continuation checks; the direct gateway and owned Study answer/replay already passed. A live open Curiosity answer passed; the signed-in real browser/BFF journey remains useful integration evidence.
2. Review the cases and measurable thresholds in [B8 evaluation](stage-8-evaluation.md) with an educator, then evaluate actual model outputs for accuracy, topic adherence, age suitability and policy override resistance. B8.2 and B8.6 have not started.
3. Check project usage against the owner-reported USD $5 hard limit during pilot operation. The local request record measures completed turns; provider-side usage is authoritative for billing.

Development evidence: the full DB-enabled backend suite passed 64 tests with two concurrency-only skips on 2026-09-27 after multipart-output, spend-limit handling and the 100/1,500 setting update; Alembic drift check was clean. The web unit suite passed 11 tests and the production build passed after the spend-limit UI update; earlier mock browser answer/unsupported flows passed. No live provider call had been made at that checkpoint. Migration `20260927_15` is applied in development.

Live evidence, 2026-09-27: gateway response `gpt-6-luna` used 33 input/31 output tokens. A temporary published Study path in a rollback-only database transaction produced one HTTP 200 answer with 188 input/13 output tokens and recorded latency. Two message rows were present, same-key replay returned the identical answer, and the outer transaction removed all temporary rows. The test bypassed login with a disposable member override; it verified answer orchestration and persistence, not the full signed-in browser path.

## Open Curiosity frontend test path

The former `FLAME Curiosity Test (Development Only)` catalogue (`d4ab2aff-c727-49c1-a72d-f18bf999ee7b`) has been archived. No workbook rows were permanently imported; the development catalogue currently has zero published curricula. Its earlier topic-check test is historical evidence of the superseded design.

Sign in to the local web app, choose **Curiosity**, and ask any learning question, such as “How do computers work?”, “What are fractions?” or a question in another language. The BFF creates an owned Curiosity session with null context, runs capability preflight, then sends the answer request without `topic_check_id`. Curiosity does not set a curriculum version or resolved subject/topic IDs. Study retains its published-path and revision checks.

A rollback-only live API call with `gpt-6-luna` answered “How do computers work?” with zero published curricula: HTTP 200, 164 input/119 output tokens, null curriculum version and no resolved subject/topic IDs. Same-key replay returned the identical answer; test member/session/answer were rolled back. The frontend mock browser verified the open suggestion and ask/retry path. Signed-in real-browser continuation, live timeout/cancellation and educator scoring remain pending.
