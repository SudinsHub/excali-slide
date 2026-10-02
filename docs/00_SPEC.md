# Excalidraw Slide Studio: Shared Spec

Working name: `excali-slides`. Save this file in the repo as `docs/SPEC.md`. Every pass reads it first. If a pass must deviate from it, record the deviation in `docs/DECISIONS.md` and update this file so it stays true.

## 1. Product

A slide generator whose slides are editable Excalidraw scenes.

Flow: **brief (prompt + settings + uploaded notes) → presentation plan → user reviews/edits plan → slide generation → editable Excalidraw slides → AI edits (per slide or whole deck) → presentation mode → export (PDF or ZIP of PNGs).**

- A **slide** is one Excalidraw scene on a fixed 1920×1080 (16:9) logical canvas. A **deck** is an ordered list of slides.
- Output is hybrid: some slides are text (bullets, statements), some are diagrams, some mix both.
- Single user, no auth, no collaboration. It is a portfolio project, so code quality, tests, docs and a clean demo matter.
- Input resources: PDF, DOCX, PPTX, Markdown, images. Documents are short notes only (no RAG, no vector DB).
- Style controls: Excalidraw's own defaults only. The user restyles with Excalidraw's normal property panel. No deck theme system.
- Presentation mode: next/previous only. No PowerPoint export.

## 2. Locked decisions

| Area | Decision |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 (async) + asyncpg, Alembic, Pydantic v2, `uv` for deps, `ruff`, `pytest` |
| DB | PostgreSQL (jsonb for scenes/IR) |
| Jobs | Postgres-backed queue (`job` table, `SELECT ... FOR UPDATE SKIP LOCKED`), separate worker process `python -m app.worker`. No Redis |
| Live updates | Server-Sent Events (SSE) |
| LLM | LiteLLM (provider-agnostic), models set by env vars, structured output validated with Pydantic, repair-retry loop |
| Layout | Graphviz `dot` binary (flow/hierarchy) + hand-written geometry for other diagram kinds |
| Frontend | Vite + React + TypeScript, `@excalidraw/excalidraw`, Zustand, TanStack Query, Tailwind, lucide-react, `pdf-lib`, `jszip`, Vitest |
| Storage | `Storage` protocol with `LocalStorage` (filesystem dir). S3 later |
| Where IR becomes Excalidraw elements | Python emits **element skeletons** with all positions/sizes computed; the **browser** converts them with `convertToExcalidrawElements` (it measures text correctly). See §7 |
| AI editing | AI edits operate on the slide's stored **IR**, not on the Excalidraw scene. The model returns a full updated IR, code recompiles, a new version is created. Manual canvas edits are NOT analysed or merged. They stay recoverable in version history (a snapshot is taken automatically before every AI edit) |
| Presentation rendering | Pre-rendered PNGs of each slide, cached, shown full-screen. Not live Excalidraw |
| PDF export | Raster PNG per slide embedded in a 960×540 pt page, done client-side |
| Language | English slides. Non-Latin scripts are out of scope (see §14) |
| Containerization | Docker, Docker Compose |

## 3. Architecture

```
React (Vite) ── REST + SSE ──> FastAPI ──> Postgres
   │                              │            ▲
   │ Excalidraw editor,           └─ enqueue ──┤ job table
   │ skeleton→scene normalizer,                │
   │ PNG/PDF/ZIP export                 Worker process
   │                              (ingest, plan, generate, edit)
   └── assets/images ◄── LocalStorage          │
                                         LiteLLM → LLM provider
Compiler (pure Python, no I/O): IR → layout → skeleton → quality report
```

## 4. Repo layout

```
excali-slides/
  README.md  docker-compose.yml  .env.example
  docs/SPEC.md  docs/DECISIONS.md  docs/PROGRESS.md
  backend/
    pyproject.toml  alembic.ini  migrations/  Dockerfile (installs graphviz)
    app/
      main.py config.py db.py errors.py logging.py
      models/        # SQLAlchemy models
      schemas/       # API request/response models
      ir/            # IR + Plan schemas, validators, budgets   (pass 2)
      compiler/      # layouts/, palette.py, text_metrics.py, skeleton.py, quality.py (pass 2)
      api/           # routers
      services/      # decks, slides, versions, revisions, assets, storage
      jobs/          # queue.py, worker.py, handlers/          (pass 3)
      ingest/        # parsers                                  (pass 3)
      llm/           # client.py, prompts/, pipeline/           (pass 3)
    tests/
  frontend/
    src/ api/ store/ pages/ components/ excalidraw/ present/ export/ dev/
```

