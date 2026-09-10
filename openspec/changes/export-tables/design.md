## Context

The Export phase today is the fencer table with three columns of its own
(`hr_id`, `disciplines`, `state`) plus a rail panel holding three buttons:
fetch ratings, write the Sheets export, download the canonical JSON. The
Sheets export writes the v1 format — a `Fencers` worksheet and one worksheet
per individual discipline slug — with merge semantics that never touch the
`Reg.` and `No.` columns downstream staff fill by hand, always refresh
`HRating`/`HRank`, and write every other cell only when it is blank.

Three facts about the existing machinery shape everything below.

**Ratings are outside the projection.** `hr_sync.take_snapshot` stores an
`HRRatingSnapshot` of `(hr_id, discipline_code) → rating, rank`, and
`latest_ratings` hands it to the exporter as a side lookup. The console's
projected `Row` — built by `sheet.base_rows`, then `rules.replay`ed — has no
rating in it. So there is nowhere for a typed rating to go, and nothing marks
one as an organizer's.

**Extras are already flattened.** `sheet._extras_summary` splits a
registration's `extra_selections` into exactly the v1 sheet's three slots:
rental names, an afterparty boolean, and everything else as freetext for the
notes column. The item tabs need the selections themselves, per category, with
quantities.

**Seating is on the row.** `base_rows` writes `disciplines` (seated entries)
and `substitute_for` (queued entries) as separate lists, so the capacity line
needs no new query.

**Paid is already a derivation on the row.** Since
`derive-balances-from-credits`, `row["paid"]` is `Registration.settled` — a
live waiver, or the paid lane credited to within tolerance — and `row["state"]`
is `wire_state`, composed from the lifecycle and that derivation. The key names
and their types did not move, so every table below reads the row as it always
did; what changed is that the answer follows the credit journal, and so follows
a reversal at once rather than after somebody remembers to reassign a state.

## Goals / Non-Goals

**Goals:**

- One tab band over the Export phase, derived from what the tournament offers.
- A rating an organizer types is the rating every reader gets, and survives a
  ratings refresh.
- A discipline tab that states the seeding order and where the capacity line
  falls, without the reader reconstructing it from the queue.
- Every table leaves by three routes that agree with each other: on screen,
  through the clipboard, and into the organizer's spreadsheet.

**Non-Goals:**

- Printing. The Typst template is its own change; nothing here anticipates it
  beyond keeping each table's column list in one place.
- Keeping the v1 in-tournament tooling working against the exported
  spreadsheet. The owner has decided the sheet takes the new shape.
- Editing anything but the rating from these tables. Name, nationality and club
  stay editable where `etl-console` already puts them.
- Per-item payment state. A credit is held against a registration, never against
  one of the items it bought; an item tab's paid column is the registration's.

## Decisions

### D1 — The tab band is derived, not declared

Tabs are computed from the tournament: `Fencers`, then one tab per discipline
with `kind == INDIVIDUAL` in the tournament's discipline order, then one tab
per `ExtraCategory` for which the tournament has at least one `ExtraItem`, in
`ITEM_CATEGORIES`-then-`ACTION_CATEGORIES` order.

*Alternative rejected:* hardcoding Afterparty / Rentals / Merch as the source
note names them. Squire has no such concepts — it has six generic categories,
and `frontend/src/extraItems.ts` already carries a compile-time assertion that
every category is placed. Hardcoding three of them would make a tournament that
sells parking or runs a seminar invisible in its own export, and would make the
seventh category someone adds a silent omission rather than a new tab.

A team discipline gets no tab, for the reason `data-export` already gives for
giving it no worksheet: its entries are `Team` rows, not registration entries,
and there is no roster of individuals to seed.

### D2 — Ratings join the projection, and an override is a rule

`sheet.base_rows` seeds each row with `ratings: {slug: rating}` and
`ranks: {slug: rank}`, read from `hr_sync.latest_ratings` by
`(hr_id, taxonomy_code)`. A new rule kind `rating_override`, targeting a row,
carries `{"discipline": slug, "rating": number | null}` and writes into that
map during replay.

