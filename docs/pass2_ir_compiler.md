# PASS 2 of 4: IR schemas and the compiler (no LLM yet)

You are a senior engineer continuing an existing repo. Pass 1 is done. Read, in order: `docs/SPEC.md`, `docs/PROGRESS.md`, `docs/DECISIONS.md` (it contains verified facts about the Excalidraw skeleton API, frame export and fonts; trust it over any assumption).

## Goal

Build the deterministic core that turns a semantic **SlideIR** into a clean Excalidraw **skeleton**, plus a quality gate and a dev preview. After this pass, a hand-written IR JSON produces a good-looking, editable slide with no LLM involved. This is the part that decides output quality, so be rigorous.

## Out of scope

LLM calls, job queue, ingestion, plan UI. Do not touch `app/llm`, `app/jobs`, `app/ingest`.

## Tasks

### 1. IR and Plan schemas: `app/ir/`
- `schemas.py`: Pydantic v2 models exactly per SPEC §6.2 and §6.3 (`DeckSettings` already exists from pass 1; reuse it). Use `Literal` enums, `extra="forbid"`, `schema_version: 1`, sensible `Field` constraints (lengths per SPEC validation rules).
- `validators.py`: cross-field validation producing a list of `IRIssue(code, path, message)` instead of raising on the first problem, plus `validate_ir(ir) -> list[IRIssue]`. Messages must be written so they can be pasted into an LLM repair prompt (e.g. `blocks[0].nodes: cycle diagrams need 3-8 nodes, got 2`). Implement every rule in SPEC §6.3: layout↔block table, id format/uniqueness, edge references, no self-loops, per-kind constraints (tree check with single root for `hierarchy`/`mindmap`, group rules for `comparison`, ordering semantics for `timeline`/`layers`), caps and label line limits (use the text metrics to count wrapped lines).
- `budgets.py`: the table from SPEC §6.1 as typed constants and `budgets_for(settings) -> Budgets(max_nodes, bullets, words_per_bullet, diagram_share)`. IR validation takes an optional `Budgets` and then enforces `max_nodes` and bullet/word limits as **warnings** (hard caps remain errors).
- Export JSON Schema helpers: `slide_ir_json_schema()` and `plan_json_schema()` (used by pass 3). Check that the schema contains no recursion and works for a discriminated union; add a test that dumps it and asserts key properties.

### 2. Text metrics: `app/compiler/text_metrics.py`
- `measure(text, font_size) -> (width, height)` using `CHAR_W = 0.58 * font_size` average advance (tunable constant), line height `1.25 * font_size`.
- `wrap(text, font_size, max_width) -> list[str]` (greedy word wrap, hard-break words longer than the width, preserve explicit `\n`).
- Put the constants in one place with a docstring that explains they are estimates and how they were calibrated.
- **Calibration page** in the frontend (`/dev/calibrate`): for ~20 sample strings of varying length at font sizes 22/28/36/64, create real Excalidraw text elements and read their measured widths (via the element width after `convertToExcalidrawElements`), then show the ratio `width / (chars * fontSize)` per sample and an overall mean/max. Run it, then set `CHAR_W` to the mean plus a ~5% safety margin and record the result in `docs/DECISIONS.md`.

### 3. Palette and primitives: `app/compiler/`
- `palette.py`: emphasis → `{stroke, fill, text}` per SPEC §7.
- `skeleton.py`: a small builder with typed helpers (`frame()`, `text()`, `shape()`, `arrow()`, `line()`, `image()`), automatic deterministic ids, collision detection on ids, and tracking of top-level element ids for the frame's `children`. Labels in shapes are `label` objects. Standalone text must be pre-wrapped. Nothing in the builder may emit random ids or seeds.
- Shape sizing helper: `fit_node(label, sublabel, shape, font_size) -> (w, h)` with padding (28 px horizontal, 18 px vertical), min size 160×72, diamonds need extra room (multiply by ~1.5), ellipses ~1.3. Sublabel is rendered as a second line in the same label with smaller size if the skeleton supports mixed sizes; otherwise as a separate text element centered under the label inside the shape. Decide from the facts in DECISIONS.md and record it.

