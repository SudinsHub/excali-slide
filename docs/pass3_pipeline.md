# PASS 3 of 4: Generation pipeline (ingestion → plan → slides)

You are a senior engineer continuing an existing repo. Passes 1 and 2 are done. Read, in order: `docs/SPEC.md`, `docs/PROGRESS.md`, `docs/DECISIONS.md`. The compiler's public interface and issue codes are documented there.

## Goal

The end-to-end AI path: the user writes a brief and uploads notes, the system builds a plan, the user reviews and edits it, then slides are generated in parallel as editable Excalidraw scenes, with live progress. Everything runs through a Postgres-backed job queue and SSE.

## Out of scope

Editing existing slides with AI, deck revisions, insert-slide (pass 4). Do not implement those endpoints (the placeholders from SPEC may return 501).

## Tasks

### 1. Dependencies and config
Add: `litellm`, `pypdf`, `python-docx`, `python-pptx`, `jinja2`; dev: none new. Env vars (add to `.env.example` and `config.py`): `LLM_MODEL_PLANNER`, `LLM_MODEL_SLIDE`, `LLM_MODEL_EDIT`, `LLM_MODEL_VISION` (placeholders such as `anthropic/<model-name>`, documented as "any LiteLLM model string"), provider API keys as LiteLLM expects, `JOB_CONCURRENCY=4`, `MAX_RESOURCE_CHARS=60000`, `LLM_TIMEOUT_S=120`, `FAKE_LLM=0`. Add the `job` table via a new Alembic migration if pass 1 skipped it (SPEC §5).

### 2. Job queue: `app/jobs/`
- `queue.py`: `enqueue(kind, deck_id, slide_id=None, payload=None, priority=0, run_after=None) -> Job`; `claim(worker_id, n)` using one atomic statement with `FOR UPDATE SKIP LOCKED` ordered by `priority DESC, created_at`; `complete`, `fail(error, retryable)`, `heartbeat`, `cancel`, `reap_stale(stale_after_s=90)`.
- Retry policy: retryable errors (LiteLLM rate limit, timeout, connection, 5xx) requeue with `run_after = now + 3s * 2^attempts` until `max_attempts`; non-retryable fail immediately; validation exhaustion is non-retryable.
- `worker.py` (`python -m app.worker`): async loop, polls every 1 s (shorter while busy), runs up to `JOB_CONCURRENCY` jobs concurrently with an `asyncio.Semaphore`, heartbeats every 15 s, runs the reaper every 30 s, handles SIGINT/SIGTERM gracefully (finish or requeue running jobs), checks `cancel_requested` between steps. Handler registry: `@handler("generate_slide")`.
- Handlers receive a `JobContext` (db session factory, storage, llm client, job row, `progress(dict)` helper that writes `job.progress` and bumps `updated_at`).
- Add a `worker` service to docker-compose and a `make worker` target.

### 3. Live updates: SSE
`GET /decks/{id}/events`: `text/event-stream`. On connect send an `snapshot` event (deck status + slides light list + active jobs). Then every ~700 ms query rows changed since the last tick (`updated_at > last_seen`) across `deck`, `slide`, `job`, `resource` and emit `deck`, `slide`, `job`, `resource` events with small JSON payloads. Send `: ping` comments every 15 s. Close cleanly on client disconnect. Frontend hook `useDeckEvents(deckId)` uses `EventSource`, reconnects automatically, and on `snapshot`/events updates the TanStack Query cache.

### 4. Ingestion: `app/ingest/`
Triggered by `POST /decks/{id}/resources` (multipart, several files): store the file via `Storage`, create the `resource` row (`uploaded`), enqueue `ingest_resource`. Limits: `MAX_UPLOAD_MB`, extension + magic-byte sniffing, reject others with a clear error.
`ingest_resource` handler by kind:
- **md/txt**: read as UTF-8 (fallback latin-1); keep as is.
- **pdf** (`pypdf`): text per page with `--- page N ---` markers; extract embedded images per page (`page.images`), keep those ≥ 200×200 px.
- **docx** (`python-docx`): paragraphs in order with heading levels converted to `#` markers, tables flattened as pipe rows, inline images via relationships.
- **pptx** (`python-pptx`): per slide `--- slide N ---`, title, text frames in reading order, tables, notes text; pictures from shapes.
- **image**: the file itself is the image.
For every extracted image: Pillow-open, convert to RGB/RGBA PNG (or keep JPEG), downscale so the long side ≤ 1600 px, compute SHA-1 hex of the final bytes → `asset.id`, upsert `asset`, create `resource_image` with `locator` (e.g. "page 3"). Then caption each image with the vision model (`structured_call` with `ImageCaption{caption ≤ 160 chars, kind: photo|screenshot|chart|diagram|logo|other}`; a batch of up to 4 images per call; skip silently if no vision model is configured). Store text on `resource.text` truncated to `MAX_RESOURCE_CHARS` with a `meta.truncated` flag. Failures set `resource.status=failed` with a readable error and never block other resources. When all resources of a deck are parsed, nothing else happens automatically (the user starts planning).

