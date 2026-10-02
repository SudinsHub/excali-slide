# PASS 4 of 4: AI editing, deck revisions, hardening

You are a senior engineer finishing a project. Passes 1-3 are done. Read, in order: `docs/SPEC.md`, `docs/PROGRESS.md`, `docs/DECISIONS.md`. Reuse the existing queue, `structured_call`, compiler, prompts and frontend patterns; do not reinvent them.

## Goal

Let the user change slides with prompts (one slide or the whole deck), undo anything at slide or deck level, insert new AI slides, and ship the project in a polished, documented, demo-ready state.

Key rule from SPEC §2: **AI edits work on the slide's stored IR, not on the Excalidraw scene.** The model returns a full updated IR, code recompiles it, and a new version is created. Manual canvas edits are not analysed or merged; they are always snapshotted into history first, so nothing is lost.

## Tasks

### 1. Slide edit pipeline
`POST /slides/{id}/edit {prompt}` (409 if the slide is `queued|generating`) → enqueue `edit_slide` (payload: prompt). Handler:
1. `flush_drafts` for this slide (`commit_draft(origin=user_save)` if dirty) so manual work is in history.
2. Find `latest_ir(slide)` (SPEC §5). If none exists (blank/manual slide), switch to "generate from instruction": build a minimal `PlanSlide` from the prompt (role `content`, kind inferred by the model) and run the pass-3 `generate_slide` with the user's text as the intent; mark the version `origin=ai_edit`, `summary="Generated from prompt"`.
3. Otherwise call `edit_slide_ir(...)` with: the current IR JSON, the user's instruction, the deck brief/tone/density, the plan slide (if any), the glossary, the image catalog, budgets, and the schema. Output type `EditResult {ir: SlideIR, summary: str (≤ 140 chars, imperative past tense: "Added a caching step between API and DB")}`.
4. Validate (`validate_ir`) and compile; one extra repair round on errors, as in pass 3.
5. Create a `slide_version` (`origin=ai_edit`, `prompt`, `summary`, ir, skeleton, warnings), set current, `draft_scene=null`, slide `ready`. Return the summary and a computed IR diff in `job.result`: added/removed/changed node ids, changed text, layout changes.
On failure the slide keeps its previous current version and shows an error toast (the slide is never left in a broken state).

**Prompt `edit_system`** (write as a template, refine while testing):
```
You edit ONE slide specification (SlideIR). You receive the current SlideIR as JSON and an instruction from the user. Return ONLY JSON matching the schema {ir, summary}.
Rules:
1. Make the smallest change that fully satisfies the instruction. Keep everything else byte-identical: layout, titles, node ids, labels, edge structure, emphasis, ordering.
2. Never rename or reorder existing node ids unless the instruction requires it. New nodes get new unique snake_case ids.
3. You may change the layout or diagram kind only if the instruction asks for it or requires it (for example "turn this into a timeline" or "add an image").
4. Obey the same constraints as generation: label lengths, budgets ({{ max_nodes }} nodes, {{ bullets }} bullets of at most {{ words }} words), layout/block rules, glossary terms, no invented facts, at most two emphasized nodes.
5. If the instruction is impossible or contradicts the constraints, do the closest valid thing and say so in summary.
6. "Simplify" means fewer nodes or shorter text; "expand" means add detail within budgets; "restyle/colors" means emphasis fields only.
```
Also support image instructions: the catalog of deck assets is provided so "put the architecture screenshot on the right" can resolve to an `asset_id`.

### 2. Deck edit pipeline
`POST /decks/{id}/edit {prompt}` (409 unless deck `ready`) → enqueue `edit_deck`. Handler:
1. `flush_drafts(deck)`, then create an `auto_before_edit` revision ("Before: <prompt truncated>") unless an identical snapshot already exists.
2. **Planner step**: `structured_call` returning `DeckEditPlan { summary, operations: [EditSlideOp{slide_id, instruction} | InsertSlideOp{after_slide_id|null, brief} | DeleteSlideOp{slide_id, reason} | ReorderOp{order:[slide_id]}] }` given the instruction, the plan, and a compact digest of every slide (position, id, title, layout, kind, node labels, bullet text; **not** the full IR). Limits: ≤ 20 operations; `DeleteSlideOp` is only allowed when the user's prompt contains explicit removal intent (validate with a simple keyword check plus the model's own justification; otherwise drop the op and note it in the result); all slide ids must exist; instructions for `EditSlideOp` must be self-contained sentences that include the relevant deck-wide intent ("Use fewer nodes: max 6").
3. **Execution**: run all slide-level operations concurrently in-process with `asyncio.gather` and the job semaphore (reuse the slide edit/generate functions, not new jobs), update `job.progress` after each, collect per-slide failures without aborting the others. Apply deletes and reorders last in a transaction.
4. Create a final `deck_revision` (`origin=ai_deck_edit`, label = planner `summary`, prompt, snapshot) even on partial success; the result reports `{applied, failed: [{slide_id, error}], skipped}`.
Prompt `deck_edit_planner_system`: explain the operation types, "choose the minimum set of slides that must change", "do not touch slides the instruction does not concern", "never delete unless asked", "return slide ids exactly".

### 3. Insert and duplicate-with-AI
`POST /decks/{id}/slides/insert {prompt, after_slide_id?}` → job `insert_slide`: builds a `PlanSlide` from the prompt using a small `structured_call` (with the deck plan and glossary for coherence), then runs `generate_slide`; creates the slide at the requested position (shift positions transactionally) with an `ai_generate` version. The slide appears immediately as `queued/generating` via SSE.

