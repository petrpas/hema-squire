## 1. Backend — tab counts

- [x] 1.1 Add `exporttables.tab_counts(rows, tab) -> tuple[int, int]` returning `(count, queued)` over `table_rows`; for a discipline split on `substitute_for`, otherwise `queued` is 0
- [x] 1.2 Add `count: int` and `queued: int` to `ExportTabOut`; have `export_tabs` replay the rows once and fill both per tab
- [x] 1.3 Tests in `backend/tests/test_export_tables.py`: a discipline counts seated and queued separately; a deleted row counts nowhere; a category counts only its buyers; Fencers counts every live row; the seated/queued split counts paid and unpaid alike (manual mode needs no case of its own: nobody there is unseated)
- [x] 1.4 `pytest tests/test_export_tables.py -q --maxfail=3 --tb=short --show-capture=no`, `uv run ruff check .`, `uv run basedpyright`

## 2. Frontend — band and counts

- [x] 2.1 Add `count` and `queued` to `ExportTab` in `api.ts`
- [x] 2.2 Add pure `tabCount(tab)` in `export/` returning `"24 + 3"` or `"24"`, and render it in a `.tab-count` span in each band tab
- [x] 2.3 Re-read the band on `revision` as well as `slug`, keeping the selected tab by its id
- [x] 2.4 Put the band into the sheet header beside the title (`.export-header`: left-aligned, centred, wrapping), leaving the ≤768px `.stage-control-band` rule in force
- [x] 2.5 Tests: `tabCount` leaves out `+ 0` and states a seated zero; `tabCount` takes no switch state, so switching a tab to active only cannot change its label

## 3. Frontend — controls to the rail

- [x] 3.1 Turn the Console's `rail` element into `renderRail(panel?)`; every other phase calls it bare and keeps its panels where they are; Export passes its cards as the panel
- [x] 3.2 Create `export/TableOperations.tsx`: a rail card headed by the open tab's name with the active-only switch, the copy action and, on a discipline tab, the ratings refresh and its hint; it states the copy/refresh message
- [x] 3.3 `ExportTables` takes `renderRail`, drops the `.export-controls` strip and the message/hint lines above the table, and renders `renderRail(<TableOperations/> <ExportPanel/>)` beside its main column
- [x] 3.4 `ExportPanel` takes `onEnglishChange` and renders the English tick (behind `offersEnglishTick`) above its buttons
- [x] 3.5 Delete `.export-controls` from `index.css`
- [x] 3.6 Tests: nothing but the band above the table; the rail card is headed by the open tab and offers the ratings refresh only on a discipline; the card states the switch state of the tab it is given; the English tick sits in the Export card

## 4. Label and checks

- [x] 4.1 `cs.json`: `export.category.rental` → "Zápůjčky"
- [x] 4.2 From `frontend/`: `npm run typecheck`, `npm run check`, `npm test`, `npm run build`

## 5. Position column (owner follow-up)

- [x] 5.1 `columns.ts`: `POSITION` column (`#`) first in all three lists; `value` takes the displayed index; `toTsv` passes it
- [x] 5.2 `ExportGrid` numbers rows by draw index (straight across the line) in a `col-index` cell; `RosterTable`'s cell takes the index
- [x] 5.3 `export.column.position` in cs/en
- [x] 5.4 Tests: every table opens with the position; numbering runs across the line; the copy carries it, numbering what the filter leaves
- [x] 5.5 `npm run typecheck`, `npm run check`, `npm test`

## 6. Seeding order split from active only (owner follow-up)

- [x] 6.1 `active` and `seeded` as single booleans in `ExportTables`, each holding across tabs; `seeded` read by `RosterTable` and the copy, `active` only narrows
- [x] 6.2 `TableOperations` draws the "Pořadí dle HR" tick on a discipline only; `export.seedByRating` in cs/en
- [x] 6.3 Tests: the tick is offered on a discipline only, beside active only
- [x] 6.4 `npm run typecheck`, `npm run check`, `npm test`
