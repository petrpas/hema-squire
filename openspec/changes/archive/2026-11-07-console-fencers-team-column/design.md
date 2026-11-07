## Context

See proposal.md — Why. What shapes the approach:

- **A team belongs to a registration, not to a person.** `Team` carries
  `registration_id` and `discipline_id`; `TeamMember` is a roster name local to
  that team and deliberately not a `Fencer` (`team-disciplines` D4). So the only
  team fact a fencer-list row can state is *which teams this row entered* — one
  registration may carry several, in one discipline or several (`team-disciplines`
  D1/D9). There is no join from a row to "the team this person fights in", and the
  column must not pretend otherwise.
- **The console sheet is one flat table with no discipline filter.** Unlike the
  public entrants band, the Fencers phase has no per-discipline tab, so a cell
  holding two teams has to disambiguate them itself.
- **`etl-console` fixes that a phase's columns are a property of the phase**:
  "Where a phase's contents follow a tournament's settings, it SHALL be the phase
  that branches, not its column table." The existing precedent is
  `BONED_PAYMENTS_COLUMNS` — a second declared list, not a condition inside one.
- Column assembly today is `[...BASE_COLUMNS, ...(boned ? BONED_PAYMENTS_COLUMNS
  : PHASE_COLUMNS[phase])]` in `Console.tsx`, with `BASE_COLUMNS = ["name",
  "nationality", "club"]`. `SheetArea` renders whatever list it is handed and
  marks a column `col-phase` when `PHASE_COLUMNS[phase]` contains it.

## Goals / Non-Goals

**Goals:**

- The team stands where the column order puts it — after Club, inside the identity
  group — without `BASE_COLUMNS` becoming conditional at its call site.
- The cell is a stated fact from the server, not a client-side join.
- A reader of two teams in one cell can tell which discipline each belongs to.

**Non-Goals:**

- No team data on any other phase, on Export, on the roster print, or in the
  public entrants rosters.
- No editing, no action on a team from the fencer list. Admission from the
  waitlist stays the Queue phase's, roster editing stays the entrant's.
- No deduplication or grouping of same-named teams — `team-disciplines` D9 already
  settles that nothing deduplicates teams by name.
- No new way to reach a team's roster from the row (no link, no expander).

## Decisions

**D1 — The cell is `name (discipline-slug)` where the disambiguator earns its
place, `name` alone where it does not; one team per line.**
The name leads because it is what the organizer is looking for; the slug follows
in parentheses as the disambiguator — but only on a tournament with more than one
team discipline. On a tournament with one, every team is in it and the slug
repeats down the whole column without telling the reader anything (owner
decision, 2026-11-07). The slug rather than the discipline's full name, because
the Disciplines column one cell to the right already speaks in slugs, and two
vocabularies for the same thing in one row would read as two different facts. One
team per line rather than comma-joined: a comma-joined list of `name (slug)` pairs
is hard to parse at a glance, and the cell is read for membership, not scanned for
length. *Alternatives:* always bare names — rejected, ambiguous across
disciplines, which is the thing that prompted this change; always the slug —
rejected as above; one column per team discipline — rejected, it makes the column
table a function of the tournament's configuration, which the spec forbids.

The count is asked of the tournament, not of the row: a row holding one team on a
two-discipline tournament still names it, so one row's cell does not follow a
different rule from the next. `teamsNeedTheirDiscipline(disciplines)` answers it
once in `Console.tsx` and reaches the cell as a prop, the way `hrIdentity`
already does — a cell is a function of what it draws.

**D2 — A second declared column set for the Fencers phase, not a conditional
`BASE_COLUMNS`.** `Console.tsx` gains `FENCERS_TEAM_COLUMNS` (or a small
`baseColumns(phase, mode)` returning the complete identity group for the phase) so
that the team column is declared as part of a named set, exactly as
`BONED_PAYMENTS_COLUMNS` is. The call site branches once; no list is built by
splicing into the middle of another. *Alternative:* `BASE_COLUMNS.toSpliced(3, 0,
"team")` at the call site — rejected: the position of Club would then be
load-bearing and silently wrong if `BASE_COLUMNS` ever gains a column.

**D3 — The column is not `col-phase`.** `col-phase` marks the columns the phase's
operation acts on. The team is read-only context in the identity group, so it
takes no phase marking and stays out of `PHASE_COLUMNS.fencers`, which also keeps
`editableHere` and the field-edit rule machinery away from it for free (the
column is simply never in `EDITABLE_COLUMNS`).

**D4 — The server states the teams on the row.** `sheet.base_rows` adds, for a
registration row, `teams: [{name, discipline}]` ordered by entry (`id`), reading
`registration.teams` — which `Team.registration` already back-populates. Imported,
unparsed and manual rows get `[]`, since no team can be entered on a row that is
not a registration. The slug comes from `team.discipline.slug`, the same source
the `disciplines` field uses. *Alternative:* a separate console endpoint joined in
the client — rejected: the sheet is already the one answer the table is built
from, and a second request would make the column arrive after the row it belongs
to.

**D5 — Offered when the feature is on and a team discipline exists.** The client
decides from the detail it already has:
`(detail ?? tournament).feature_teams && (detail?.disciplines ?? []).some(d => d.kind === "team")`
— the same idiom as `offeredSlugs`, which already filters disciplines by kind. Not
"the sheet has a row with a team": an empty column on a tournament that has the
discipline is information (nobody has entered a team yet), while a column that
appears when the first team is entered would make the table's shape depend on its
contents.

**D6 — Czech label "Tým", English "Team"**, under the existing `column.*` namespace
in both locale files, beside `column.club`.

## Risks / Trade-offs

- **The column appears a beat after the table on first paint** (it depends on the
  detail, which arrives on its own request) → the same already holds for the money
  columns' currency and for the timezone; the table does not reflow its rows, only
  gains a column, and the alternative is withholding the whole table until the
  detail lands.
- **A tall cell makes a tall row** where a row entered three teams → rows in this
  table are already variable-height (markers, the balance cell, the substituted
  marker); three teams on one registration is the far tail.
- **A team named the same in two disciplines reads as two near-identical lines** →
  that is the truth about the data, and the slug is exactly what separates them.
- **Adding a second team discipline to a tournament changes every team cell**,
  since the slug appears once there is something to disambiguate → the column
  states more, never less, and the change is in the same direction as the
  organizer's own: they have just made the tournament ambiguous.
- **The column says "entered", not "plays for"** — an organizer may read a dash on
  a fencer who is on someone else's roster and conclude they are in no team →
  mitigated only by the column's label and position (it sits in the identity
  group, beside the club the fencer registered under). Stating roster membership
  would require an identity the data model deliberately does not keep.

## Migration Plan

None. The field is derived from `teams` rows that already exist; no schema change,
no backfill. Rollback is the revert.