## 5. Data model

All ids are UUIDs except where noted. All tables have `created_at`; mutable ones have `updated_at`.

- **deck**: title, status (`draft | ingesting | planning | plan_review | generating | ready | failed`), settings (jsonb, see §6.1), current_plan_id.
- **resource**: deck_id, kind (`pdf|docx|pptx|md|image|text`), filename, mime, size, storage_key, status (`uploaded|parsing|parsed|failed`), text (parsed text), meta (jsonb), error.
- **asset**: `id` is a string (Excalidraw `fileId`, the SHA-1 hex of the bytes), deck_id, storage_key, mime, width, height. The only store for images shown in slides.
- **resource_image**: resource_id, asset_id, caption (AI-written), locator (e.g. "page 3").
- **plan**: deck_id, version (int), status (`draft|approved`), content (jsonb, §6.2), created_by (`ai|user`).
- **slide**: deck_id, position (0-based, contiguous among non-deleted), plan_key (nullable), status (`queued|generating|ready|failed`), error, current_version_id, draft_scene (jsonb, nullable), draft_rev (int, starts 0), draft_hash, draft_updated_at, deleted_at (soft delete).
- **slide_version** (immutable, append-only): slide_id, seq (1-based, unique per slide), parent_version_id, origin (`manual|ai_generate|ai_edit|user_save|user_checkpoint|restore`), prompt, summary, ir (jsonb, nullable), skeleton (jsonb, nullable), scene (jsonb, nullable), scene_hash, warnings (jsonb list). Invariant: skeleton or scene is non-null. The only allowed mutation: `scene` may be filled once from null (normalization).
- **deck_revision**: deck_id, seq, label, origin (`ai_generate|ai_deck_edit|user_checkpoint|restore|auto_before_edit`), prompt, snapshot (jsonb: `{order: [slide_id...], versions: {slide_id: version_id}, deleted: [slide_id...]}`).
- **job**: deck_id, slide_id (nullable), kind, status (`queued|running|succeeded|failed|cancelled`), priority, payload, result, progress (jsonb), attempts, max_attempts (default 3), run_after, locked_by, locked_at, cancel_requested, error, started_at, finished_at.
- **llm_call**: job_id (nullable), purpose, model, prompt_tokens, completion_tokens, latency_ms, ok, error.

### Draft / version semantics

- **Draft** = the live autosaved scene of a slide (`slide.draft_scene`), overwritten on every autosave. `draft_rev` increments on each write; writers send `if_rev` and get 409 on mismatch.
- **Version** = immutable snapshot. Created by: manual slide creation, AI generation, AI edit, user checkpoint button, auto-snapshot before AI edits (`user_save`), restore.
- A slide is **dirty** when `draft_hash != current_version.scene_hash`.
- `commit_draft(slide, origin)` creates a version from the draft (`ir = null`, since the IR no longer describes the canvas) and makes it current.
- `flush_drafts(deck)` runs `commit_draft` for every dirty slide. Called before any AI edit and before deck checkpoints.
- **Restore** never rewinds history. It creates a new version copying the target's content (`origin=restore`) and sets it current.
- **latest_ir(slide)** = the IR of the nearest ancestor version with non-null `ir`. AI edits start from this, so manual canvas changes are discarded by an AI edit (they live in the earlier version).
- When an AI operation produces a new version: `draft_scene = null`. The editor then normalizes `current_version.skeleton` into a scene in the browser and PUTs it as the draft with `normalizing_version_id`. The backend also writes it into `version.scene` (once) and sets `scene_hash`.

## 6. Content schemas (Pydantic, in `app/ir/`)

