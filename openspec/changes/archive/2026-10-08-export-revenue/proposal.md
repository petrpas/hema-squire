## Why

The organizer has no place where Squire states what the tournament brings in.
The Summary tab counts pieces, but leaves out prices. The Payments console lists
payments one at a time. Neither answers "how much has entry brought in, how much
the rentals, how much is still to come, and does it agree with the account". The
organizer currently answers that by hand in a spreadsheet, from the same data
Squire already holds.

## What Changes

- A new **Revenue** tab (`Příjmy`) is added to the Export band, after Summary.
  It holds one block per group:
  - entry fees, one row per individual discipline and one per team discipline;
  - one block per offered extra-item category.

  Each row states:
  - the unit price;
  - the count, as paid / all;
  - the amount paid;
  - the amount still to pay.

  A row stands for one unit price. An item sold at two prices, such as an early
  bird and a regular price, has two rows.
- A **discount** stands in the block of each category it deducted from. It is
  written as a negative row: what it took off the paid and the unpaid side, and
  how many registrations it applied to.
- **Block totals.** Each block ends with a total. Its amounts are net of the
  block's discounts. Its count is the registrations holding something in the
  block, as paid / all. A grand total follows the last block.
- **Paid** is the registration's settled state, the same reading as Summary and
  as the paid column of every tab. A partial payment or a deposit is not spread
  across items. Instead a closing **reconciliation** block sets the paid figure
  beside the money the payment journal actually holds and names the
  difference:
  - waived registrations;
  - deposits and partial payments on registrations not yet settled;
  - payments held in the queue;
  - money on cancelled or expired registrations;
  - the remainder, which covers tolerance, overpayment, rounding and prices
    edited after issue.
- **Waived** registrations are counted in neither paid nor still to pay. The
  reconciliation states how many there are and what their selections are worth.
- **Prices are in the local currency.** A registration settled in EUR is valued
  at its local price, and the reconciliation states received EUR in EUR.
- **What leaves.** The tab leaves by the clipboard. It is written to Sheets
  as a `Revenue` worksheet, rewritten whole on every export like `Summary`, but
  only when the organizer ticks **Zahrnout finance** (`Include finances`). The
  tick sits under the English tick in the export card and is off by default. An
  export without the tick does not touch a `Revenue` worksheet left by an
  earlier export; the owner chose to leave it rather than delete it. The English
  tick renders Squire's own words in English.
- **Not counted.** Queued placements owe nothing and have no row. A row without
  a registration behind it (not yet issued) has no price. The reconciliation
  states how many such rows there are.

## Capabilities

### New Capabilities
- `export-revenue`: the Revenue tab. Covers which blocks and rows it holds, how a
  row is priced and counted, where a discount stands and how it reads, the block
  and grand totals, the reconciliation against the payment journal, and how the
  table leaves.

### Modified Capabilities
- `export-tables`: the band ends with Summary and then Revenue. Revenue, like
  Summary, states no count, has no position column, and offers no active-only
  switch. Its rail card offers the copy alone. The export card gains the
  finances tick under the English tick.
- `data-export`: the Sheets export writes a `Revenue` worksheet only when the
  finances tick is on. It is then rewritten whole and its money is written as
  numbers. Without the tick, no `Revenue` worksheet is written or touched.

## Impact

- Backend:
  - a new `app/exportrevenue.py` computes the table from the replayed rows and
    the registrations behind them;
  - `pricing.py` gains a per-category breakdown of each discount's deduction.
    Today it reports one figure per discount;
  - `exporttables.tabs` gains the new tab;
  - `sheets_export` gains a `Revenue` worksheet;
  - `routers/export_api.py` gains `GET /export/revenue`;
  - new locale keys, backend and frontend.
- Frontend: a `RevenueTable` beside `SummaryTable`, built on the same
  fixed-width, table-per-group layout. Its rows add a price column and money
  columns.
- The tab only reads. No seat, total or credit is written. The export-tables
  rule that Export acts on no seat and no money still holds.
- Visibility: the tab is part of Export, so whoever can open the console can see
  it. The Sheets workbook is shared with downstream staff, so money reaches it
  only by an explicit tick, off by default, on each export.
- API: `POST /export/sheet` gains `finances: bool = False` beside `english`.
