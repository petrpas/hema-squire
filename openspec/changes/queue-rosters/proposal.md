## Why

The Queue phase sits after Export, although it is the one place that changes who holds a
seat — so the export, meant to be the tournament's result, can be taken before the
roster is settled. Its body is a stack of cards listing names without the money that
decides who is demoted, without ratings, and with a line of its own that is not the
line the Export rosters draw. Its actions are offered where the server will refuse them
(return a paid registration, promote into a full discipline) and the refusal comes back
as a raw code. The organizer settles seating, irreversibly, from a count in a dialog,
unable to see which registrations that count is.

## What Changes

- **The Queue phase moves before Export.** The fixed order becomes Setup, Import,
  Fencers, Matching on HR, Deduplication, Payments, **Queue**, Export, Teams. Export is
  what leaves the tournament and comes after everything that changes it.
- **The Queue phase is offered only on an automatic tournament.** A manual tournament
  never creates a substitute placement, so the phase would be a capacity mark with
  nothing to act on. A URL naming it on a manual tournament lands on the default phase.
- **Its body is a band of rosters**, one tab per individual discipline, labelled and
  counted as the Export discipline tabs are, drawing the **same rows in the same order
  with the same line** — the Export rosters' ordering, in the tab's own order (no
  seeding order, no active-only switch: the unpaid are what this phase is about).
- **Row actions are two arrows**: ↑ *posunout na místo* on a queued row, offered only
  while the discipline has a free place; ↓ *vrátit do fronty* on a seated row, offered
  only while the registration is unpaid. A row with no registration behind it carries
  neither and says why. These arrows are the only row actions of the phase.
- **Each roster states the money**: for a seated row, paid, waived, or what is owed and
  by when; for a queued row, its queue moment (from `demotion-hardening`). The rating is
  a column, read-only here; it is corrected on Export.
- **The right rail holds seating**: the seating deadline, whether and when seating
  settled, the free places of the open discipline, and the settle action. Its
  confirmation states how many registrations will be moved and how many of their teams
  will be waitlisted.
- A refused arrow is reported in words, not as the server's code.
- **Export states that it acts on nothing.** No row action is ever offered on an Export
  tab; the rating correction, which changes no seat and no money, stays the one edit.
- The stack-of-cards view is removed.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `etl-console`: the fixed phase order puts Queue between Payments and Export; the Queue
  phase is offered only on an automatic tournament.
- `seating-queue`: the queue view becomes a band of discipline rosters with arrows and a
  money column; the settle action lives in the phase's rail and its confirmation counts
  teams as well as registrations.
- `export-tables`: a requirement that no Export tab offers an action on a row other than
  the rating correction.

## Impact

- Frontend: `Console.PHASES` order and `offeredPhases` (mode); `QueuePanel` replaced by a
  `queue/` directory — the band orchestrator, the roster (reusing `ExportGrid`,
  `rosterOrder`, `tabs`), the arrow cell, the seating rail card; refusal codes mapped to
  i18n; `QueueEntryLine` removed.
- Backend: `GET /{slug}/queue` slims to the seating summary — deadline, settled moment,
  pending demotions, pending team waitlistings, and per discipline capacity, taken and
  free — since the rows come from the discipline export table; `scheduler` gains the
  team count from the same `_demotable` selection.
- i18n: phase rail card, arrow labels and hints, refusal texts, money cell (cs, en).
- Depends on `demotion-hardening` for the queue moment carried on the rows; to be
  implemented and archived after it.
