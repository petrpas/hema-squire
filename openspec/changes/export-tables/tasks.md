## 1. Ratings in the projection

- [x] 1.1 Seed `ratings` and `ranks` maps (slug → value) onto every row in `sheet.base_rows`, read from `hr_sync.latest_ratings` by `(hr_id, taxonomy_code)`; manual and imported rows get empty maps
- [x] 1.2 Add the `rating_override` rule kind to `rules.HANDLERS` — payload `{"discipline": slug, "rating": number | null}`, writing into `row["ratings"]` and auditing the field as `rating:<slug>`
- [x] 1.3 Validate the kind in `rules.create_rule`: the slug must name an individual discipline of the tournament, the rating must be a number or null
- [x] 1.4 Tests: an override survives a replay; removing the rule exposes the fetched value; a second discipline's rating is untouched; a new snapshot does not displace an override

## 2. Extras per category in the projection

- [x] 2.1 Add a per-category selections map to the projected row (category → list of `{name, qty}`), alongside the v1 slots `_extras_summary` produces
- [x] 2.2 Retire the v1-slot flattening from the row once nothing reads it; keep `weapon_rentals` and `afterparty` only while a consumer remains
- [x] 2.3 Tests: a registration with two merch items and a rental projects both categories with quantities

## 3. Export tables on the API

- [x] 3.1 A read endpoint returning the tab band for a tournament: the fencer table, the individual disciplines with their capacities, and the item categories that have items
- [x] 3.2 A read endpoint returning one table's rows — replayed rows narrowed to the tab, with seated and substitute membership stated per discipline so the client draws the line without a second query
- [x] 3.3 Publication gate on both, as every export is gated
- [x] 3.4 Tests: a team discipline yields no tab; an empty category yields no tab; a deleted row appears in no table

## 4. The rating refresh

- [x] 4.1 Confirm and test that `hr_sync.take_snapshot` fetches and parses each fighter page once per run across all taxonomy codes
- [x] 4.2 Make the ratings-refresh action reachable from a discipline tab, refreshing the tournament and saying so
- [x] 4.3 Test: a refresh after an override leaves the override standing and refreshes everyone else

## 5. Sheets export takes the new shape

- [x] 5.1 Replace `FENCERS_HEADER` and `DISCIPLINE_HEADER` with the export tables' columns, and add an item-category header
- [x] 5.2 Write one worksheet per item category the tournament offers, named for the category
- [x] 5.3 Read the rating from the replayed row rather than the ratings lookup, so an override is what is written; keep `PRESERVED` and `REFRESHED` as they are
- [x] 5.4 Take a locale on the export and render headers and yes/no through `app.i18n.Catalog`
- [x] 5.5 Tests: `Reg.`/`No.` survive a re-export against a grid in the old format; an override is written; a category with no items produces no worksheet; an English export carries English headers

## 6. Console: the tab band

- [x] 6.1 New `frontend/src/export/` directory — the orchestrator and the tab band, deriving tabs from the tournament, with `useTabBand` keeping the selection visible
- [x] 6.2 A shared column-definition module read by every table and by the TSV builder, so a column is declared once
- [x] 6.3 `FencersTable`, `RosterTable`, `ItemsTable`, one file each
- [x] 6.4 Per-tab all/active-only switch; active means `row["paid"]`, the settled derivation, so a waived registration is active and one credited nothing is not
- [x] 6.5 `Console.tsx`: drop the Export entry from `PHASE_COLUMNS` and put Export among the phases that replace the fencer table
- [x] 6.6 Tests: the band derives from the tournament; the switch is per tab; an item tab lists only its buyers; a registration priced at zero with no credit is not active

## 7. Console: the roster tab

- [x] 7.1 Seeding order under active-only — rating descending, unrated last in registration order
- [x] 7.2 The capacity line: seated above, substitutes below in queue order, with the line labelled as a queue boundary or a capacity mark according to what the tournament holds
- [x] 7.3 The rating cell editable through `EditableCell`, writing a `rating_override` rule; rank read-only
- [x] 7.4 The corrected rating marked as a manual edit, and present in the phase's manual-edits log with its discipline named
- [x] 7.5 Tests: a high-rated substitute stays below the line; a tournament with no queue gets the capacity mark; a typed rating reorders the tab

## 8. Copy and English

- [x] 8.1 The copy action: the visible table as TSV with a header row, following the filter and the order, carrying no line and no edit marking
- [x] 8.2 The English tick, offered only when the interface language is not English, governing the copy and the sheet write and not the screen
- [x] 8.3 Czech and English catalogue entries for every column header, the yes/no values, the tab labels and the line's two labels
- [x] 8.4 Tests: the copy follows the filter; the English copy renders headers and yes/no in English while the screen does not change; the tick is absent for an English interface

## 9. Finish

- [x] 9.1 `ExportPanel` keeps the JSON download and the sheet write; its wording follows the new sheet shape
- [x] 9.2 From `backend/`: `uv run ruff check .`, `uv run basedpyright`, `uv run pytest tests -q --maxfail=3 --tb=short --show-capture=no`
- [x] 9.3 From `frontend/`: `npm run typecheck`, `npm run check`, `npm test`
- [x] 9.4 Delete `openspec/changes/export_tables.md`, the source note this change absorbs
