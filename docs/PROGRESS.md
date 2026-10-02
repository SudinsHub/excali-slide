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

### Running the App
```bash
# 1. Start Postgres database
docker compose up -d

# 2. Start Backend API
cd backend
uv run uvicorn app.main:app --reload --port 8000

# 3. Start Frontend App
cd frontend
npm run dev
```

### Ready for Next Step
When resuming, we are ready to continue with browser verification or proceed into **Pass 2: IR + Compiler** as defined in `docs/pass2_ir_compiler.md`.
