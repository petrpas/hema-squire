## Context

The Export phase is a band of tables built in `app/exporttables.py`: a tab list
derived from the tournament, and `table_rows` narrowing the replayed fencer table
(`sheet.base_rows` + `rules.replay`) to each tab. Every row already carries what a
summary needs:

- `disciplines` — slugs of the seated entries; `substitute_for` — slugs of the queued;
- `paid` — `Registration.settled`, the ledger's derived state;
- `extras` — per category, a list of `{name, qty, option}` selections
  (`sheet._extras_by_category`);
- `_deleted` — set on a row a deletion took out.

The offer comes from the tournament: `individual_disciplines`, `offered_categories`,
and `tournament.extra_items` with `option_label` / `option_choices`.

Owner decisions (2026-09-24): the summary is the band's last tab; goods count in
pieces; every offered category is summarised; every item with an option breaks down
by its answer, declared choices listed even at zero; the queue row appears only where
somebody waits; the Sheets export writes it as its own worksheet.

## Goals / Non-Goals

**Goals:**
- One table answering "how many of each, paid and unpaid" for everything the
  tournament offers, identical on screen, on the clipboard and in the spreadsheet.
- Counting lives in one backend function, read by the console and the Sheets export.

**Non-Goals:**
- Money. The summary counts; amounts owed and collected stay in Payments.
- Per-item payment. Settlement is a property of the registration (`payment-ledger`);
  nothing here apportions a partial payment across its items.
- Team disciplines, for the reason they have no tab.
- A totals row, a filter, or a sort control.

## Decisions

### D1. A separate endpoint returning structured lines, not pre-rendered labels

`GET /{slug}/export/summary` returns `lines: [{kind, category, name, option, missing,
item_id, paid, unpaid}]`. `kind` is `discipline`, `queue` or `item`. `option` is the
answer string, or `null` for "no option", with a distinct `missing: true` for a
selection that should have answered but did not. `item_id` is null on a
discipline's lines, and is carried so that two items sharing a name stay two lines
to a reader keying them.

The console composes the label (`LSM (fronta)`, `Triko – XL`, `Triko – neuvedeno`)
through i18n, so the English tick renders the copy in English with
`i18n.getFixedT("en")` exactly as the other tables' copy does. The Sheets writer
composes the same label through `app.i18n.catalog` in the export's locale.

*Alternative:* reusing `GET /export/table?kind=summary` with `rows: list[dict]`.
Rejected. Those rows are fencer rows, which the console orders, filters and numbers.
A summary line is none of that, and putting it through the same shape would invite
the active-only switch to filter it.

### D2. `exportsummary.summary_lines(tournament, rows)` is the one computation

It is a pure function over the tournament's offer and the replayed rows, with deleted
rows dropped first:

1. For each individual discipline in order: a `discipline` line counting live rows
   whose `disciplines` holds the slug, split on `paid`. Then, if any live row's
   `substitute_for` holds the slug, a `queue` line counted the same way. Manual mode
   creates no substitute entries, so the queue line never appears there without a
   mode check.
2. For each offered category in `_CATEGORY_ORDER`, then each of its items in
   `tournament.extra_items` order (id order, which is creation order and the order
   Setup lists them): sum `qty` over selections of that item, split on the row's
   `paid`.
   - An item with no `option_label` gives one line and ignores any stale answer on a
     selection.
   - An item with `option_choices` gives one line per declared choice in declared
     order, zero lines included. A stored answer outside the choices (the choices
     were edited after it was given) gives a line after the declared ones. A missing
     answer gives a `missing` line, stated only where it counts something.
   - An item with a free-text option gives one line per distinct answer. Answers are
     grouped trimmed and case-folded, and the line shows the first spelling in
     registration order. Lines are ordered by that first appearance, then the
     `missing` line. Where nobody chose the item, one bare line at 0 / 0 keeps it
     visible.

A selection is joined to its item by `item_id`, which `_extras_by_category` now adds.
Joining by name would merge two items that share a name, which Setup does not forbid.

### D3. The summary is a tab kind with no count

`exporttables.tabs` appends `Tab(kind=SUMMARY, key="", label=SUMMARY)` as the last
tab, always, including on a tournament offering nothing but disciplines.
`ExportBandTabOut.count` becomes `int | None`, and the band endpoint sends `None` for
the summary. `tabs.ts:tabCount` renders nothing for `null`. `find_tab` recognises the
summary so the band and the table fetch share one tab list.

*Alternative:* `count = number of lines`. Rejected. A line count is not a population,
and the band's numbers compare populations.

### D4. Rail card: the copy alone

`TableOperations` takes `active` as optional in the same way it already takes
`seeded`. The summary passes neither, and no ratings refresh. The copy writes TSV
with the header `Item, Paid, Unpaid` (localised), no position column, the numbers as
digits. The shared `active` state is left untouched, so returning to another tab
finds the switch as it was.

### D5. Sheets: a `Summary` worksheet, written whole

`export_to_sheets` handles the summary tab by writing `[header, *lines]` directly,
without `merge_grid`. The worksheet is named `Summary` in every locale, like the
other worksheet names, because a worksheet name is an address. The Paid and Unpaid
columns are written as numbers. Nothing merges, because the table has no identities
to merge by and nothing a person annotates. The spec states this as a narrowing of
the preservation semantics. The result's `worksheets` list includes `Summary`.

## Risks / Trade-offs

- [A partly paid registration makes all its items unpaid] → The summary means the
  same as the paid column everywhere else, and the proposal says so. Per-item
  settlement would need a ledger change outside this change.
- [Free-text answers fragment ("xl", "XL ", "X-L")] → Case and whitespace are
  folded. Spelling variants remain separate rows, which is honest. The organizer who
  wants clean rows declares choices.
- [Staff annotations typed into the Summary worksheet are lost on re-export] →
  Stated in the spec as intended. The worksheet is a report, not a working list.
- [The uncommitted `export-sheet-wizard` change also edits `data-export` and
  `ExportPanel`] → This change touches different requirements and leaves
  `ExportPanel` alone. Whichever change archives second rebases its delta on the
  synced spec.

## Migration Plan

No storage change. `item_id` joins the row's `extras` selections additively. Old
readers ignore it, and the canonical JSON export does not read `extras` from rows.
Rollback is a revert.

## Open Questions

None. The owner answered all six on 2026-09-24.