### 5. LLM client: `app/llm/client.py`
Implement `structured_call` per SPEC §10: LiteLLM `acompletion`, JSON-schema `response_format` where supported, fallback to JSON-only prompting, Pydantic validation, up to 2 repair turns that append the assistant's invalid output and a user message containing the validation errors verbatim, timeouts from config, `llm_call` rows (tokens, latency, ok/error), image inputs as base64 data URLs. Add `FakeLLM` (selected by `FAKE_LLM=1` or injected in tests): returns canned or rule-based outputs by `purpose`, deterministic, supports simulated latency and injectable failures. Add a `--fake` path in the dev docs so the whole app can be demoed without a key.

### 6. Prompts: `app/llm/prompts/*.md.j2`
Write these as Jinja2 templates. Starting drafts (refine wording as you test, keep the rules):

**planner_system**
```
You are a presentation strategist who thinks in diagrams. You turn a brief and source notes into a slide plan.
Rules:
1. Output ONLY JSON matching the provided schema.
2. Every slide communicates exactly ONE idea; title is an assertion (the takeaway), at most 8 words.
3. Start with a cover slide and end with a closing/summary slide unless slide_count is too small.
4. Narrative flow: setup → problem/context → approach → details → result → next steps (adapt to the material).
5. Aim for the target slide count (or choose 6-12 if "auto"). Honor the diagram intensity: about {{ diagram_share }} of slides should be kind "diagram" or "hybrid". Prefer a diagram when the content is a process, a structure, a system, a comparison, a timeline, a cycle, or relationships between concepts; prefer text for statements, definitions, and conclusions.
6. For each diagram slide give diagram_hint.kind (flow|hierarchy|layers|cycle|timeline|comparison|mindmap) and a one-sentence description of what the nodes and edges represent.
7. key_points: 2-6 short items using ONLY facts from the sources. Never invent statistics, names or claims. If the sources are thin, keep points generic.
8. Build a glossary of recurring terms with a short_label (≤ 3 words) to be reused as diagram node labels so terminology stays consistent.
9. Attach image_ids only when an available image (listed with caption) clearly supports the slide.
10. Tone: {{ tone }}. Audience: {{ audience }}. Density: {{ density }}. {{ extra_instructions }}
```
**planner_user**: brief text, settings, resources (id, filename, truncated text), image catalog (asset id, caption, kind, locator), and for regeneration the previous plan plus the user's feedback ("revise the plan accordingly; keep slide keys stable where slides are retained").

**slide_system**
```
You are a presentation designer. You convert ONE planned slide into a structured slide specification (SlideIR). Output ONLY JSON matching the schema.
Rules:
1. One idea per slide. Respect the plan slide's intent, title (you may tighten it), key points and diagram_hint.
2. Pick the layout: cover/section/statement/text/diagram/split/two_column/image_text/closing. Use "split" when a slide needs both a short explanation and a diagram; otherwise prefer "diagram" or "text".
3. Choose the diagram kind by relationship: process or sequence → flow (or timeline if chronological); part-whole or taxonomy → hierarchy; system stack → layers; recurring loop → cycle; contrast of options → comparison (use groups, nodes carry group_id); one central concept with associated ideas → mindmap.
4. Node labels: 1-5 words (max 60 chars), nouns or short verb phrases, never sentences. Use sublabels (≤ 40 chars) only when they add information. Edge labels ≤ 3 words and only when they add meaning. Reuse glossary short_labels verbatim.
5. Respect budgets: at most {{ max_nodes }} nodes, at most {{ bullets }} bullets with at most {{ words }} words each.
6. Emphasis: at most two nodes with emphasis primary/accent; use positive/negative only for good/bad semantics; everything else normal.
7. Do not invent facts beyond the plan and sources. No markdown, no emoji, no trailing punctuation in labels.
8. Node ids: lowercase snake_case, unique, stable and meaningful (e.g. "api_gateway").
9. Use an image only if the plan slide lists image_ids; then use layout image_text (or a fitting layout) and reference the exact asset id.
```
**slide_user**: deck brief + tone/density, the full plan outline (all titles + intents, for coherence), this plan slide as JSON, relevant source excerpts (for short notes: the whole resource text, capped at 12k chars), the glossary, image catalog entries for this slide, and on retries the compiler/validator issue list: "Your previous output had these problems: ... Fix them and return the full corrected JSON."

### 7. Pipeline code: `app/llm/pipeline/`
- `plan.py`: `generate_plan(deck, resources, images, feedback=None, previous=None) -> Plan`. Post-process: enforce `slide_count` (trim/ask-to-fill rules: if the model returns too many, keep within ±1 and merge nothing silently: fail validation and use the repair loop), assign stable keys `s1..sN`, drop `image_ids` that do not exist, validate `source_refs`.
- `slide.py`: `generate_slide(deck, plan, plan_slide, ...) -> (ir, compile_result)`: LLM call → `validate_ir` (with budgets) → `compile` → if compile errors, **one extra repair round** feeding `IRIssue`/quality messages back (max 2 total). On success return IR, skeleton, warnings. On failure raise `GenerationError` with the issue list.
- Both functions are pure orchestration and take the client as a parameter (testable with `FakeLLM`).

