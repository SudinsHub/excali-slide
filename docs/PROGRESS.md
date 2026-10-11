# Progress & Handoff Log

## Pass 1: Foundation (Completed)

### Completed Work
1. **Repository & Infrastructure**:
   - Initialized Git repository.
   - `docker-compose.yml` configured with PostgreSQL 16 (`slides` dev DB and `slides_test` test DB) with auto-creation of `slides_test`.
   - Backend `Dockerfile` created with `graphviz` and `uv`.
   - `.env.example`, `.env`, and root `Makefile` created for `dev`, `test`, `lint`, and `migrate`.

2. **Backend (Python 3.12+ / FastAPI / SQLAlchemy 2.0 Async / Alembic)**:
   - Data models in `app/models/` matching SPEC §5: `deck`, `resource`, `asset`, `resource_image`, `plan`, `slide`, `slide_version`, `deck_revision`, `llm_call`.
   - Alembic migration `0001_initial_schema` created and applied cleanly.
   - Storage service (`LocalStorage`) with path traversal security enforcement.
   - Deck CRUD services & API router (`POST/GET/PATCH/DELETE /api/decks`).
   - Slide services & API router (`/api/decks/{id}/slides`, `/api/slides/{id}`, `/duplicate`, `/reorder`, soft deletion with position compaction).
   - Draft service with optimistic concurrency (`if_rev`), canonical sha1 hashing, single-write `version.scene` normalization, and `flush_drafts`.
   - Version history service (`POST /versions` checkpoints, `POST /restore` non-destructive restoration, version listing).
   - Asset upload & serving (`PUT /api/decks/{id}/assets/{file_id}`, `GET /api/assets/{id}`) with Pillow dimension detection.
   - Dev sample deck generator (`POST /api/dev/decks/sample`) with 4 fixture skeletons: Cover, Bullets, Diagram (labeled shapes + bound arrows), and Image slide with on-the-fly PNG generation.
   - **Backend Tests**: 7 integration tests in `backend/tests/` passing with 100% green:
     - `test_decks.py`
     - `test_slides.py`
     - `test_drafts_and_versions.py`
     - `test_assets_and_storage.py`
     - `test_dev_sample.py`
   - `ruff check .` and `ruff format .` are 100% clean.

3. **Frontend (Vite / React / TypeScript / Tailwind / Excalidraw)**:
   - Types, API client, and Zustand store implemented.
   - `src/excalidraw/normalize.ts`: `normalizeSkeleton` and `loadSlideForEditor` with priority fallback.
   - Excalidraw editor (`ExcalidrawEditor.tsx`) with frame fitting, debounced autosave (800ms) on element change, `if_rev` concurrency tracking, and paste-image asset uploading.
   - `ThumbnailsRail.tsx`: Slide numbers, client-rendered canvas thumbnails with caching, drag-and-drop reordering, duplicate, delete.
   - `RightPanel.tsx`: Version history with origin badges, checkpoint creation, restore action, and placeholder AI tab.
   - Fullscreen Presentation Mode (`PresentPage.tsx`): 16:9 letterbox raster rendering, next/prev prefetching, keyboard shortcuts (`Space`, `Arrows`, `PageUp/Down`, `Home/End`, `F`, `Esc`), mouse click zones, and touch swipe.
   - Exporters:
     - PDF export via `pdf-lib` (960×540 pt pages, full bleed, High/Standard quality options).
     - ZIP export via `JSZip` (`slide-01.png` ... sequential PNG package).
   - Spike test page at `/dev/spike`.
   - **Frontend Tests**: 12 Vitest unit tests in `src/__tests__/` passing with 100% green (`autosave.test.ts`, `normalize.test.ts`, `export.test.ts`).
   - Production bundle (`npm run build`) builds cleanly with no TypeScript errors.

### Running the App (Dockerized)
```bash
# Start all services (PostgreSQL, Backend with Graphviz, Frontend with Vite)
docker compose up -d

# Backend API: http://localhost:8000
# Frontend App: http://localhost:5173
# IR Compiler Playground: http://localhost:5173/dev/compiler
# Font Calibrator: http://localhost:5173/dev/calibrate
```

