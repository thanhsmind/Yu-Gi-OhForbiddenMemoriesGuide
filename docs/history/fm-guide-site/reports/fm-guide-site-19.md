# fm-guide-site-19 — report

**Outcome:** `[BLOCKED]` before any edit was made — no writes were attempted
against `index.html` or `tools/check.py`; the cell content is unchanged.

## Blocker

This worker session's `CLAUDE_PROJECT_DIR` (write-guard root) resolves to
the main checkout
(`/home/thanhsmind/projects/goglbe/Yu-Gi-OhForbiddenMemoriesGuide`), not the
feature worktree the dispatch prompt named
(`/home/thanhsmind/projects/goglbe/Yu-Gi-OhForbiddenMemoriesGuide--wt--fm-guide-site`),
where the cell's `files` (`index.html`, `tools/check.py`) actually live. Every
attempt to write inside that worktree — via `Edit` and via a plain `Bash`
`touch` — was refused by the `bee` write-guard hook with the same message:

```
bee write guard denied this target: it could not be canonically contained
inside the physical worktree — it resolves inside worktree
"Yu-Gi-OhForbiddenMemoriesGuide--wt--fm-guide-site". FIX: open a session
with cwd=/home/thanhsmind/projects/.../--wt--fm-guide-site to work there, or
merge it back from main via `bee worktree merge --id ...`.
```

Reads worked fine (the cell's `read_first` file, the CSS/HTML/JS regions
around `view-mode`/`currentHash`/`readStateFromHash`/`applyState`/
`scheduleHashWrite`, and `tools/check.py`'s existing `fm-guide-site-17`
assertion block were all read successfully from the worktree path), and the
store commands (`bee reservations list/reserve`) work fine because the store
lives in the main checkout — only writes to worktree-resident files are
refused, uniformly and structurally, not intermittently.

**Diagnosis:** this looks like a dispatch-time gap, not a decision for the
worker to route around: the session was not actually launched with
`cwd` = the feature worktree, even though the assignment named that worktree
as "work here." There is no in-session way to change `CLAUDE_PROJECT_DIR`
(it is fixed for the process; each `Bash` call resets `cwd` to the main
checkout too, per the harness's own note). Bypassing the guard (e.g. writing
through some other path) would defeat the exact protection the guard exists
for, so this was not attempted.

## Implementation plan (verified against the code, ready for a correctly
cwd'd worker or re-dispatch)

Read and mapped before the block hit, so a re-dispatch (or a same-worker
resume with a corrected `cwd`) should be a straight execution, not more
exploration:

- HTML: add a `#grid-size-toggle` button group (`role="group"`,
  `aria-label="Cỡ lưới"`, `hidden` by default) right after the existing
  `.view-mode-toggle` span (`index.html:794-797`), reusing the `.view-mode-btn`
  class for styling/`aria-pressed` so no new CSS class is needed for the
  buttons themselves. Four buttons: `grid-size-auto` (Tự động, default
  pressed), `grid-size-4`/`grid-size-6`/`grid-size-8`, the three number
  buttons carrying `aria-label="Lưới N cột"`.
- CSS: add three `.card-grid[data-cot="N"]` rules next to the existing
  `.card-grid` block (`index.html:331-337`), each
  `grid-template-columns: repeat(auto-fill, minmax(max(110px, calc((100% -
  (N-1) * 0.75rem) / N)), 1fr))` for N = 4, 6, 8 (0.75rem matches the
  existing `.card-grid` gap). Optionally bump `.grid-tile-name`/
  `.grid-tile-num` font-size under `[data-cot="4"]` — tiles are largest there.
- JS: a `gridSize` variable outside `state` (next to `viewMode`,
  `index.html:74810`), `"tu-dong" | "4" | "6" | "8"`. `setGridSize(size)`
  sets/removes `data-cot` on `#card-grid` and syncs `aria-pressed` on the
  four buttons, mirroring `setViewMode` (`index.html:75152-75158`) —
  no re-render. `setViewMode` gains one line,
  `elGridSizeToggle.hidden = viewMode !== "luoi";`, so the group only shows
  in grid mode. Each grid-size button's click handler calls `setGridSize`
  then `scheduleHashWrite(true)` (same pattern as the two
  `elViewModeTableBtn`/`elViewModeGridBtn` listeners at
  `index.html:75160-75171`).
- Hash: `currentHash()`'s `#tra-cuu` branch (`index.html:75798-75809`) gets
  one more pair, `["cot", viewMode === "luoi" && gridSize !== "tu-dong" ?
  gridSize : ""]`, placed next to the existing `["xem", ...]` pair.
  `readStateFromHash()`'s `tra-cuu` object (`index.html:75911-75925`) gets
  `cot: (params.cot === "4" || params.cot === "6" || params.cot === "8") ?
  params.cot : "tu-dong"`. `applyState()` calls `setGridSize(st.cot)` right
  next to its existing `setViewMode(st.xem)` call (`index.html:75947`).
- `tools/check.py`: add assertions next to the existing
  `fm-guide-site-17` block (around line 1032) for: the four real
  `<button type="button">` grid-size buttons with `aria-pressed`; the
  group's `aria-label`; the three `max(110px, calc(...))` CSS rules for
  N=4/6/8; `"cot"` present in both `currentHash` and `readStateFromHash`;
  `applyState` calling `setGridSize`; the click handlers routing through
  `scheduleHashWrite(true)`.

## Reservation state

`index.html` and `tools/check.py` are still reserved under `gridder` for
`fm-guide-site-19` (never released — no write happened, nothing to clean up).
The cell is still `claimed` by `gridder`; it was not capped, blocked, or
unclaimed by this worker, so a corrected re-dispatch can either resume this
claim or the orchestrator can reassign after inspecting the gap above.