### 8. Handlers and state transitions
- `POST /decks/{id}/plan/generate`: requires deck status `draft`/`plan_review`/`failed`; waits for resources not `parsing`; sets `planning`; enqueues `generate_plan`. Handler writes a `plan` row (`version` = max+1, `created_by=ai`, `status=draft`), sets `current_plan_id`, deck → `plan_review`.
- `GET /decks/{id}/plan`, `PUT /decks/{id}/plan` (user edits: validate with the Plan schema; creates a new version with `created_by=user`; enforce stable keys, allow add/remove/reorder/edit of slides), `POST /decks/{id}/plan/regenerate {feedback}` (enqueue with feedback + previous plan).
- `POST /decks/{id}/plan/approve`: marks the plan `approved`, creates the `slide` rows in plan order (`status=queued`, `plan_key`), deck → `generating`, enqueues one `generate_slide` job per slide. If slides already exist from an earlier approval, soft-delete them first only after flushing drafts (keep history); document this behavior.
- `generate_slide` handler: status `generating` → pipeline → create `slide_version` (`origin=ai_generate`, ir, skeleton, warnings, `prompt=null`), set current, `draft_scene=null`, status `ready`. On `GenerationError`: slide `failed` with a human-readable error and the issue list in `meta`. After each slide finishes, if no slides remain `queued|generating`: deck → `ready` (or `failed` if every slide failed) and create the first `deck_revision` (`origin=ai_generate`, snapshot of current versions).
- `POST /slides/{id}/regenerate`: re-enqueues `generate_slide` for that slide (creates a new version; old stays in history).
- `POST /jobs/{id}/cancel` sets `cancel_requested`; handlers stop at the next checkpoint, queued jobs become `cancelled`.

### 9. Frontend
- **Brief step**: textarea for the idea/prompt; settings form (slide count with an "auto" toggle, tone, diagram intensity, density, audience, extra instructions); drag-and-drop file uploader with per-file status (uploading → parsing → parsed/failed with message) fed by SSE; image resources show thumbnails with captions; button "Generate plan" (disabled until no file is parsing).
- **Plan step**: an editable outline: reorderable cards with title, role badge, kind toggle (text/diagram/hybrid), diagram kind select + description, editable key points (add/remove), image attachments (choose from the image catalog), delete, "Add slide". A feedback box + "Regenerate plan" (with a confirm that unsaved edits will be sent as the base). Save edits via `PUT` (debounced, with a visible saved state). "Approve & generate slides" button.
- **Generation progress**: after approval, a grid of slide cards with live status (queued/generating/ready/failed), a failed card shows the error and a Retry button; overall progress bar; a Cancel button; when all are ready, auto-navigate to the Slides step (pass 1 workspace) with the first slide selected. Slides whose current version has no draft are normalized by the pass-1 loader automatically.
- Global: a small jobs/status indicator in the top bar. Error toasts use the API error format.

### 10. Tests (all with `FakeLLM`, no network)
- Queue: claim concurrency (two workers never claim the same job), retry with backoff, reaper requeues a stale job, cancellation.
- Ingestion: tiny fixture files for each format (generate them in the test with python-docx/python-pptx/pypdf-compatible writers or commit small binaries): text extraction order, image extraction and downscaling, SHA-1 dedupe, failure isolation for a corrupt file.
- `structured_call`: valid output, repair loop success on the second turn, exhaustion raising, schema fallback path (use a stub provider).
- Pipeline: plan enforcement (slide count, key stability, bad image ids), slide generation happy path, compile-error repair round, final failure → `failed` slide.
- State machine integration: upload → plan → approve → all slides ready → deck `ready` → first revision exists; a mix of failed and ready slides; retry a failed slide.
- SSE: snapshot then delta events (use an async test client and short timeouts).

## Acceptance criteria

1. With `FAKE_LLM=1`: upload a Markdown file and a PDF, generate a plan, edit it, approve, watch slides appear live, open them in the editor, present and export.
2. With a real model key (if provided in the environment): same flow produces sensible, compiler-valid slides for a short notes document; paste a sample run's plan and one slide IR in `docs/PROGRESS.md`.
3. Killing the worker mid-generation and restarting it completes the remaining slides (reaper works).
4. A malformed LLM output is repaired or fails gracefully with a visible, retryable slide error.
5. `make test` and `make lint` pass.

## Handoff

Update `docs/PROGRESS.md` (architecture of the pipeline, how to run API + worker + frontend, env vars, known weaknesses, prompt tuning notes) and `docs/DECISIONS.md`. Pass 4 will extend the same handlers and prompts for editing.

## Working rules

Do not stop to ask questions; choose the simplest option consistent with the spec and record it. Verify LiteLLM, python-docx, python-pptx and pypdf behavior by running code. Never log API keys or full document contents. Commit in logical steps.