### 4. Page layouts: `app/compiler/layouts/page.py`
Implement each layout on the grid from SPEC §7 (margins 120, content region y 250–1000, 120–960 without title):
- `cover`: title 88 centered vertically around y≈420, subtitle 40 muted below, plus a hand-drawn accent: a `line` underline under the title (2–3 points with slight irregularity from a deterministic function, stroke accent, width 4).
- `section`: large title 96 left-aligned at vertical center with a small accent ellipse marker.
- `statement`: one big paragraph/quote, font 64, centered, wrapped at 1400 px; quotes get an oversized opening quote glyph element. Optional title small above.
- `text`: title 64 at (120, 80); each bullet is its **own text element** (so users can edit and move individually) with prefix `•  ` or `1.  `; font 40, gap 28 px. If total height overflows, step the font down 40→36→32→28; if still overflowing, emit error `text_overflow`.
- `two_column`: two columns (each 800 wide, 80 gap), heading 44 bold-feeling (use accent color) + items at 34.
- `split`: text panel 640 wide (font 34) on `text_side`, diagram region the remaining width; delegates to the diagram engine with a region rect.
- `image_text`: image fitted by aspect ratio into a 780×640 box on `image_side` (never upscale beyond the natural size; use `ctx.asset_dims`), text beside it; optional caption under the image at 24.
- `closing`: like cover, with optional bullets (max 3) at 36 below.
- `diagram`: title + diagram engine over the full content region.
Everything must land inside the frame with ≥ 40 px clearance, or the quality gate reports an error.

### 5. Diagram engine: `app/compiler/layouts/diagram/`
Interface: `layout_diagram(block, region: Rect, ctx) -> DiagramLayout` (elements + warnings). Common step: size every node with `fit_node` at font 28 (sublabel 22), compute a natural layout, then **fit to region**: first reduce gaps, then reduce node font stepwise (28→26→24); minimum font 24, otherwise emit error `diagram_too_dense` (message includes node count and a suggestion to split the slide). Center the result in the region. Never scale text with a transform.

- `flow` and `hierarchy` (`dot.py`): generate DOT with `rankdir` from `direction` (hierarchy defaults TB), fixed node sizes (`fixedsize=true`, inches = px/72), `nodesep`/`ranksep` from px, clusters for groups (flow only; draw the group as a dashed rounded rectangle with the label at its top-left, behind its nodes). Run `dot -Tjson` via `subprocess` with a 10 s timeout and clear errors if the binary is missing. Parse **node positions and cluster bounding boxes only** (flip the y-axis, convert points to px). Do not use dot's spline routing: draw straight bound arrows (`start`/`end`), and when an edge would pass through a non-endpoint node (check segment/rect intersection), render it as an elbow arrow (`elbowed` if the installed Excalidraw supports it, else a three-point arrow). Edge labels are text elements placed at the edge midpoint with a white-filled rounded rect behind them. Hierarchy edges have no arrowheads. Disconnected components must still lay out (dot handles it; verify).
- `layers`: stacked full-width bands in list order (top→bottom), each a rect with the label left-aligned inside and the sublabel on the right; band height from content, equal heights; optional small down-arrows between bands when edges exist.
- `cycle`: nodes on a circle, equal angles, first node at 12 o'clock, clockwise, radius from node sizes (so neighbors never touch), arrows between consecutive nodes plus a closing arrow; caption (if any) centered in the circle.
- `timeline`: a horizontal axis line across the region with a circle marker per milestone; labels alternate above/below the axis; label width = spacing − gap (wrap with the metrics); sublabels under labels in muted color. Emphasis colors the marker.
- `comparison`: 2–3 equal columns; each column has a header rect (group label, accent fill for the first group, primary for the second, positive for the third) and stacked rounded rects for its nodes.
- `mindmap`: root ellipse at the center; children by angle sectors allocated proportionally to the number of leaves in each subtree (full circle, root's children at radius R1, grandchildren at R2 inside the parent's sector); curved-looking links via straight bound arrows without arrowheads. Cap depth at 2 (validator error beyond that).
Document each algorithm in a docstring of ≤ 10 lines.

