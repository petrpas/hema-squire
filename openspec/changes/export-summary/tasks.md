## 1. Backend: the summary computation

- [x] 1.1 `sheet._extras_by_category`: add `item_id` to each selection dict
- [x] 1.2 New `app/exportsummary.py` with a frozen `SummaryLine(kind, category, name, option, missing, paid, unpaid)` and `summary_lines(tournament, rows) -> list[SummaryLine]` per design D2: deleted rows dropped; disciplines with a queue line only where somebody is queued; offered categories in `exporttables._CATEGORY_ORDER` (expose it or add an accessor rather than import a private name); items in id order; pieces summed by `qty`; the option breakdown for declared choices (declared order with zeros, stale answers after them), free text (trim + casefold, first spelling, first appearance), missing answers, and no-option items
- [x] 1.3 `exporttables`: add `SUMMARY` kind, append the summary tab last in `tabs()`, make `find_tab` resolve it, and have `tab_counts` / the band endpoint yield `None` for it; `ExportBandTabOut.count` becomes `int | None`
- [x] 1.4 `export_api`: `GET /{slug}/export/summary` returning `ExportSummaryOut(lines=[...])` with the same access and publication guards as `/export/table`; `/export/table?kind=summary` answers 404, since the summary is not a fencer table
- [x] 1.5 Backend locale catalogs (`app/locales/cs.json`, `en.json`): `export.column.item`, `export.column.unpaid` (reuse `export.column.paid`), `export.summary.queue` ("{name} (fronta)" / "{name} (queue)"), `export.summary.option` ("{name} – {option}"), `export.summary.missing` ("neuvedeno" / "not given")

## 2. Backend: Sheets

- [x] 2.1 `sheets_export`: a `SUMMARY_SHEET = "Summary"` name and a label function composing a line's item cell from the catalog in the export locale
- [x] 2.2 `export_to_sheets`: for the summary tab, write `[header, *lines]` whole without `merge_grid`, with paid and unpaid typed as numbers; include `Summary` in the returned `worksheets`

## 3. Backend tests

- [x] 3.1 `tests/test_export_summary.py` over real `Tournament` / `Discipline` / `ExtraItem` models and replayed rows: order (disciplines, then categories in band order, items in id order); the seated/queued split matching `tab_counts`; queue row absent at zero and in manual mode; pieces summed by qty; declared choices in order with zeros; a stale answer after the declared ones; free-text folding and first-appearance order; the missing row only when nonzero; a no-option item ignoring stale answers; an offered item nobody chose at 0/0; a deleted row counting nowhere; an unsettled registration counting all its items unpaid; a team discipline absent
- [x] 3.2 `test_export_tables.py`: the band ends with the summary tab on every tournament, carries a null count, and `/export/table?kind=summary` is 404
- [x] 3.3 `test_sheets_export.py`: a Summary worksheet is written with Item/Paid/Unpaid and numeric counts; a re-export replaces a hand-typed cell in it; an English export renders the queue and missing labels in English; the worksheet list in the "worksheet per tab" test gains Summary
- [x] 3.4 Run `pytest tests/test_export_summary.py tests/test_export_tables.py tests/test_sheets_export.py -q --maxfail=3 --tb=short --show-capture=no`, then `uv run ruff check .` and `uv run basedpyright`

## 4. Frontend

- [x] 4.1 `api.ts`: `ExportBandTab.count: number | null`, the `summary` tab kind, `SummaryLine` type and `api.exportSummary(slug)`
- [x] 4.2 `export/tabs.ts`: `tabLabel` names the summary via `export.tab.summary`; `tabCount` renders nothing for a null count, and the band omits the `.tab-count` span then
- [x] 4.3 New `export/summary.ts`: `summaryLabel(t, line)` composing `LSM (fronta)`, `Triko – XL` and `Triko – neuvedeno`, and `summaryTsv(t, lines)` with the header row and no position column
- [x] 4.4 New `export/SummaryTable.tsx`: three columns (Item left, Paid and Unpaid right-aligned numeric like the other numeric columns), in the existing export table styling with no new tokens
- [x] 4.5 `ExportTables.tsx`: fetch the summary when the summary tab is open (and on `revision`), render `SummaryTable`, and route `copy()` through `summaryTsv` with the English `getFixedT` as for the other tables
- [x] 4.6 `TableOperations.tsx`: make the active-only switch optional, as `seeded` already is; the summary card passes neither and no ratings refresh
- [x] 4.7 i18n `cs.json` / `en.json`: `export.tab.summary` (Souhrn / Summary), `export.column.item` (Položka / Item), `export.column.unpaid` (Neplaceno / Unpaid), `export.summary.queue`, `export.summary.option`, `export.summary.missing`

## 5. Frontend tests and checks

- [x] 5.1 `exportTables.test.tsx`: the band's last tab is Souhrn with no count; opening it shows the lines with the queue and option labels; the rail card offers the copy but no active-only switch; switching Merch to active only, then Summary, then Merch keeps the switch on; an English copy renders the English header and `(queue)`
- [x] 5.2 From `frontend/`: `npm run typecheck`, `npm run check`, `npm test`
