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
