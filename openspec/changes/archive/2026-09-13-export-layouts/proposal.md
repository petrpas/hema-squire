## Why

The Export phase is used at the check-in desk and when seeding, and its layout makes the organizer work to read it. The tab band's frame runs across the whole table width with nothing in it. A tab does not say how many fencers it holds, so seeing whether Sabre Open is full means opening it and counting. The controls sit in a strip above the table, while every other phase keeps its operations in the right-hand rail. The Czech label for the rental category, "Půjčovna", names a shop rather than the things lent.

## What Changes

- The tab band is as wide as its tabs and ends at the last one. Below 768px it stays the full-width scrolling band it is now.
- Every tab states how many rows it holds:
  - a discipline tab states its seated fencers and its queue, as `SABRE OPEN 24 + 3`, and leaves out `+ 0`;
  - the Fencers tab and each item-category tab state a single count.
  - The counts are of the whole tab. The tab's own active-only switch does not change them.
- The strip of controls above the table is removed, and its controls move to the phase's operations rail:
  - a card headed by the open tab's name holds the active-only switch, the copy action and, on a discipline tab, the HR ratings refresh;
  - the English tick joins the Export card beside the spreadsheet write and the JSON download, since it governs what leaves by either route.
- The Czech label of the rental category becomes "Zápůjčky". The English "Rentals" is unchanged.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `export-tables`: the band fits its tabs and every tab states its count; a tab's controls are offered in the operations rail rather than above the table.

## Impact

- **Backend:** `GET /api/tournaments/{slug}/export/tables` adds `count` and `queued` to each tab, computed from the replayed rows by the narrowing `exporttables.table_rows` already applies. The spreadsheet export, which reads `exporttables.tabs`, is unchanged.
- **Frontend:**
  - `export/ExportTables.tsx` loses its control strip and renders its card into the rail;
  - a new `export/TableOperations.tsx` holds the tab card;
  - `ExportPanel.tsx` gains the English tick;
  - `Console.tsx` builds the rail so the Export phase can supply its card;
  - `index.css` gets the band's width and loses `.export-controls`;
  - `i18n/cs.json` gets the new label.
- **Tests:**
  - `backend/tests/test_export_tables.py` covers the counts;
  - `frontend/src/export/exportTables.test.tsx` covers the tab label and where the controls are placed.
