# PASS 1 of 4: Foundation (no AI)

You are a senior full-stack engineer starting a new project from an empty repo. Read `00_SPEC.md` completely before writing code, and copy it to `docs/SPEC.md`. It is the source of truth for architecture, data model, API and conventions.

## Goal

A working product shell with **no AI yet**: create decks, create and reorder slides, edit each slide in a real Excalidraw editor with autosave and version history, present the deck, and export it to PDF or a ZIP of PNGs. Hand-written fixtures stand in for AI output so the whole rendering path (skeleton → Excalidraw scene) is proven before any compiler or LLM exists.

## Out of scope this pass

Anything in `app/ir`, `app/compiler`, `app/jobs`, `app/ingest`, `app/llm`. Do not create the job table or the plan/resource/revision endpoints. Do create the data model tables listed under "Database" below.

## Tasks

### 1. Repo and tooling
- Monorepo layout from SPEC §4 (create only the folders this pass uses).
- `backend/`: `uv` project, Python 3.12, dependencies: `fastapi`, `uvicorn[standard]`, `sqlalchemy[asyncio]>=2`, `asyncpg`, `alembic`, `pydantic>=2`, `pydantic-settings`, `python-multipart`, `pillow`; dev: `pytest`, `pytest-asyncio`, `httpx`, `ruff`. Add `ruff` config and a `Makefile` (or `justfile`) with `dev`, `test`, `lint`, `migrate`.
- `frontend/`: Vite + React + TypeScript, Tailwind, `@excalidraw/excalidraw` (latest stable), `zustand`, `@tanstack/react-query`, `react-router-dom`, `lucide-react`, `pdf-lib`, `jszip`, `vitest`.
- `docker-compose.yml`: a `postgres` service (dev DB `slides`, test DB `slides_test`) with a named volume. Backend `Dockerfile` that also installs the `graphviz` apt package (needed in pass 2).
- `.env.example` with `DATABASE_URL`, `TEST_DATABASE_URL`, `STORAGE_DIR`, `ENV`, `CORS_ORIGINS`, `MAX_UPLOAD_MB` (and placeholders for the LLM vars that later passes use).
- `README.md` quickstart: how to start Postgres, migrate, run backend and frontend, run tests.

### 2. Database (SQLAlchemy models + Alembic migration 0001)
Create these tables exactly as described in SPEC §5: `deck`, `resource`, `asset`, `resource_image`, `plan`, `slide`, `slide_version`, `deck_revision`, `llm_call` (the unused ones are still created now to avoid churn). Use UUID PKs (`asset.id` is a string), `jsonb` for JSON, enums as Postgres enums or constrained strings (pick one, document it), indexes on `slide(deck_id, position)`, `slide_version(slide_id, seq)` (unique), `resource(deck_id)`. Add `created_at`/`updated_at` with server defaults and `onupdate`.

### 3. Backend services and API
Implement in `services/` (logic) and `api/` (thin routers), with the error format from SPEC §9:

- **Storage**: `Storage` protocol (`put(key, bytes) -> None`, `get(key) -> bytes`, `delete(key)`) and `LocalStorage` rooted at `STORAGE_DIR`; reject path traversal.
- **Decks**: `POST/GET /decks`, `GET/PATCH/DELETE /decks/{id}` (settings stored as jsonb; validate with a Pydantic `DeckSettings` that matches SPEC §6.1, including defaults).
- **Slides**:
  - `GET /decks/{id}/slides` returns a light list (id, position, status, title if known, current_version_id, draft_rev, dirty flag), never scene bodies.
  - `POST /decks/{id}/slides` creates a blank slide at a position (default end) with version 1 (`origin=manual`) whose skeleton contains only the frame element (SPEC §7).
  - `GET /slides/{id}` returns the slide, `current_version` (with ir/skeleton/scene) and `draft` (`scene`, `rev`, `hash`) if any.
  - `PATCH /slides/{id}` supports `position` changes: reorder transactionally and keep positions contiguous.
  - `DELETE /slides/{id}` is a soft delete (`deleted_at`) with position compaction.
  - Also a `duplicate` action: `POST /slides/{id}/duplicate` copies the current draft-or-version content into a new slide.