### 6.1 Deck settings
`slide_count` (int 3–30 or null = auto), `tone` (`professional|casual|playful|technical|persuasive`), `diagram_intensity` (`low|medium|high`), `density` (`light|standard|dense`), `audience` (str), `language` (default "English"), `extra_instructions` (str).

Budgets (constants in `app/ir/budgets.py`):

| | low / light | medium / standard | high / dense |
|---|---|---|---|
| share of slides with diagrams | ~25% | ~50% | ~75% |
| max nodes per diagram | 8 | 12 | 16 |
| bullets per text slide | 3 (≤8 words) | 4 (≤12 words) | 6 (≤16 words) |

### 6.2 Plan
```
Plan { title, audience, goal, narrative_summary,
       glossary: [{term, short_label}],
       slides: [PlanSlide] }
PlanSlide { key ("s1".."sN", stable),
            role: cover|agenda|section|content|process|comparison|data|summary|closing,
            title, kind: text|diagram|hybrid,
            layout_hint: Layout | null,
            diagram_hint: {kind: DiagramKind, description} | null,
            key_points: [str],
            source_refs: [{resource_id, locator}],
            image_ids: [asset_id],      # images from resources the slide should use
            intent: str }               # one sentence: what the audience should take away
```

### 6.3 SlideIR
```
SlideIR { schema_version: 1, slide_key, layout, title?, subtitle?, blocks: [Block] }
Layout = cover | section | statement | text | diagram | split | two_column | image_text | closing
Block = TextBlock | DiagramBlock | ImageBlock        (discriminated union on `type`)
TextBlock    { type:"text", style: bullets|numbered|paragraph|quote, heading?, items: [str] }
DiagramBlock { type:"diagram", kind: flow|hierarchy|layers|cycle|timeline|comparison|mindmap,
               direction: LR|TB (flow/hierarchy only), nodes: [Node], edges: [Edge],
               groups: [Group], caption? }
Node  { id (^[a-z][a-z0-9_]{0,31}$, unique per slide), label, sublabel?,
        shape: rounded|rect|ellipse|diamond|text = rounded,
        emphasis: normal|primary|accent|positive|negative|muted = normal,
        group_id? }
Edge  { source, target, label?, directed = true, dashed = false }
Group { id, label, node_ids? }
ImageBlock { type:"image", asset_id, caption? }
split: also `text_side: left|right`.  image_text: also `image_side: left|right`.
```

Layout ↔ block rules:

| layout | title | blocks |
|---|---|---|
| cover, closing | required (+ subtitle) | cover: none. closing: optional 1 TextBlock bullets ≤3 |
| section | required | none |
| statement | optional | exactly 1 TextBlock (`paragraph`/`quote`, 1 item) |
| text | required | ≥1 TextBlock |
| diagram | required | exactly 1 DiagramBlock |
| split | required | exactly 1 TextBlock + 1 DiagramBlock |
| two_column | required | exactly 2 TextBlocks (each with heading) |
| image_text | required | exactly 1 ImageBlock + 1 TextBlock |

Validation rules (reject with precise messages the repair loop can feed back to the LLM):
title ≤ 70 chars; node label ≤ 60 chars and ≤ 3 lines after wrapping; sublabel ≤ 40; edge label ≤ 30; bullets ≤ 6 and ≤ 140 chars; node ids unique; edges reference existing nodes; no self-loops; node count ≤ hard cap 16.
Per kind: `cycle` 3–8 nodes; `timeline` 3–7 nodes (list order = chronological); `comparison` 2–3 groups each with ≥1 node (nodes use `group_id`); `layers` ordered top→bottom, no edge required; `hierarchy` and `mindmap` are trees with exactly one root; `flow` any directed graph (cycles allowed), 2–16 nodes.

## 7. Compile contract

`compile(ir: SlideIR, ctx: CompileCtx) -> CompileResult { skeleton, warnings, errors, stats }`. Pure function, no I/O. `ctx` holds asset dimensions (for image sizing).

