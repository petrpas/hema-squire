## Why

The Load phase's `Registered` column drops the clock off a stored instant and
shows the day alone. On a tournament where a discipline fills in the first
hour, the day is not enough: the organizer cannot see the order registrations
arrived in, cannot tell a queue position from the table, and cannot check a
disputed cut-off — even though the backend has always stored the full moment
and the table is already sorted by it.

The organizer's queue view has the same gap, and there it is sharper: the queue
is *ordered by* the registration moment, and the line between a seat and a
place in the queue can fall between two fencers who registered on the same day.
A view that states only the day cannot explain the order it is listing.

## What Changes

- The `Registered` column in the console's fencer table states the day and the
  clock time, not the day alone.
- The queue view's `registered …` line beside each fencer states the same day
  and clock, so the order the queue is listed in is legible from the entries.
- The moment is read in the tournament's own zone, the same frame every other
  date on its timeline is read in, rather than in whatever zone the
  organizer's browser happens to sit in.
- A registration moment that arrives without a zone — the case for imported
  rows, whose `registration_time` is extracted from a spreadsheet — is shown
  as the wall clock it states, unshifted.
- The column keeps the tabular numerals the sheet table already sets, so the
  times line up down the column.
- No backend change: `registered_at` already travels as a full ISO instant.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `etl-console`: the fencer table's registration column gains a stated
  requirement — day plus clock time, read in the tournament's zone, with the
  zone-less imported case fixed.
- `seating-queue`: the queue view already owes each entry "their registration
  time"; the requirement is sharpened to say that a time is a day *and* a
  clock, read in the same zone.

## Impact

- `frontend/src/Console.tsx` — the `registered_at` branch of `CellDisplay`,
  which needs the tournament's zone threaded to it, and the `QueuePanel` call,
  which needs the same.
- `frontend/src/QueuePanel.tsx` — the `registeredAt` line, plus a new
  `timezone` prop; the panel currently takes only a slug.
- `frontend/src/i18n/{cs,en}.json` — the `queue.registeredAt` placeholder,
  which is named `{{date}}` and no longer holds only a date.
- A small shared formatter beside `frontend/src/openingMoment.ts`, so the
  zone-aware rendering is written once.
- Frontend tests covering the formatter and the rendered cell.
- Out of scope: the `expires_at` / `paid_at` columns and the queue view's own
  `seating_deadline` and `settled on` lines, which stay days.