## Pass 2: IR Schemas & Compiler (Completed)

### 1. Completed Deliverables
- **IR Schemas (`app/ir/schemas.py`)**:
  - Pydantic v2 strict models (`extra="forbid"`) for `Plan`, `PlanSlide`, `SlideIR`, `TextBlock`, `DiagramBlock`, `ImageBlock`, `Node`, `Edge`, `Group`.
  - JSON schema exports via `slide_ir_json_schema()` and `plan_json_schema()`.
  - Density budgets (`app/ir/budgets.py`): `light`, `standard`, `dense` density rules.
- **Cross-Field IR Validators (`app/ir/validators.py`)**:
  - Validates all 9 layouts and 7 diagram kinds (`flow`, `hierarchy`, `layers`, `cycle`, `timeline`, `comparison`, `mindmap`).
  - Emits structured `IRIssue(code, path, message, severity)` suitable for direct injection into Pass 3 LLM repair loops.
- **Text Metrics Engine (`app/compiler/text_metrics.py`)**:
  - Calibrated Virgil hand-drawn font estimator (`CHAR_W_RATIO = 0.58`, `LINE_HEIGHT_RATIO = 1.25`).
  - Preserves explicit newlines and applies greedy wrapping.
- **Layout Engines (`app/compiler/layouts/`)**:
  - Page layouts: `cover`, `section`, `statement`, `text`, `two_column`, `split`, `image_text`, `closing`, `diagram`.
  - Diagram layouts:
    - `flow` & `hierarchy`: Subprocess Graphviz `dot -Tjson`, inverted Y-axis, 3-point collision detour routing for straight arrows.
    - `layers`: Stacked horizontal bands with centered text and sequential connectors.
    - `cycle`: Equal-angle circular distribution starting at 12 o'clock, radius sized to avoid neighbor collisions, closing connector.
    - `timeline`: Horizontal milestone cards with alternating top/bottom placement and axis marker highlights.
    - `comparison`: 2-3 column cards with colored headers (`accent`, `primary`, `positive`).
    - `mindmap`: Root ellipse with widescreen elliptical sector allocation (`rx1=340, ry1=220, rx2=580, ry2=300`) capped at depth 2.
    - Adaptive density font stepping (28px -> 26px -> 24px) before raising `diagram_too_dense`.
- **Quality Gate (`app/compiler/quality.py`)**:
  - Bounding box frame clearance (error if outside, warning if within 40px margin).
  - Element and node overlap detection.
  - Arrow collision detection with intermediate non-endpoint nodes.
  - Minimum font size verification (error if `< 24px`).
  - Edge crossings count (warning if `> 6`).
  - Label length checks (warning if `> 40` chars).
- **Compiler Entry Point (`app/compiler/__init__.py`)**:
  - `compile(ir, ctx) -> CompileResult(skeleton, warnings, errors, stats)`.
  - Pure, deterministic compilation verified by byte-identical JSON tests.
- **Dev Endpoints & Playground**:
  - `POST /api/dev/compile`: Validates and compiles arbitrary IR payloads.
  - `POST /api/dev/slides/{id}/apply-ir`: Creates a manual slide version and clears draft.
  - `/dev/compiler`: Full-featured two-column playground with fixture selector, JSON editor, live Excalidraw preview, margin overlay guides, diagnostics display, and slide applicator.
  - `/dev/calibrate`: Interactive font character ratio calibrator.
- **Test Suite & Golden Snapshots**:
  - 26 test fixtures in `backend/tests/fixtures/ir/` covering every layout, diagram kind, and edge condition.
  - Golden snapshot test suite with `--update-golden` flag support.
  - Hypothesis property fuzzing test generating arbitrary graph topologies up to 16 nodes.
  - Total backend tests: **29/29 passed (100% green)** in Docker.
  - Total frontend tests: **12/12 passed (100% green)** in Docker.
  - Ruff linter: **All checks passed (0 errors)**.
  - Frontend production build (`npm run build`): **Passes cleanly**.