**Skeleton** (stored in `slide_version.skeleton`):
```json
{ "version": 1,
  "frame": {"width": 1920, "height": 1080},
  "elements": [ /* Excalidraw ExcalidrawElementSkeleton objects, first one is the frame */ ],
  "asset_ids": ["<asset id>", "..."] }
```
Rules:
- First element is `{type:"frame", id:"slide-frame", name:"", x:0, y:0, width:1920, height:1080, children:[...ids of all other top-level elements]}`.
- Every element has a deterministic string id (`title`, `subtitle`, `n_<nodeId>`, `e_<src>_<dst>`, `b<blockIdx>_i<itemIdx>`, ...) so snapshot tests are stable.
- Shapes carry their text via `label: {text, fontSize, strokeColor}`. Arrows use `start: {id}` / `end: {id}` so Excalidraw binds them.
- **Python hard-wraps all text** (inserts `\n`) using `text_metrics.py`, so the browser never needs wrapping logic. Container sizes are computed from wrapped text plus padding.
- Layout grid: margins 120 px left/right; title baseline region y 80–220; content region x 120–1800, y 250–1000 (full height 120–960 when there is no title).
- Font sizes: title 64 (cover 88, section 96), body 36–40 (36 in split), node labels 28, sublabels 22, captions 24. Never below 24 (hard error).
- Palette (Excalidraw defaults): text/stroke `#1e1e1e`; primary stroke `#1971c2` fill `#a5d8ff`; accent `#f08c00` / `#ffec99`; positive `#2f9e44` / `#b2f2bb`; negative `#e03131` / `#ffc9c9`; muted stroke `#868e96` fill `#f1f3f5`, text `#495057`. Filled nodes use `fillStyle:"solid"`. Everything else uses Excalidraw's default roughness and font.
- Images: `{type:"image", id, fileId:<asset id>, x, y, width, height}` (verify skeleton support in the installed version; fallback in pass 1 spike).

**Browser normalizer** (`frontend/src/excalidraw/normalize.ts`): fetch assets → build `files` map → `convertToExcalidrawElements(skeleton.elements, {regenerateIds:false})` → return `{elements, files}`. Scene stored in DB = `{elements: [...non-deleted], appState: {viewBackgroundColor:"#ffffff"}}` (no image bytes; images are re-fetched from `/assets/{id}` by fileId on load).

## 8. Job states

Deck: `draft → ingesting → planning → plan_review → generating → ready` (any → `failed`; failures are recoverable by retry).
Slide: `queued → generating → ready | failed`.
Job: `queued → running → succeeded | failed | cancelled`. Retries with exponential backoff for transient errors, a reaper requeues jobs whose heartbeat is stale.
Job kinds: `ingest_resource`, `generate_plan`, `generate_slide`, `edit_slide`, `edit_deck`, `insert_slide`.

## 9. API surface (all under `/api`)

```
Decks     POST/GET /decks   GET/PATCH/DELETE /decks/{id}
Resources POST /decks/{id}/resources (multipart)  GET /decks/{id}/resources  DELETE /resources/{id}
Assets    GET /assets/{id}   PUT /decks/{id}/assets/{file_id} (browser-pasted images)
Plan      POST /decks/{id}/plan/generate   GET /decks/{id}/plan   PUT /decks/{id}/plan
          POST /decks/{id}/plan/regenerate {feedback}   POST /decks/{id}/plan/approve
Slides    GET /decks/{id}/slides (light)   POST /decks/{id}/slides (blank)   GET/PATCH/DELETE /slides/{id}
          PUT /slides/{id}/draft {scene, if_rev, normalizing_version_id?}
          POST /slides/{id}/versions {label?}   GET /slides/{id}/versions   POST /slides/{id}/restore {version_id}
          POST /slides/{id}/regenerate   POST /slides/{id}/edit {prompt}   POST /decks/{id}/slides/insert {prompt, after_slide_id?}
Deck edit POST /decks/{id}/edit {prompt}
Revisions GET /decks/{id}/revisions   POST /decks/{id}/revisions {label?}   POST /decks/{id}/revisions/{rid}/restore
Jobs/SSE  GET /jobs/{id}   POST /jobs/{id}/cancel   GET /decks/{id}/events (text/event-stream)
Dev       POST /dev/compile {ir} (only when ENV=dev)   POST /dev/slides/{id}/apply-ir
```
Errors: `{"error": {"code": "string", "message": "string", "details": {}}}` with proper HTTP status.