- **Drafts**: `PUT /slides/{id}/draft {scene, if_rev, normalizing_version_id?}`. Validate the scene shape (`elements` list of dicts with `id`/`type`, size limit 5 MB). Compute `draft_hash` = sha1 of canonical JSON (sorted keys, no whitespace). 409 with code `draft_conflict` if `if_rev` ≠ current. If `normalizing_version_id` equals the current version and that version's `scene` is null, also write `version.scene` and `scene_hash` (exactly once).
- **Versions**: `POST /slides/{id}/versions` (checkpoint: `commit_draft` with `origin=user_checkpoint`, optional label in `summary`; 409 `nothing_to_commit` if not dirty), `GET /slides/{id}/versions` (light list: id, seq, origin, summary, created_at, has_ir), `POST /slides/{id}/restore {version_id}` (creates a new `restore` version copying skeleton/scene/ir, sets it current, resets draft per SPEC §5).
- Implement `commit_draft(slide, origin, summary)` and `flush_drafts(deck)` as service functions (later passes depend on them).
- **Assets**: `PUT /decks/{id}/assets/{file_id}` (raw body or multipart; image mime allowlist png/jpeg/webp/gif/svg+xml; store bytes; read dimensions with Pillow (skip for svg); idempotent), `GET /assets/{id}` (correct content-type, long cache headers).
- **Dev fixtures**: when `ENV=dev`, `POST /dev/decks/sample` creates a deck with 4 slides whose skeletons are hand-written JSON files in `backend/app/fixtures/` covering: a cover slide (text only), a bullets slide (text elements), a diagram slide (4 labeled rectangles + bound arrows), and an image slide (generate a small PNG asset on the fly). These skeletons must follow SPEC §7 exactly (frame first with `children`, deterministic ids, `label` objects, arrows with `start`/`end`).

### 4. Frontend: Excalidraw spike FIRST
Before building UI, run these experiments in a scratch page and record the results in `docs/DECISIONS.md` (this is critical for later passes):
1. Does `convertToExcalidrawElements` accept the SPEC §7 skeleton as-is: frame with `children`, shapes with `label`, arrows with `start`/`end` ids? Does it keep given container sizes and put text in the center? Does it handle multi-line (`\n`) labels?
2. Does it accept an `image` skeleton with `fileId`? If not, implement a fallback inside `normalize.ts` that builds image elements through `restoreElements` (or equivalent) from minimal objects.
3. Frame export: can `exportToBlob`/`exportToCanvas` clip to a frame (`exportingFrame` option) and produce exactly the frame's pixel size at scale 1 and 2, with elements outside the frame excluded? If not, implement the fallback: export everything, compute bounds with `getCommonBounds`, and crop to the frame rectangle on a 2D canvas.
4. Are hand-drawn fonts present in PNG exports (not a fallback font)? What must be configured (`EXCALIDRAW_ASSET_PATH`, self-hosted fonts)? Verify by exporting a slide and inspecting it.
5. Does the frame label (name) render in the editor but not in exports? Pick the frame `name` value accordingly.

### 5. Frontend: core app
Routes: `/` (deck list: create, open, delete), `/decks/:id` (workspace), `/present/:id`.

**Normalizer** `src/excalidraw/normalize.ts`: `normalizeSkeleton(skeleton, fetchAsset) -> {elements, files}`; `loadSlideForEditor(slide)` picks draft scene → version scene → normalized skeleton (in that order) and, when normalization happened, PUTs the draft with `normalizing_version_id`. Pure and unit-tested with Vitest (mock Excalidraw conversion only if the import cannot run in jsdom; otherwise test for real).