---

### 2. Public Interface of `compile` and `validators`

#### `app.compiler.compile`
```python
def compile(ir: SlideIR | dict[str, Any], ctx: CompileCtx | None = None) -> CompileResult:
    ...
```
- **Inputs**:
  - `ir`: `SlideIR` instance or equivalent JSON dict.
  - `ctx`: Optional `CompileCtx(asset_dims: dict[str, tuple[float, float]], seed: int)`.
- **Returns**: `CompileResult`:
  - `skeleton`: Pydantic `Skeleton` or `None` if validation fails.
  - `warnings`: `list[QualityIssue]`
  - `errors`: `list[QualityIssue]`
  - `stats`: `dict` with keys: `node_count`, `element_count`, `min_font_used`, `bounding_box` (or `bbox`).

#### `app.ir.validate_ir`
```python
def validate_ir(ir: SlideIR, settings: DeckSettings | None = None) -> list[IRIssue]:
    ...
```
- **Inputs**:
  - `ir`: `SlideIR` instance.
  - `settings`: Optional deck settings to determine density budgets (`light`, `standard`, `dense`).
- **Returns**: `list[IRIssue]`. Any issue with `severity == "error"` causes compilation to abort early.

---

### 3. Exact List of Issue Codes (Pass 3 LLM Repair Loop)

| Issue Code | Severity | Description |
|---|---|---|
| `unsupported_layout` | error | Layout identifier is not one of the 9 allowed layouts. |
| `invalid_block_type` | error | Block type not supported for the slide layout. |
| `missing_diagram_block` | error | `diagram` layout provided without a diagram block. |
| `multiple_diagram_blocks`| error | More than 1 diagram block specified on a single slide. |
| `too_many_blocks` | error | Total blocks exceed density budget maximum. |
| `empty_block` | error | Block has 0 items or no content. |
| `too_many_bullets` | error | Number of bullet items exceeds budget. |
| `bullet_text_too_long` | error | Individual bullet text exceeds character budget. |
| `statement_too_long` | error | Statement / quote text exceeds character budget. |
| `node_count_out_of_range`| error | Node count is outside allowed min/max range for diagram kind. |
| `empty_node_label` | error | Node label is empty or whitespace. |
| `node_label_too_long` | error | Node label exceeds maximum character limit. |
| `duplicate_node_id` | error | Duplicate node ID found within diagram block. |
| `edge_node_not_found` | error | Edge references a non-existent `from_node` or `to_node`. |
| `self_loop_edge` | error | Edge connects a node to itself. |
| `duplicate_edge` | error | Duplicate edge connecting the same pair in the same direction. |
| `group_node_not_found` | error | Group definition references a non-existent node ID. |
| `empty_group` | error | Group contains 0 node members. |
| `mindmap_depth_exceeded`| error | Mindmap hierarchy tree depth exceeds maximum depth of 2. |
| `cycle_diagram_has_edges`| warning | Explicit edges provided for `cycle` (edges are auto-generated). |
| `timeline_has_edges` | warning | Explicit edges provided for `timeline` (milestones are placed on axis). |
| `comparison_no_groups` | error | `comparison` diagram must define 2 or 3 groups. |
| `diagram_too_dense` | error | Diagram cannot fit in the canvas region even after font downscaling to 24px. |
| `frame_overflow` | error | Element extends outside the 1920×1080 slide frame. |
| `low_frame_clearance` | warning | Element is within 40px of canvas boundaries. |
| `element_overlap` | error | Two nodes or text containers overlap in canvas coordinates. |
| `arrow_crosses_node` | warning | Edge arrow passes directly through a non-endpoint node. |
| `font_too_small` | error | Element font size is below minimum allowable threshold (< 24px). |
| `text_overflow` | error | Text content exceeds container bounding box. |
| `excessive_edge_crossings`| warning| Edge crossing count exceeds readability threshold (> 6 crossings). |
| `label_too_long` | warning | Rendered node label length exceeds recommended 40 characters. |

