## Context

The Export phase (`frontend/src/export/ExportTables.tsx`) draws three things inside `main.sheet-area`, one under another: a `.stage-control-band` of tabs, an `.export-controls` strip, and the open tab's table. The rail next to it is the Console's shared `rail` element. For this phase it holds `ExportPanel` (spreadsheet write, JSON download) and the manual-edits log.

The state behind the strip lives in `ExportTables`: the tab list, the selected tab, the per-tab active-only switches, the loaded rows, the message line and the ratings-refresh busy flag. The English tick lives in `Console`, because both the copy in `ExportTables` and the sheet write in `ExportPanel` read it.

`.sheet-area` is a flex column, so its children stretch to its width. The tabs inside `.stage-control` are only as wide as their labels, but the framed band stretches with the column. That leaves an empty framed stretch after the last tab. The Setup preview avoids this with `.preview-tabs { align-self: flex-start }`.

`GET /export/tables` returns `exporttables.tabs(tournament)`, which is derived from configuration alone and reads no rows. `sheets_export` calls the same function.

The owner's answers to the open questions are recorded in memory `export-layouts-owner-decisions`.

## Goals / Non-Goals

**Goals:**
- The band ends at its last tab.
- Every tab carries a count that does not depend on the tab's filter.
- The tab's controls move into the rail.
- The Czech rental label changes.

**Non-Goals:**
- Counts in the spreadsheet's worksheet names or in the copied table.
- Changing what any tab lists, its order, its capacity line or the paid rule.
- Restyling tab bands of other phases, or changing the band below 768px.
- Persisting the English tick or the switches beyond what they persist today.

## Decisions

### D1 — The band stands on the title's line

The band moves into `.sheet-header`, beside the "Exportní tabulky" title (owner's follow-up request). In that row it is only as long as its tabs, so the empty stretch of frame goes with it. The header gets an `.export-header` modifier: items start at the left, are centred vertically, and wrap. Where the title and the band do not fit side by side, the band wraps under the title.

Below 768px the existing `.stage-control-band { width: 100% }` puts the band on its own line under the title. There it is still the full-width scroller, and `useTabBand` keeps the selected tab in view.

**Alternative rejected:** making `.stage-control` itself `align-self: flex-start` everywhere. That would reach bands whose layout nobody has asked to change.

### D2 — Counts are computed by the backend, on the tabs endpoint

`ExportTabOut` gains `count: int` and `queued: int`. The router replays the rows once, as `export_table` already does. For each tab, it counts `exporttables.table_rows(rows, tab)`. For a discipline, it splits that set: rows whose `substitute_for` names the key are `queued`, and the rest make up `count`. A new `exporttables.tab_counts(rows, tab)` holds the split, so the narrowing stays in the one module the spec says owns it.

The `Tab` dataclass and `sheets_export` are not touched.

**Alternatives rejected:**
- Fetching every table from the console to count it: one request per tab each time the band loads.
- Counting the console's own sheet rows in the frontend: a second copy of the narrowing in `table_rows`, which could drift from the spreadsheet's.

Manual mode needs no special case. Nobody there holds a `substitute_for` entry, so `queued` is 0 and the frontend leaves out `+ 0`.

### D3 — The band re-reads on the console's revision

The tabs effect today depends on `[slug]` only. It will depend on `revision` as well, which the console already bumps when rows change, so a count does not keep stating an earlier roster. The selected tab is kept across the re-read by its `kind:key` id.

### D4 — The label format is one pure function

`tabCount(tab)` returns `"24 + 3"` or `"24"`, and the tab renders it in the existing `.tab-count` span. It is a pure function so the `+ 0` rule is tested without rendering.

### D5 — `ExportTables` supplies its rail card through the console's rail

`rail` stops being a fixed element and becomes `renderRail(panel?: ReactNode)`. Every other phase calls it with the panel it has today. The Export branch passes `renderRail` into `ExportTables`, which renders its main column and `renderRail(<TableOperations …/> + <ExportPanel …/>)` side by side.

The tab state stays where it is, in `ExportTables`. Nothing is lifted into the 1100-line `Console`, and no export hook runs on other phases.

`TableOperations` (`export/TableOperations.tsx`) is a presentational card with these props: tab name, switch state and its setter, copy, and, for a discipline, the ratings refresh, the busy flag and the message.

**Alternatives rejected:**
- A `useExportBand` hook called in `Console`: hooks are unconditional, so it would run on every phase or need an `enabled` flag, and it grows `Console`.
- A React portal into the rail: layout-driven indirection for what a prop does.

### D6 — The English tick moves into `ExportPanel`

`ExportPanel` already receives `english`. It now also receives `onEnglishChange`, and it renders the tick behind `offersEnglishTick(i18n.language)` above its two buttons. The state stays in `Console`, as today.

`.export-controls` is deleted from `index.css`. Checkboxes in the rail use the rail's existing label styling.

The rail keeping these controls does not conflict with etl-console's "Operation parameters" rule. That rule keeps tournament configuration out of phase panels, and none of these controls configures the tournament.

### D7 — The label change is a translation edit

`export.category.rental` in `cs.json` becomes "Zápůjčky". No other Czech string says "Půjčovna", and `en.json` keeps "Rentals".

### D8 — The position column is a frontend column with an index

This was an owner follow-up. Every export table opens with `#`, numbered as displayed. The number travels in the copy but not in the spreadsheet. `ExportColumn.value` takes `(row, index)`, and `POSITION` is the one column that reads the index. `ExportGrid` passes the index of each drawn row, which runs straight across the capacity line because the line is interleaved rather than counted. `toTsv` passes the same index over the same ordered rows. Screen and clipboard therefore number alike without a second computation.

The backend's spreadsheet columns are not touched.

**Alternative rejected:** stamping a position onto each row before rendering. That is a second pass that the filter and the seeding order would both have to repeat.

### D9 — Seeding is its own tick, apart from active only

This was an owner follow-up. Previously, switching a discipline to active only also switched it to the seeding order. The two are now separate state in `ExportTables`: `active` narrows to the paid on every tab, and `seeded` orders by rating on a discipline. Both are single booleans rather than per-tab records, because the owner wants each to keep its value across tabs. `rosterOrder`'s `seeded` argument already kept the two apart and now reads `seeded`. `TableOperations` takes an optional `seeded` prop and draws the tick only when it is given.

## Risks / Trade-offs

- **The tabs request now replays the rows.** Its cost equals one table read, and the console already makes such a read each time a tab opens. → Acceptable; no caching.
- **The rail is taller on Export.** The tab card sits above the Export card and the edits log, which pushes the log further down. → The tab card comes first because it is used most often. The edits log was already last.
- **Counts can briefly disagree with the table.** The band and the table re-read on the same revision but in separate requests. → Both settle on the same revision; no locking.