### 6. Compiler entry: `app/compiler/__init__.py`
`compile(ir, ctx) -> CompileResult(skeleton, warnings, errors, stats)`. Steps: validate IR (errors short-circuit with `skeleton=None`), page layout (which calls the diagram engine), assemble the frame with `children`, run the quality gate, collect `asset_ids`. `stats` = node count, element count, min font used, bounding box of content. Pure and deterministic: the same IR must always produce byte-identical JSON (test this).

### 7. Quality gate: `app/compiler/quality.py`
Operates on the produced skeleton plus layout metadata. Checks: (a) element bounding boxes inside the frame with ≥ 40 px clearance (error if outside, warning if inside the clearance); (b) no overlap between node boxes, and no overlap between text blocks and nodes (error); (c) arrows do not cross through non-endpoint nodes (warning); (d) minimum font ≥ 24 (error); (e) estimated text overflow inside containers (error); (f) edge crossings count above 6 (warning); (g) label length > 40 chars (warning). Each issue has `code`, `severity`, `element_id`, `message`. Remediation loop inside `compile`: on overflow/density errors retry up to 2 times with tighter spacing and smaller fonts before returning errors.

### 8. Dev endpoints and preview
- `POST /dev/compile {ir, asset_dims?}` returns `{skeleton, warnings, errors, stats}`.
- `POST /dev/slides/{id}/apply-ir {ir}`: validates and compiles, then creates a version (`origin=manual`, with `ir`, `skeleton`, `warnings`) as the slide's current version and clears the draft.
- Frontend `/dev/compiler` page: left a JSON editor (plain textarea with a fixture dropdown and a "format" button), right a **live Excalidraw preview** of the compiled skeleton through the pass-1 normalizer, below it warnings/errors listed with severity color, and a button "Apply to slide…" (pick deck + slide) that calls `apply-ir`. Show `stats`. Display a transparent grid overlay toggle to judge margins.

### 9. Fixtures and tests
- `backend/tests/fixtures/ir/`: at least 16 IR files: one per layout (9), one per diagram kind in a `diagram` layout (7: flow LR, flow TB with groups, hierarchy, layers, cycle, timeline, comparison, mindmap → 8 total), plus edge cases: single-node flow, disconnected flow, flow with a cycle, 16-node flow at the hard cap, very long labels, long title, 6 bullets at max length, image_text with a tall image and with a wide image, `split` with both text sides.
- Tests: every fixture validates and compiles with no errors; **golden snapshot** tests (stored JSON skeletons; provide a `--update-golden` flag); determinism test; each validator rule has a positive and a negative test with the exact message asserted; the quality gate has tests that construct bad skeletons (overlap, out of frame, tiny font); property test (use `hypothesis`) for random flow graphs up to 16 nodes and random labels: compile either returns errors with `diagram_too_dense` or a skeleton that passes the quality gate (no overlaps, inside frame).
- Skip dot-dependent tests with a clear message if `dot` is missing, but CI/Docker must have it.

## Acceptance criteria

1. All 16+ fixtures render in `/dev/compiler` as clean slides: no overlaps, readable at presentation size, arrows bound and following when nodes are moved in the editor.
2. Eyeball review: take a screenshot of each fixture's preview and critique it in `docs/PROGRESS.md` (what looks weak, what you tuned). Iterate on spacing/sizing until each looks presentable. This step is mandatory.
3. Over-long input fails with actionable messages, not crashes.
4. Applying a fixture to a slide from the dev page creates a version; the slide opens in the main editor, exports to PDF, and presents correctly.
5. `make test` and `make lint` pass; golden files committed.

## Handoff

Update `docs/PROGRESS.md` with: the public interface of `compile` and the validators, the exact list of issue codes (pass 3 feeds them to the LLM repair loop), calibrated `CHAR_W`, known layout weaknesses. Record deviations in `docs/DECISIONS.md`.

## Working rules

Do not stop to ask questions; choose the simplest option consistent with the spec and record it. Verify Excalidraw and Graphviz behavior by running code, not from memory. Keep modules small and typed. Commit in logical steps.