---

### 4. Calibrated Font Metric (`CHAR_W`)
- Font: **Virgil** (Excalidraw default hand-drawn font)
- **`CHAR_W_RATIO = 0.58`**: Average character advance width is `0.58 * font_size` px.
- **`LINE_HEIGHT_RATIO = 1.25`**: Line height spacing is `1.25 * font_size` px.
- Container padding: minimum 24px horizontal, 16px vertical.

---

### 5. Known Layout Weaknesses & Tuning Notes
- **Graphviz Straight Arrows**: Graphviz `dot` spline paths can occasionally curve closely past adjacent nodes in complex dense graphs; the straight-bound arrow router uses Liang-Barsky segment collision checks to insert a midpoint detour when crossing nodes.
- **Mindmap Radial Space**: In standard widescreen 16:9, vertical room (760px) is tighter than horizontal room (1680px). Elliptical layout allocation keeps depth-2 branches balanced without clipping top/bottom headers.
- **Timeline Milestones**: Milestone cards must have an inset of `card_w / 2` from the horizontal margins to avoid left/right canvas clipping on the first and last milestones.

---

### Ready for Next Step
Pass 2 is complete and all acceptance criteria are met.

---

## Pass 3: Generation Pipeline (Completed)

### 1. Architecture Overview
The generation pipeline implements an end-to-end AI workflow from raw documents to editable Excalidraw slides:
```
[User Brief + Notes (PDF, DOCX, PPTX, MD, TXT, Images)]
                         │
                         ▼
             app/ingest/parsers.py
  (Text extraction, Image extraction & SHA-1 dedupe, <=1600px downscaling)
                         │
                         ▼
             app/llm/pipeline/plan.py
   (Jinja2 prompt + structured_call -> Plan Pydantic schema)
                         │
                         ▼
        User Review & Outline Editing (PlanStep.tsx)
  (Reorder slides, edit key points, change diagram kinds, pick images)
                         │
                         ▼
                 Plan Approval
                         │
                         ▼
               Postgres Job Queue
  (Atomic claim CTE FOR UPDATE SKIP LOCKED, parallel workers)
                         │
                         ▼
             app/llm/pipeline/slide.py
   (SlideIR generation -> Quality Gate repair loop -> Compiler)
                         │
                         ▼
               Live SSE Event Stream
   (Snapshot on connect, 700ms delta polling for deck, slides, jobs, resources)
                         │
                         ▼
        Deck Workspace (Excalidraw canvas, version history, export)
```

### 2. How to Run (API + Worker + Frontend)
```bash
# Start all core services in background (Postgres, API backend, Frontend)
docker compose up -d

# Start the background pipeline worker
docker compose up -d worker

# Apply any pending migrations
make migrate

# Run full test suites
make test-backend   # 50/50 tests passing (pytest in Docker)
make test-frontend  # 12/12 tests passing (Vitest in Docker)
make lint           # Ruff (backend) & tsc (frontend) clean
```

### 3. Environment Variables
Added to `.env.example` and `app/config.py`:
* `FAKE_LLM`: `0` for live LiteLLM provider, `1` for deterministic offline testing and demo mode.
* `LLM_MODEL_PLANNER`: Model string for planner (e.g. `anthropic/claude-3-7-sonnet`, `gemini/gemini-2.5-pro`, `gpt-4o`).
* `LLM_MODEL_SLIDE`: Model string for slide IR generation.
* `LLM_MODEL_EDIT`: Model string for slide revisions (Pass 4).
* `LLM_MODEL_VISION`: Model string for image captioning.
* `JOB_CONCURRENCY`: Worker concurrency limit (default: `4`).
* `MAX_RESOURCE_CHARS`: Character budget cap for ingested document text (default: `60000`).
* `LLM_TIMEOUT_S`: Request timeout for LiteLLM calls (default: `120`).

### 4. Sample Pipeline Artifacts