**Workspace (Slides step only this pass)**:
- Left rail: thumbnails (generated client-side from the saved scene via the export helper at small scale, cached in memory by `slide_id:rev`), drag-and-drop reorder (use `@dnd-kit` or native DnD), add blank slide, duplicate, delete (with confirm), slide numbers.
- Center: the Excalidraw editor following SPEC §11 (remount per slide, autosave debounced with `if_rev`, fit frame on load, UIOptions trimmed, self-hosted assets). Show a save-state indicator (Saved / Saving… / Conflict / Error with retry). Handle 409 by showing a "reload slide" banner.
- Right panel with two tabs: **Versions** (list with origin badge, time, summary; "Save checkpoint" button; "Restore" on each row; restoring first warns that unsaved draft changes will be committed to history automatically via `commit_draft`) and **AI** (placeholder card: "Coming in a later pass", disabled input).
- Keyboard: `Alt+↑/↓` move between slides; ignore when typing.
- Persist the selected slide id in the URL query string.

**Presentation mode** `/present/:id`: fetch all slides, render each to a PNG blob URL (scale = min(2, devicePixelRatio)) lazily with a small LRU cache and prefetch of next/previous; show full-screen, letterboxed on black, scaled to fit; keys: →/Space/PageDown next, ←/PageUp previous, Home/End, `F` fullscreen toggle, `Esc` exit; click right/left third of the screen for next/prev; slide counter that fades after 2 s; touch swipe. Entering from the workspace starts at the selected slide. Flush dirty drafts before opening (the render must use the latest saved scene).

**Export** (`src/export/`): 
- `renderSlidePng(slide, scale)` using the method chosen in the spike.
- Export ZIP: `slide-01.png` ... zero-padded, JSZip with STORE compression, filename `<deck-title-slugified>.zip`.
- Export PDF: `pdf-lib`, one 960×540 pt page per slide, PNG embedded full-bleed, quality option Standard (scale 1.5) / High (scale 2), filename `<slug>.pdf`.
- Both: sequential rendering (never parallel), a progress dialog ("Rendering 3/12"), cancel button, `await` a macrotask between slides so the UI stays responsive. Flush dirty drafts first.

Styling: clean, minimal, light theme, Tailwind only. No component library.

### 6. Tests
- Backend (pytest, real Postgres test DB created/migrated by a session fixture, each test in a transaction or with table truncation): deck CRUD; blank slide creation; reorder keeps positions contiguous; soft delete compaction; draft PUT happy path, 409 on stale `if_rev`, normalization writes `version.scene` once; checkpoint creates a version and 409 when clean; restore creates a new version (history never rewinds); `flush_drafts` commits only dirty slides; asset PUT idempotent; path traversal rejected.
- Frontend (Vitest): `normalizeSkeleton` on each fixture; autosave debounce/`if_rev` logic as a pure state machine; PDF/ZIP helpers with a stubbed renderer (page count, filenames, ordering).

## Acceptance criteria (verify each manually and say how you verified)

1. `make dev` style flow from README works from a clean clone.
2. Create a sample deck, open it: all 4 fixture slides render as proper Excalidraw scenes, arrows are bound (move a box and the arrow follows), text is editable, the image shows.
3. Edit a slide, reload the browser: edits persist. Edit in two tabs: second save shows the conflict banner.
4. Checkpoint, make changes, restore: the canvas returns, history shows a new `restore` version.
5. Reorder, duplicate, delete slides: order survives reload.
6. Present mode works with keyboard, click and touch gestures; fonts look hand-drawn.
7. PDF has the right page count and crisp slides; ZIP has correctly named PNGs at 1920×1080 (×scale).
8. `make test` and `make lint` pass.

## Handoff

Update `docs/PROGRESS.md` (state, run instructions, known issues) and `docs/DECISIONS.md` (every spike result in section 4 with the exact library versions and the chosen approach, plus any deviation from SPEC). Pass 2 will rely on those facts, so be precise.

## Working rules

Do not stop to ask questions. When something is ambiguous, choose the simplest option consistent with SPEC and record the choice in DECISIONS.md. Verify library APIs against the installed versions instead of relying on memory. Commit in small, logical commits with clear messages.