This buys three things at once and they are the reason for the choice:

- **The override outlives a refresh** with no special case. A refresh writes a
  new snapshot; the next replay seeds from it and the rule overwrites it again.
  Nothing in `take_snapshot` has to know an override exists, so nothing can
  forget to check.
- **The colour comes free.** `rules.net_changes` already attributes every
  projected cell that differs from its source to the newest contributing rule,
  and the manual-edits rail already renders that. A rating override is one more
  entry in a mechanism the console has.
- **One rating, everywhere.** The sheet exporter is handed replayed rows, so it
  writes the override without being taught about it. The roster order and the
  capacity line read the same field.

The audit field name is `rating:<slug>`, so a fencer entered in two disciplines
has two independently attributable cells.

*Alternative rejected:* a column on `RegistrationDiscipline`, or a second
snapshot flavour holding organizer values. Either makes the "typed value wins"
rule a `COALESCE` that every reader must remember to write, and neither is
reversible the way removing a rule is.

*Scope note:* rank is not editable. The owner chose the rating alone; rank
stays whatever the snapshot said, and an overridden rating is deliberately
allowed to disagree with the rank beside it — the rank is HEMA Ratings'
statement, and the export says so.

### D3 — The capacity line is drawn, not filtered

A discipline tab sorts, then draws one line. Above it are the fencers who hold
a **seated** entry in that discipline (`slug in row["disciplines"]`); below it
are those holding a **substitute** entry (`slug in row["substitute_for"]`),
whatever the sort key says, in queue order — which `seating-queue` fixes as
registration order over live registrations. The line therefore falls after the
seated group, which is at most the discipline's capacity.

Where the tournament's mode never creates substitute placements, there is no
queued group; the line is then drawn at the capacity position in the sort order
and states what would be cut, marking nobody as queued. This is what "podle
způsobu vedení turnaje" means in the source note: the line is always at
capacity, but only an actual queue puts a named fencer below it.

The line is a row in the table with a rule above it, not a section break that
splits the table in two: a copy or a sheet write carries every fencer in one
block, and the line does not survive into TSV. What leaves is the order.

### D4 — The sheet mirrors the tabs, worksheet for worksheet

`sheets_export.export_to_sheets` keeps its merge engine unchanged —
`merge_grid` addresses old cells by their header name, so `Reg.` and `No.`
survive a column-set change without special handling — and changes what it is
given: the `Fencers` worksheet's columns become the Fencers tab's, each
discipline worksheet's become the discipline tab's, and one worksheet per item
category appears, named for the category.

`PRESERVED` and `REFRESHED` are unchanged. `HRating` is still always
refreshed; what refreshes it is now the replayed row, so an override wins there
too and re-exporting never restores a stale fetched value over a typed one.

**BREAKING**, and the owner has taken it: v1 in-tournament tooling reading this
spreadsheet sees changed columns and unfamiliar worksheets. `data-export`'s
downstream-compatibility requirement is removed rather than quietly falsified.

### D5 — The English tick governs what leaves, not what is on screen

The tick renders the **copied TSV and the sheet write** through the `en`
catalogue — column headers and the yes/no values — and leaves the table on
screen in the organizer's own language. It is offered only when that language
is not already English, where it would be a tick that changes nothing.

*Alternative considered:* having it re-render the visible table too, so the
organizer sees what they will get. Rejected because the table is also the place
the organizer works — types a rating, reads the line — and a language switch
that flips the working surface to make a preview is a worse trade than a tick
whose effect is stated in its label.

Rendering happens server-side for the sheet, through `app.i18n.Catalog`, and
client-side for the clipboard, through the `en` resource bundle already loaded
by `react-i18next`. Both read the same key names, so a header exists once per
language and not once per surface.

### D6 — Filter and sort are per tab, and the switch means paid

