## Why

The Export phase is one fencer table and three buttons. What actually leaves a
tournament is several different tables read by different people: a check-in desk
wants every fencer with a paid mark, a poolmaster wants one discipline's seeding
order with the capacity line drawn on it, and the person handing out T-shirts
wants only the fencers who bought one. Today each of those is assembled by hand
out of a spreadsheet after the fact, and the seeding order — the one an organizer
routinely corrects, because HEMA Ratings is not always right — cannot be
corrected at all: Squire holds ratings only as fetched snapshots, so a typed
rating has nowhere to live.

## What Changes

- The Export phase gains a tab band above its table. Tabs are derived from the
  tournament: **Fencers**, one tab per individual discipline, and one tab per
  extra-item category the tournament offers (rentals, merch, afterparty,
  seminars, other). A tournament offering no merch shows no merch tab.
- Every tab carries an **all / active only** switch. "Active" means paid — the
  registration's settled state as `payment-ledger` derives it, a live waiver or
  a lane credited to within tolerance, so the switch answers the same question
  whether Squire collected the money or the organizer forgave it — and on an
  item tab it narrows the list to fencers who both ordered the item and paid.
- The **Fencers** tab is the fencer table as it stands: name, nationality, club,
  HR ID, disciplines, paid, in registration order.
- A **discipline** tab is a seeding roster: name, nationality, club, HR ID,
  rating, rank, paid. It sorts by paid then registration order; switched to
  active-only it sorts by rating, highest seed first. A line is drawn at the
  discipline's capacity, and a fencer holding a substitute placement sits below
  it whatever the sort says.
- The **rating** cell becomes editable. A typed rating persists as a rule on
  (row, discipline) replayed over the projection, so it survives a ratings
  refresh, is marked as an organizer edit wherever it shows, and is the rating
  every reader gets — the roster order, the capacity line, and the Sheets export
  alike.
- Refreshing ratings from a discipline tab fetches each fighter's page at most
  once per run whatever the tournament's disciplines, and writes over no rule.
- Every tab offers **copy** — the visible table as TSV, for pasting into a
  spreadsheet — and an **export in English** tick, offered only to an organizer
  whose interface is not already English.
- **BREAKING** The Google Sheets export writes these tables instead of the v1
  worksheet format. `output_sheet_url` keeps its meaning and receives a
  worksheet per tab; the Fencers and per-discipline worksheets change columns,
  and item worksheets appear beside them. The v1 in-tournament tooling stops
  consuming the sheet unchanged. The preserve-and-refresh semantics — `Reg.` and
  `No.` never written, ratings always refreshed, other cells written only when
  blank — carry over to the new worksheets.
- Printing through a Typst template is named in the source note and is **out of
  scope**; it is its own change.

## Capabilities

### New Capabilities
- `export-tables`: the Export phase's derived tab band, each tab's columns,
  filter and sort, the capacity line, the editable rating and its rule, the
  copy-as-TSV action, and the English rendering tick.

### Modified Capabilities
- `data-export`: the Sheets export's format is replaced by the export tables, so
  the v1 worksheet format and its downstream-compatibility requirement go, and
  the rating an organizer typed is what the sheet carries. The canonical JSON
  document is untouched: it exports the rule set generically, so the new rule
  kind round-trips with no version bump.
- `etl-console`: the Export phase stops being a single fencer table and gains a
  tab band of its own, joining Setup, Deduplication, Teams and Queue as a phase
  that replaces the plain table.
- `hr-integration`: a ratings refresh is reachable from a discipline tab, fetches
  a fighter page at most once per run, and never overwrites an organizer's typed
  rating.

## Impact

- Backend: `app/sheets_export.py` (new worksheet shapes), `app/routers/export_api.py`,
  `app/rules.py` (a rating-override rule kind), `app/hr_sync.py` (per-run page
  reuse), `app/sheet.py` where roster rows are projected and where extras are
  currently flattened into the v1 slots.
- Frontend: `src/ExportPanel.tsx` and a new `src/export/` directory holding the
  tab band and one file per table; `src/Console.tsx` where the Export phase's
  columns are declared; `src/api.ts`; Czech and English catalogues.
- Data: a new rule kind; no schema migration and no export-document version bump.
- Downstream: v1 in-tournament tooling reading the exported spreadsheet.
- Depends on `derive-balances-from-credits`. That change is what makes `paid` a
  derivation rather than a stored state, and it leaves `row["paid"]`,
  `row["state"]` and the hand-mark fields named and typed exactly as they are
  today. Nothing here reads a payment column directly, so this change needs the
  vocabulary and not the schema; it can be worked before or after, and its
  wording follows the derived reading either way.
