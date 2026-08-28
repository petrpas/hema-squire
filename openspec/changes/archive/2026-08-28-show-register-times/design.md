## Context

See `proposal.md` — Why. The relevant current state:

- `Console.tsx` renders `registered_at` as
  `new Date(row.registered_at).toLocaleDateString("cs")` — the clock is
  present in the data and thrown away in the cell.
- The backend already sends the whole moment. Rows built from registrations
  (`sheet.base_rows`) send `registered_at.isoformat()` off a
  `DateTime(timezone=True)` column written with `datetime.now(UTC)`, so those
  strings carry an offset. Rows built from imports (`sheet._imported_rows`)
  pass through `record["registration_time"]`, an ISO-shaped string the
  extractor lifts out of a spreadsheet with no zone attached — and an
  unparsed row sends `null`.
- The tournament's zone is already on the wire: `TournamentDetail.timezone`,
  an IANA identifier, which `Console` already fetches into `detail` beside the
  sheet. `openingMoment.ts` establishes the house style for reading an instant
  in that zone (design `add-registration-open-time` D3/D6).
- `.sheet-table td` already sets `font-variant-numeric: tabular-nums`, so the
  alignment the spec asks for needs no new CSS.

## Goals / Non-Goals

**Goals:**

- One pure, unit-tested formatter for "a stored moment as a day and a clock",
  so no second caller re-derives the zone rules.
- Correct handling of the two shapes the column actually receives — an
  offset-bearing instant and a bare local timestamp — without either quietly
  shifting.

**Non-Goals:**

- Any backend change; no new field, no serialization change.
- Making the same move on `expires_at`, `paid_at`, or the queue view's
  `seating_deadline` and `settled on` lines — all read as days, not moments.
- Seconds, relative times ("2 hours ago"), or a zone label in the cell.
- A user-facing zone preference. The tournament's zone is the frame.

## Decisions

### D1 — Day and clock in one cell, not a second column

The cell states the day and then the 24-hour clock to the minute
(`14. 3. 2026 15:32`). A separate `Time` column was considered and rejected:
it doubles the column's width in a table that already carries eight columns in
the Load phase, and it separates two halves of one fact that are always read
together. Seconds are excluded — they are noise at the resolution an organizer
reasons about, and the ordering question they would settle is already answered
by the table's sort.

### D2 — Read in the tournament's zone, not the browser's

The moment is formatted with `Intl`'s `timeZone` option set to
`detail.timezone`. Every other date on a tournament's timeline is read in that
zone, and the console is a shared surface: an organizer travelling, or a
co-organizer abroad, must read a registration as the same clock time the
tournament itself does. The browser's zone is the fallback, used only in the
two cases where the tournament's is unavailable: before `detail` has arrived
(the sheet and the detail are fetched independently, and the sheet can render
first), and when `Intl` rejects the identifier. Both fall back silently — a
cell that renders a slightly differently-framed time beats a cell that throws.

### D3 — A zone-less moment is spelled out, never resolved

A string is treated as an instant only when it carries a zone: a trailing `Z`
or a `±HH:MM` offset. Anything else — the imported case — is not passed
through `Date` at all. Its date and time parts are read off the string and
re-spelled in the display shape.

The alternative, assuming the imported timestamp is in the tournament's zone
(or the browser's, which is what `new Date()` does today), was rejected: the
import never stated a zone, so any assumption invents a fact, and the shift it
introduces is invisible in the cell and wrong across a DST boundary. Spelling
the stated clock back out is the only reading that cannot be wrong about
something the data does not say.

### D4 — A pure module beside `openingMoment.ts`

The formatter lands in a new `frontend/src/momentText.ts` as a pure function
taking `(value: string | null, timezone: string | null)` and returning the
display string, mirroring how `openingMoment.ts` keeps its clock logic pure
and testable away from React. `Console.tsx` is already long; the parsing branch
does not belong inline in `CellDisplay`.

Formatting follows the existing precedent exactly: `toLocaleDateString("cs")`
for the day, and `toLocaleTimeString("sv-SE", { hour: "2-digit", minute:
"2-digit" })` for the clock — `sv-SE` used only for its plain 24-hour `HH:MM`
shape, as `openingHourIn` already does.

### D5 — The zone reaches both views as a prop

`CellDisplay` and `QueuePanel` each take a `timezone: string | null` prop,
threaded from `Console`'s `detail` — `QueuePanel` is rendered by `Console`, so
the value is already in hand at both call sites. No context, no module-level
store: the console renders one tournament, the value is one string, and a prop
keeps both a pure function of their inputs, which is what makes them testable.

Adding `timezone` to the `Queue` payload was considered and rejected: it would
be a backend change to hand the panel a fact its parent already holds, and it
would put the tournament's zone on two wires that could disagree.

### D7 — The queue's i18n placeholder is renamed

`queue.registeredAt` reads `registered {{date}}` / `registrace {{date}}`. The
placeholder becomes `{{moment}}` in both locale files. Passing a day and a
clock into a variable named `date` is the kind of small lie that survives for
years and misleads the next translator; the visible strings are unchanged.

### D6 — An unreadable value falls back to itself

If a value carries no zone and cannot be split into a date and a time, the
cell shows the raw string rather than `Invalid Date` or an em dash. The em dash
means "nothing was recorded"; a garbled import timestamp is something recorded,
and showing it is what lets the organizer recognise the bad import. Only `null`
gets the em dash.

## Risks / Trade-offs

- **The queue's entry line grows by five characters inside a `muted` span that
  already carries the club** → the line already wraps rather than overflowing;
  the clock is the fact the list is ordered by, so it earns the width.
- **The Load phase's row gets wider, and can push the table to scroll on a
  narrow screen** → the added text is five characters in a table whose Name
  and Club columns already dominate; the table already scrolls horizontally
  rather than reflowing.
- **Falling back to the browser zone before `detail` arrives means a cell can
  render one time and then re-render at another** → the two fetches are issued
  together and the window is one paint; the alternative (holding the column
  blank until `detail` lands) makes the common case worse to protect a case
  nobody sees.
- **Reading imported timestamps literally means two rows in one table can be
  framed in different zones, without saying so** → they already are, invisibly;
  this change stops making it worse by not shifting a value it cannot place.
  The stated clock is what the import file itself says.
- **An unknown IANA identifier makes `Intl` throw** → every call is guarded,
  falling back to the browser zone, as `openingHourIn` already does.

## Migration Plan

None — a display change on data already sent. It ships and reverts with the
frontend build.