Each tab holds its own `all / active only` state; moving between tabs does not
carry it, because the tabs answer different questions.

"Active" is the registration's settled state — `row["paid"]`, which
`payment-ledger` derives as a live waiver or a lane credited to within
tolerance, so the switch works whoever handles the money. On an item tab it is
the second half of a conjunction: the tab already lists only fencers holding a
selection in that category, and the switch narrows that to the paid ones.
Deleted rows are in no tab at all, as `etl-console` already requires of every
export.

Two consequences of that derivation are worth naming here, because a check-in
desk reads these tables. A registration that has been credited nothing and
waived by nobody is not active, whatever it owes: a fencer whose entries all sit
in a queue is priced at zero and is still not a fencer who has paid, and the
`credited > 0` term in the derivation is what keeps them off the active roster.
And an organizer who reverses a credited transaction sees the row leave the
active list on the next read, because the column is a sum over live credits and
not a mark somebody has to remember to take back.

Sort per tab: Fencers by registration order; a discipline by paid then
registration order, and by rating descending when active-only, which is the
seeding question; an item tab by paid then registration order.

The paid column is a plain `Ano`/`Ne`. A registration settled short of its
total — inside tolerance, or waived over an outstanding balance — reads `Ano`
here, and the shortfall is stated where it is worked, in the Payments phase. This is a deliberate narrowing of
`tolerance-decides-state-not-display` to a surface whose product is machine-read
downstream, and the change states it as such rather than letting the two rules
silently disagree.

### D7 — Frontend shape

A new `frontend/src/export/` directory: the tab band and the orchestrator, one
file per table kind (`FencersTable`, `RosterTable`, `ItemsTable`), the copy
action, and the shared column-definition module that the three tables and the
TSV builder read. `ExportPanel.tsx` stays in the rail and keeps the JSON
download and the sheet write; the ratings refresh moves to the discipline tabs,
where it is about the ratings a reader is looking at. `Console.tsx` loses the
Export phase's entry in `PHASE_COLUMNS` and gains it to the list of phases that
replace the fencer table, beside Setup, Deduplication, Teams and Queue.

### D8 — One fighter page per refresh run

`take_snapshot` already fetches each `hr_id` once and loops the taxonomy codes
over the parsed result, so tiers of one weapon share a fetch. What the source
note asks for beyond that is that a refresh started from a discipline tab does
not re-fetch a page another discipline's tab fetched moments earlier: the
refresh is per tournament, not per discipline, and the endpoint takes no
discipline. A discipline tab's refresh button runs the tournament's refresh and
says so.

## Risks / Trade-offs

- **The v1 tooling breaks the moment someone re-exports.** → The change is
  stated as BREAKING in the proposal and removes the compatibility requirement
  from `data-export` rather than leaving a spec that says two things. The
  destination is the organizer's own `output_sheet_url`, so the blast radius is
  one spreadsheet per tournament and re-creating the old worksheets by hand is
  possible if a tournament still needs them.
- **`base_rows` gains a query.** Seeding ratings means every projection reads
  the latest snapshot, on every phase, not just Export. → It is one indexed
  read of one snapshot with its ratings eagerly loaded, which `latest_ratings`
  already does for the exporter; the alternative is a rating that some phases
  have and others do not, which is worse to reason about than one extra read.
- **An overridden rating can disagree with the rank beside it.** → Deliberate,
  per D2. The rank column says what HEMA Ratings says; if that is confusing in
  practice, making rank overridable is an additive follow-up, not a rework.
- **A derived tab band can be long.** A tournament with six disciplines and
  three item categories shows ten tabs. → `useTabBand` already keeps the
  selected tab scrolled into view in a `.stage-control-band`, which is the
  mechanism the fencer home and the payments queues use.
- **The capacity line means two things.** With a queue it names who is below
  it; without one it only marks where capacity falls. → The line carries its
  own label saying which of the two it is, so a reader is never left inferring
  it from the tournament's mode.