### 4. Revisions API and restore
- `GET /decks/{id}/revisions` (light list), `POST /decks/{id}/revisions {label?}` (user checkpoint after `flush_drafts`).
- `POST /decks/{id}/revisions/{rid}/restore`: in one transaction: `flush_drafts` (so current manual work is preserved), create an `auto_before_edit`-style revision of the present state, then for each slide in the snapshot: undelete if soft-deleted, and if its current version differs from the snapshot version create a new `restore` version copying that version, set current, clear draft; soft-delete slides not in the snapshot; restore `position` order from `snapshot.order`; finally create a revision `origin=restore` labeled "Restored #N". History is append-only.
- Slide-level restore (pass 1) stays as is.

### 5. Frontend
- **AI panel** (right panel tab from pass 1): a prompt box with two scope buttons, "This slide" and "Whole deck"; example chips ("Simplify", "Add a step for testing", "Make it a timeline", "Make the whole deck less dense"); while running show progress (SSE) and disable the editor for the affected slide(s) with an overlay "AI is editing…"; on success show a toast with the summary and an **Undo** button (restores the previous version/revision) and a **Show changes** popover rendering the IR diff (added/removed/changed nodes). Warn once per session, in a dismissible banner, that AI edits rebuild a slide from its structure and that manual canvas changes are kept in version history.
- **History**: slide Versions tab gets origin icons, prompt text, summary, and "Restore". New **Deck history** drawer (top bar) listing revisions with labels/time, "Save checkpoint" and "Restore". Restoring shows a confirmation that lists how many slides will change.
- **Insert**: "+ Add slide with AI" at the end of the rail and an insert button between thumbnails; opens a prompt popover.
- **Regenerate**: slide context menu → "Regenerate from plan" (pass 3 endpoint) and "Edit with AI" (focuses the AI panel).
- After any AI version is created, the slide loader normalizes the new skeleton automatically (pass 1); verify thumbnails refresh.
- Polish: empty states, error boundaries, skeletons/loading states, consistent toasts, favicon/title, keyboard shortcut cheat-sheet dialog (`?`), responsive layout down to 1280 px.

### 6. Robustness
- Idempotency: double-clicking edit/regenerate must not enqueue duplicates (reject with 409 when an active job exists for that slide/deck).
- Race safety: an AI edit job re-checks at the end that the slide's `current_version_id` has not changed since it started (e.g. user restored meanwhile); if it has, store the result as a non-current version and report `superseded`, never overwrite silently.
- Timeouts and cancellation work for edit jobs; the UI cancel button stops them cleanly.
- Add structured logging with `deck_id/slide_id/job_id` everywhere, and a `/healthz` endpoint (DB reachable, graphviz binary present, LLM configured flag).
- Cost visibility: a small `/decks/{id}/usage` endpoint summing `llm_call` tokens by purpose, shown in the deck settings dialog.

### 7. Tests
- Backend (FakeLLM): slide edit happy path creates an `ai_edit` version with `ir`, the pre-edit auto snapshot exists when the draft was dirty, edit from a version with no IR falls back to generation, `latest_ir` walks past `user_save` versions, repair round on invalid edit output, failure leaves the slide untouched, superseded edit, duplicate-enqueue 409, deck edit executes a mixed operation list with one failure and still creates the revision, delete-op rejection without removal intent, revision restore (order, undelete, soft-delete of newer slides, history append-only), insert-slide position shifting.
- Frontend (Vitest): IR diff rendering helpers, the undo flow state machine, restore confirmation counts.
- **E2E (Playwright)** with `FAKE_LLM=1`: create deck → upload a markdown file → generate plan → edit one plan card → approve → wait for slides → edit a slide with AI → undo → deck edit → restore revision → present (check slide counter) → export ZIP (assert file count). Run in CI-friendly headless mode; document `make e2e`.

### 8. Documentation and demo
- `README.md`: product overview with a short GIF/screenshots placeholder section, features, architecture diagram (Mermaid), tech choices and why (IR + deterministic compiler, Postgres job queue, browser-side normalization), quickstart (Docker compose and local), env vars table, `FAKE_LLM` demo mode, testing, project structure, limitations (SPEC §14), roadmap ideas (non-Latin fonts, vector PDF, scene-aware edits that preserve manual changes, collaboration).
- `docs/ARCHITECTURE.md`: the pipeline, state machines, version/draft/revision semantics, the compile contract, and the reasoning behind AI-edits-on-IR.
- A seeded demo: `make demo` runs migrations, loads a sample notes file, runs the full pipeline with `FakeLLM` (canned plan + 6 hand-authored IRs that show off every diagram kind) so reviewers can explore without an API key.
- `CONTRIBUTING`-style short section on adding a new diagram kind (files to touch, tests to add).

## Acceptance criteria

1. From a clean clone: `make demo` then open the app: a complete 6-8 slide deck exists with diagrams, editable, presentable, exportable.
2. "Make this simpler" on a diagram slide produces a new version with fewer nodes; Undo restores the previous one; the diff popover is accurate.
3. "Make the whole deck less dense" edits only the relevant slides, creates a revision, and restoring the earlier revision brings back the original deck exactly (positions, versions).
4. Inserting a slide with AI in the middle of the deck works and shifts positions.
5. Pressing edit twice quickly does not create two jobs; cancelling mid-edit leaves the slide untouched.
6. `make test`, `make lint`, `make e2e` pass.

## Handoff

Final update of `docs/PROGRESS.md` (state: complete, known issues, ideas for next steps) and `docs/DECISIONS.md`. List any spec deviations clearly in the README.

## Working rules

Do not stop to ask questions; choose the simplest option consistent with the spec and record it. Verify behavior by running code. Keep commits logical. Quality over breadth: if time is short, finish slide edit + undo + the e2e test first, then deck edit, then insert.
