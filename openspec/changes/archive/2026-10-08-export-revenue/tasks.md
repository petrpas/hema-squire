## 1. Pricing breakdown

- [x] 1.1 Extend `pricing._itemized_selection_breakdown` to record, in the same pass, each discount's deduction per category. Fixed: the per-category `take` in `_apply_fixed`. Percent: per-category `before − after`, rounded as today. Leave `registration_discounts` and the totals unchanged.
- [x] 1.2 Add `pricing.registration_breakdown(registration, tournament)`. Local lane only. It returns:
  - the priced pieces, as (category, item or discipline, unit price, qty);
  - the per-category discount deductions;

  all at `_priced_on`. It covers itemized and legacy tournaments (flat rental / afterparty fee) and teams that are not waitlisted.
- [x] 1.3 Tests in `tests/test_pricing_itemized.py`, invariants not shapes:
  - the breakdown's pieces less its deductions equals `registration_total(...).local`, for single-category, multi-category fixed, percent and early-bird cases;
  - a fully queued registration has no pieces.

## 2. Revenue computation

- [x] 2.1 New `app/exportrevenue.py`. From the replayed rows and the registrations behind them, build the blocks: Startovné, then the offered categories in band order. Within a block:
  - a line per (item, unit price), higher price first;
  - discount lines;
  - the block total;
  - then the grand total.

  Count pieces paid / all, with paid = `registration.settled`. Exclude:
  - waived registrations;
  - deleted rows;
  - rows without a registration;
  - registrations waiting wholly in the queue.
- [x] 2.2 Build the reconciliation lines 1–9 of the spec from live credits per lane. Cover waived, unsettled, queue-waiting, and cancelled/expired registrations, and unissued rows.
- [x] 2.3 `tests/test_export_revenue.py`, one test per spec scenario that is a behavioural invariant:
  - price × count;
  - two prices give two lines;
  - pieces;
  - a euro payer at the crown price;
  - a deposit is not apportioned;
  - a waived registration is on no line;
  - the queue owes nothing;
  - discount lines, including across two categories;
  - block and grand totals;
  - the reconciliation identity (2 + 4 + 5 + 6 + 7 = 9 per lane);
  - a tolerated shortfall shows in Difference;
  - a forfeited deposit is reconciled.

  Use real models, per CLAUDE.md.

## 3. API, band and Sheets

- [x] 3.1 `exporttables`: add `REVENUE` and append its tab after Summary. `tab_counts` returns `(None, 0)` for it. Update `tests/test_export_tables.py`'s band expectations.
- [x] 3.2 `GET /tournaments/{slug}/export/revenue` in `routers/export_api.py`, with the same access and publication guards as `/export/summary`. Add the response schemas in `schemas.py`.
- [x] 3.3 `POST /export/sheet` takes `finances: bool = False` beside `english` and passes it to `export_to_sheets`. Without it, `Revenue` is neither written nor touched, and is absent from the returned `worksheets`. Test both ways, plus "an existing Revenue worksheet is left as it was" against `InMemorySheets`.
- [x] 3.4 `sheets_export`:
  - add a `REVENUE_SHEET = "Revenue"` grid, written whole;
  - one block per table, a blank row between;
  - count as two numeric cells, amounts as numbers, a percent price as text.

  Wire it into `export_to_sheets`. Update the worksheet-list assertions in `tests/test_sheets_export.py` and `tests/test_team_disciplines.py`, and add a rewritten-whole test.
- [x] 3.5 Backend locale keys, cs and en:
  - `export.revenue.*`: block name `entry`, `total`, `grand_total`, `discount`, the reconciliation labels and the Difference hint;
  - column headers `price`, `count`, `to_pay`.
- [x] 3.6 `uv run ruff check .` and `uv run basedpyright` are clean. Run the scoped pytest.

## 4. Frontend

- [x] 4.1 `api.ts`: add the `ExportRevenue` types and `api.exportRevenue(slug)`. Add `"revenue"` to the tab kinds, and to `tabLabel` / `tabCount` in `export/tabs.ts`.
- [x] 4.2 `export/revenue.ts`: label composition (`Sleva <name>`, `<block> celkem`), money and count formatting (true minus, `12/18`), and `revenueTsv` in the D9 layout.
- [x] 4.3 `export/RevenueTable.tsx`:
  - one table per block with a `<colgroup>` of fixed widths (D8);
  - totals set off by `--rule-strong`;
  - the reconciliation as a two-column table of the same width.

  Add CSS in `index.css` next to the summary rules, using tokens only.
- [x] 4.4 `ExportTables.tsx`: load the revenue when its tab opens, render `RevenueTable`, and offer the copy with no active-only switch, as Summary does.
- [x] 4.5 The finances tick:
  - `Console` holds `finances` state, initially `false`, beside `english`;
  - `ExportPanel` renders the checkbox directly under the English tick for every language, with its hint that an earlier Revenue worksheet is left as it was;
  - `api.exportSheet(slug, english, finances)`.
- [x] 4.6 Frontend locale keys, cs and en, matching the backend. `locale-parity.test.ts` passes.
- [x] 4.7 `export/revenue.test.tsx`:
  - the TSV layout (blocks, blank lines, count in two cells, `%` kept);
  - English labels;
  - one table per block on screen;
  - the rail card offers the copy alone;
  - the finances tick is offered in English too, starts off, and is sent with the sheet write.
- [x] 4.8 `npm run typecheck`, `npm run check` and `npx vitest run` are clean.

## 5. Specs and check in the app

- [x] 5.1 Look at the tab in the running app on a tournament with a discount, rentals, a waived and an unsettled registration. The columns must align across blocks, and the reconciliation identity must hold on real data.
- [x] 5.2 Sync the delta specs (`export-tables`, `data-export`) and add `export-revenue` to `openspec/specs/` on archive.
