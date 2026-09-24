## Why

Before a tournament the organizer needs totals, not rosters: how many are seated in
each discipline and how many wait, how many of each rental to bring, how many shirts
of each size to order, how many are coming to the afterparty — and of each, how many
have paid. Today every one of those is a count done by hand over a tab of names,
and a merch tab states "Triko (XL) x2" in a cell rather than a number anyone can add.

## What Changes

- The Export band gains a last tab, **Souhrn** (Summary): one table with the columns
  *Item*, *Paid*, *Unpaid*.
- Its rows, in this order:
  - each individual discipline in the tournament's discipline order, counting fencers
    holding a seated entry; directly under it a **"<discipline> (fronta)"** row counting
    fencers holding a substitute entry, stated only where somebody is queued;
  - then each extra item the tournament offers, category by category in the band's
    order (goods before programme), items in the tournament's own order. Every offered
    category is summarised, not only rentals, merch and afterparty.
  - An item that takes an option is broken down by its answer ("Triko – XL"): one row
    per declared choice in the organizer's order, zero rows included; free-text answers
    one row per distinct answer; a selection with no answer under "– neuvedeno".
- Items are counted in **pieces** (an order of two shirts counts 2); disciplines in
  fencers. An offered item nobody chose still has its row, at 0 / 0.
- Paid / unpaid is the registration's settled state, exactly as the paid column of every
  other tab reads it. Deleted rows count nowhere.
- The Summary tab carries **no count** in the band, **no position column**, and neither
  the active-only switch nor the seeding order: its columns already split paid from
  unpaid. Its rail card offers only the copy action.
- The Google Sheets export writes the summary as its own worksheet, **Summary**,
  rewritten whole on every export — it holds nothing downstream staff annotate. The
  English tick governs it as it governs every other table.

## Capabilities

### New Capabilities

- `export-summary`: the summary table — which rows it holds, in what order, how each
  row counts, what paid means for it, and how it leaves the screen.

### Modified Capabilities

- `export-tables`: the band ends with the Summary tab; the rules that every tab states a
  count, opens with a position column and offers the active-only switch gain the
  summary as their one exception; its rail card offers the copy alone.
- `data-export`: the Sheets export writes a Summary worksheet besides one per table,
  without a position column, and rewrites it whole instead of merging it.

## Impact

- Backend: a new `app/exportsummary.py` computing the lines from the tournament's
  offer and the replayed rows; `exporttables` gains the `summary` tab kind;
  `sheet._extras_by_category` adds the selection's `item_id` so a selection is joined
  to the item it belongs to rather than by name; `export_api` gains
  `GET /{slug}/export/summary`; `ExportBandTabOut.count` becomes nullable for the
  summary tab; `sheets_export.export_to_sheets` writes the Summary worksheet.
- Frontend: `export/SummaryTable.tsx`, a summary branch in `ExportTables.tsx` and
  `tabs.ts`, `TableOperations` gaining an optional active-only switch, `api.ts` types.
- i18n: `export.tab.summary`, `export.summary.*` (column headers, "fronta",
  "neuvedeno"), Czech and English, frontend and backend catalogs.
- No storage change, no migration. Sits beside the uncommitted `export-sheet-wizard`
  change, which touches `ExportPanel` and `data-export` in other requirements.