#### Sample Plan (`Plan` IR):
```json
{
  "title": "Modern Distributed Microservices Architecture",
  "theme": "dark",
  "target_slide_count": 3,
  "slides": [
    {
      "key": "s1",
      "position": 0,
      "title": "Modern Distributed Systems",
      "layout": "cover",
      "goal": "Introduce the distributed systems paradigm",
      "key_points": ["Scalability", "Fault tolerance", "High availability"],
      "image_ids": []
    },
    {
      "key": "s2",
      "position": 1,
      "title": "Event-Driven Pipeline Architecture",
      "layout": "diagram",
      "diagram": {
        "kind": "flow",
        "description": "Client requests flow through API Gateway to Event Bus and Processing Workers"
      },
      "goal": "Illustrate asynchronous decoupled message processing",
      "key_points": ["Decoupled services", "Durable queues"],
      "image_ids": []
    },
    {
      "key": "s3",
      "position": 2,
      "title": "Key Reliability Takeaways",
      "layout": "closing",
      "goal": "Summarize architecture benefits",
      "key_points": ["Zero single point of failure", "Observable tracing"],
      "image_ids": []
    }
  ]
}
```

#### Sample Slide IR (`SlideIR` with flow diagram):
```json
{
  "layout": "diagram",
  "title": "Event-Driven Pipeline Architecture",
  "kicker": "SYSTEM ARCHITECTURE",
  "blocks": [
    {
      "type": "diagram",
      "diagram": {
        "kind": "flow",
        "nodes": [
          {"id": "n1", "label": "Client Apps", "role": "accent", "shape": "rectangle"},
          {"id": "n2", "label": "API Gateway", "role": "primary", "shape": "rectangle"},
          {"id": "n3", "label": "Kafka Event Bus", "role": "muted", "shape": "rectangle"},
          {"id": "n4", "label": "Worker Fleet", "role": "positive", "shape": "rectangle"}
        ],
        "edges": [
          {"from_node": "n1", "to_node": "n2", "label": "HTTPS"},
          {"from_node": "n2", "to_node": "n3", "label": "Produce"},
          {"from_node": "n3", "to_node": "n4", "label": "Consume"}
        ]
      }
    }
  ]
}
```

### 5. Known Weaknesses & Prompt Tuning Notes
- **JSON Schema Strictness Across Providers**: Certain LiteLLM providers reject complex `json_schema` definitions with `additionalProperties: false` or nested definitions. `LiteLLMClient` incorporates an automatic fallback that injects the schema directly into the prompt system message if the provider raises a schema error.
- **Microsecond Clock Skew in SSE Polling**: In rapid programmatic mutations, testing timestamp comparisons (`updated_at > last_seen`) requires microsecond precision or clean generator teardown to avoid false idle ticks.
- **Worker Reaping vs Concurrency**: Worker reaps stale jobs older than 90 seconds. In long LLM generation calls (`LLM_TIMEOUT_S=120`), heartbeats must tick regularly (every 15s) to prevent the reaper from prematurely claiming active long-running calls.

### 6. Test Suite & Verification
- **Backend**: **50/50 integration and unit tests passing** (`pytest` in Docker).
  - `test_queue.py`: Atomic CTE claims, exponential backoff, retry exhaustion, reaper recovery.
  - `test_ingest.py`: Sniffing magic bytes, text extractors, image deduplication, downscaling, corrupt file isolation.
  - `test_llm_client.py`: Valid schema generation, 2-turn repair loop, schema fallback, fake LLM.
  - `test_pipeline.py`: Plan enforcement, slide generation, compiler error repair round, failed slide isolation.
  - `test_state_machine.py`: Full state machine (Brief -> Plan -> Approve -> Ready -> First revision snapshot).
  - `test_sse.py`: Snapshot event emission and live delta event streaming.
  - Legacy test suite (Pass 1 & Pass 2): 29 compiler, deck, and draft tests 100% passing.
- **Frontend**: **12/12 Vitest tests passing** (`npm test -- --run`).
- **Linters**:
  - `ruff check .` & `ruff format --check .`: 0 errors.
  - `tsc --noEmit` & `npm run build`: 0 errors, production bundle built cleanly in ~31s.

