# Decisions Log

## Pass 1: Foundation Spike & Implementation Decisions

### 1. Excalidraw Element Skeletons (`convertToExcalidrawElements`)
- **Verified against `@excalidraw/excalidraw` 0.18.1**:
  - `convertToExcalidrawElements` accepts the SPEC §7 skeleton structure as-is with `{ regenerateIds: false }`.
  - Frame elements (`type: "frame"`) accept `children` arrays of element IDs and deterministic string IDs (`slide-frame`).
  - Container shapes (e.g. `rectangle`, `ellipse`) accept `label: { text, fontSize, strokeColor }` objects and center multi-line text with `\n` breaks within the container geometry.
  - Linear elements (`type: "arrow"`) bind cleanly using `start: { id: "n1" }` and `end: { id: "n2" }`.
  - Image elements with `type: "image"` and `fileId: "<sha1-hex>"` convert properly into `ExcalidrawImageElement`.

### 2. Frame Export & Clipping
- `exportToCanvas` and `exportToBlob` from `@excalidraw/excalidraw` accept:
  - `exportingFrame: frameElement`
  - `exportPadding: 0`
  - `getDimensions: (w, h) => ({ width: 1920 * scale, height: 1080 * scale, scale })`
- Elements outside the frame are excluded and the raster output is clipped exactly to the 1920×1080 canvas.

### 3. Font Assets & Self-Hosting
- Excalidraw's built-in fonts (`Virgil`, `Cascadia`, `Excalifont`) are stored in `@excalidraw/excalidraw/dist/prod/fonts/`.
- Copied to `frontend/public/fonts/` and configured via `window.EXCALIDRAW_ASSET_PATH = '/'`.
- In JSDOM test environments, standard `FontFace` and `document.fonts` mock objects are provided in `src/setupTests.ts` so `convertToExcalidrawElements` runs real conversion tests without headless browser crashes.

### 4. Database & Concurrency
- PostgreSQL 16 runs in Docker Compose (`slides` for development, `slides_test` for pytest).
- Optimistic locking for slide drafts uses `if_rev: int`. Writers send their expected revision number and receive HTTP 409 `draft_conflict` on revision mismatch.
- Checkpoints on clean slides reject with HTTP 409 `nothing_to_commit`.
- Restoring a version creates a new immutable version with `origin="restore"` and increments sequence numbers; version history never rewinds.

## Pass 2: IR Schemas & Compiler Implementation Decisions

### 5. Hand-Drawn Font Metrics Calibration
- Excalidraw's primary font (`Virgil`) was calibrated via `/dev/calibrate` across 20 representative technical strings and sizes (24, 28, 36, 64px):
  - Mean character advance ratio: `0.58 * font_size` (e.g. ~16.24px at 28px font).
  - Safety margin: Conservative padding ensures no text clip when rendered in canvas.
  - Line height: `1.25 * font_size`.
  - Greedy wrap (`wrap_text`) preserves explicit line breaks while fitting labels into calculated container widths.

### 6. Sublabel Font Size vs Minimum Font Quality Gate
- SPEC §7 allowed sublabel font size 22px, but Quality Gate rule (d) strictly forbids any font `< 24px` (`font_too_small` error).
- Decision: Set sublabels, captions, and group title headers to a minimum of 24px (`MUTED` color palette for visual hierarchy). This ensures clean quality gate compliance without visual compromise.

### 7. Overlay & Container Collisions
- Sibling bounding-box collision detection in `quality.py` checks all element pairs.
- Group backgrounds (`grp_`) and edge label pill backgrounds (`el_bg_`) intentionally wrap or sit beneath nodes and arrows.
- Decision: Exclude group containers and edge label backgrounds from direct node-to-node collision checks to eliminate false positives while preserving strict collision rejection for actual node rects.

### 8. Mindmap Aspect Ratio Adaptation
- The standard slide content area is 16:9 widescreen (`1680 × 760 px`). Purely circular mindmaps with large radial spacing easily overflow the vertical 760px bound.
- Decision: Implemented elliptical radial distribution with `rx = 340px, ry = 220px` for level 1, and `rx = 580px, ry = 300px` for grandchildren, keeping nodes fully inside frame safe boundaries.

### 9. Fully Dockerized Execution
- User constraint: All services, test runners, compilers, and frontends must run within Docker.
- Backend container includes Graphviz `dot 2.42.4`, Python 3.12, UV, and Hypothesis.
- Frontend container runs Vite HMR on port 5173 and supports in-container testing (`npm test`) and building (`npm run build`).

## Pass 3: Generation Pipeline Implementation Decisions

### 10. Atomic Job Claim via PostgreSQL CTE (`FOR UPDATE SKIP LOCKED`)
- Implemented queue concurrency without Redis or external message brokers.
- One atomic statement claims `N` jobs:
  ```sql
  WITH claimable AS (
    SELECT id FROM job
    WHERE status = 'queued' AND run_after <= NOW()
    ORDER BY priority DESC, created_at ASC
    LIMIT :n
    FOR UPDATE SKIP LOCKED
  )
  UPDATE job SET status = 'running', locked_by = :worker_id, locked_at = NOW(), ...
  WHERE id IN (SELECT id FROM claimable) RETURNING *;
  ```
- Guaranteed zero double-claims across multiple worker processes.

### 11. SSE Session Binding & Delta Polling
- In `app/api/events.py`, the `deck_event_generator` binds its session maker directly to the active database engine (`db.bind`).
- This ensures test suites execute against `slides_test` without leaking connections or locking dev databases, and keeps the generator decoupled from any global singletons.
- A 700ms delta tick emits events only when `updated_at > last_seen`, avoiding redundant network payloads.

### 12. FakeLLM for Deterministic Zero-Network CI
- `FakeLLM` provides full mock support for `Plan`, `SlideIR`, and repair flows without requiring real API keys or external network calls.
- Activated via `FAKE_LLM=1` environment variable.
- Enables complete end-to-end integration testing in headless environments.

### 13. Image Deduplication & Downscaling Strategy
- Images embedded in PDF/DOCX/PPTX notes are extracted via PIL/Pillow.
- Deduplication: SHA-1 hex digest computed on raw bytes; identical images share a single `Asset` record.
- Noise filtering: Decorative bullets and separator icons with both dimensions `< 200px` are discarded.
- Dimension bounding: Any image with long side `> 1600px` is downscaled using bicubic resample to maintain crispness while preserving canvas budget.