## 10. LLM layer rules

- One function `structured_call(model, system, user, schema, images=None) -> BaseModel`. Sends the JSON schema via `response_format`, falls back to "JSON only" prompting if the provider rejects it, validates with Pydantic, and on failure runs up to 2 repair turns that include the validation errors verbatim.
- Models come from env: `LLM_MODEL_PLANNER`, `LLM_MODEL_SLIDE`, `LLM_MODEL_EDIT`, `LLM_MODEL_VISION`. Never hardcode a model name in code.
- Keep schemas provider-friendly: no recursion, flat structures, small enums.
- Every call is logged in `llm_call`. Never log API keys or full uploaded documents.
- Tests use a `FakeLLM` that returns canned structured outputs. No test may need a network or API key.

## 11. Frontend conventions

- Screens: Deck list → Deck workspace (steps: **Brief → Plan → Slides**) → Present (`/present/:deckId`).
- Slides screen: left rail of thumbnails (drag to reorder), center Excalidraw, right panel with AI prompt box and version history. Top bar: Present, Export PDF, Export ZIP.
- Excalidraw is remounted per slide (`key={slideId}`); flush any pending autosave before switching.
- Excalidraw setup details: import `@excalidraw/excalidraw/index.css`, give the container an explicit height, set `window.EXCALIDRAW_ASSET_PATH` to self-hosted font assets so exports and offline use are reliable, `handleKeyboardGlobally={false}`, disable load/save/export canvas actions in `UIOptions`, no collaboration UI. After load, fit the frame into the viewport (`scrollToContent` on the frame element).
- Autosave: debounce ~800 ms; only when `getSceneVersion(elements)` changed (ignore pure scroll/zoom changes); drop `isDeleted` elements before saving; send `if_rev`.
- Image files: Excalidraw `fileId` is a content hash, so on autosave upload any new file via `PUT /decks/{id}/assets/{fileId}`; on load, fetch the assets referenced by image elements.
- Unit-test pure helpers with Vitest. No test may depend on a running backend.

## 12. Engineering conventions

- Python: full type hints, `ruff` clean, small modules, no business logic in routers (use `services/`). Async everywhere in the API; the compiler is sync and pure.
- DB changes only via Alembic migrations.
- Tests: pytest + httpx `AsyncClient` against a real Postgres test database (docker-compose service), created and migrated by a fixture.
- Logging: stdlib `logging`, JSON-ish key=value lines, include `deck_id`/`slide_id`/`job_id` where known.
- Config: `pydantic-settings`, env vars documented in `.env.example`.
- At the end of every pass: update `docs/PROGRESS.md` (what is done, how to run, known issues, what the next pass must know) and `docs/DECISIONS.md` (deviations, spike results, library API facts verified against the installed versions).
- Do not rely on memory for library APIs (Excalidraw, LiteLLM, python-pptx, ...). Read the installed package's types/docs and verify by running code.

## 13. Pass map

1. **Foundation**: DB, CRUD, versions/drafts, Excalidraw editor, slide manager, presentation mode, exports. No AI.
2. **IR + Compiler**: schemas, layouts, quality gate, dev preview, fixtures.
3. **Generation pipeline**: ingestion, jobs, SSE, planner, slide generator, plan review UI, progress UI.
4. **AI editing + hardening**: slide/deck edits, revisions, restore UI, insert-slide, e2e tests, docs, demo.

## 14. Non-goals and known limitations

No collaboration, auth, PPTX export, animations/builds, speaker notes, custom themes, RAG, or non-Latin scripts. Excalidraw's built-in hand-drawn fonts probably do not cover Bengali or other non-Latin scripts (browser fallback fonts would break the text-metrics assumptions), so slide language is English for now. An AI edit rebuilds a slide from its IR and re-runs layout, so unchanged diagram parts can shift position slightly, and manual canvas edits are not carried over (they stay in version history).
