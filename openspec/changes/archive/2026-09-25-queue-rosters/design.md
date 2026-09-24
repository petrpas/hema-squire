## Context

`QueuePanel.tsx` is a self-contained screen: it reads `GET /{slug}/queue` (seated and
queued lists per individual discipline, built from `RESERVED` registrations ordered by
`registered_at`), draws a card per discipline, and calls `admitSubstitute`,
`returnToQueue` and `settleSeating`. It has no rail of its own and reports refusals as
`String(err.detail)`.

The Export band (`export/ExportTables.tsx`) already draws one roster per individual
discipline from `api.exportTable(slug, "discipline", key)`, ordered and lined by
`export/ordering.rosterOrder`, through `ExportGrid`. Its rows (`SheetRow`) carry
`registration_id`, `paid`, `settled_by_hand`, `outstanding_amount`, `expires_at` and —
after `demotion-hardening` — each queued placement's moment. The band's tabs come from
`api.exportTabs`, with capacity, counts and the line kind.

Phase order and offering live in `Console.PHASES` and `offeredPhases`; the rail is handed
to a phase through `renderRail`.

Owner decisions (2026-09-24): Export read-only; Queue before Export; rosters with ↑/↓ as
the only row actions; settle in the right rail; Queue hidden on manual tournaments; no
active-only switch; rating as a column.

## Goals / Non-Goals

**Goals:**
- One ordering and one line, shared with Export by construction.
- Arrows only where the server would act; refusals in words.
- The organizer sees the money on the rows that settlement will move, and the count of
  teams it will move with them.

**Non-Goals:**
- Any change to what promotion, return or settlement do (`demotion-hardening`,
  `paying-substitutes`).
- Team rosters or team arrows (`team-queue`, undecided).
- Rating correction on this phase; it stays on Export.

## Decisions

### D1. Rows from the export table, summary from `/queue`

The Queue roster reads the same discipline table Export reads and orders it with the same
`rosterOrder(rows, slug, capacity, "queue", seeded=false)`. That is what makes "the same
line as Export" hold by construction rather than by two queries kept alike.

`GET /{slug}/queue` keeps what the rows do not carry: seating deadline, settled moment,
pending demotions, pending team waitlistings, and per discipline `capacity`, `taken`,
`free`. Its `seated`/`queued` lists are removed along with `QueueEntryOut`, and so is the
`RESERVED`-only listing that disagreed with `live_registration()`.

*Alternative:* extend `/queue` to return full rows. Rejected: it would be a second
projection of the same fencers, with its own name, club and rating, drifting from the
sheet's replayed corrections.

### D2. Arrow availability is computed on the client from row and summary

- ↑ on a queued row: `row.registration_id !== null` and `free > 0` for the open
  discipline.
- ↓ on a seated row: `row.registration_id !== null` and `!row.paid`.

These mirror the server's refusals (`discipline_full`, `registration_paid_cancel_instead`)
and the server stays the authority. A refusal that still happens (a race) maps its code
through `queue.refused.<code>` with a generic fallback naming the action.

### D3. Components under `frontend/src/queue/`

Per the frontend convention (thin orchestrator, a file per section):
- `QueuePhase.tsx` — band of discipline tabs (reusing `useTabBand`, `tabLabel`,
  `tabCount`), loads rows and summary, owns `act()`, hands the rail card to `renderRail`.
- `QueueRoster.tsx` — `ExportGrid` with the Queue column set and a `cell` renderer.
- `queueColumns.ts` — position, name, club, rating (read-only), money-or-moment, action.
- `ArrowCell.tsx` — the ↑/↓ buttons, outline icons, with hints.
- `SeatingCard.tsx` — deadline, settled state, open discipline's free places, settle
  action and its `Modal` confirmation.

`ExportGrid` already takes a `cell` override; the action column is a column of the Queue
set only, so Export's column set, copy and Sheets write are untouched.

### D4. Team count from the same selection

`scheduler.pending_demotions` becomes a small result of the `_demotable` selection:
registrations, and seated teams among them. Counting teams from anything else would let
the confirmation and the settlement disagree, which `seating-queue` forbids.

### D5. Phase offering by mode

`offeredPhases(mode)` gains `registrations_kept_by` and drops `queue` for `"organizer"`.
The console's existing rule — an unoffered phase's URL lands on the default phase —
covers the stale bookmark.

### D6. After an action

`act()` re-reads the open table, the tabs (counts) and `/queue` (free places), and calls
the console's `onChanged`, which bumps the payment queues' reload, as a money change
anywhere does.

### D7. The sheet states instants with their zone (found in implementation)

The rows now carry the queue moment the roster states, and the sheet emitted every
instant as `isoformat()` of what SQLite hands back — without a zone. `momentText`
reads a zone-less stamp as an imported wall clock and shows it unshifted, so a UTC
moment would have been stated as the tournament's local time. `sheet._instant` stamps
UTC on `registered_at`, `expires_at` and each `queued_since` before they leave, which
also puts the fencer table's registration column in the tournament's zone, as
`etl-console` always said it was.

## Risks / Trade-offs

- [Both this change and `demotion-hardening` modify `seating-queue`'s queue view] → this
  change's delta is written over `demotion-hardening`'s text and must be archived after
  it; tasks start by confirming that change is archived.
- [Rows without a registration on an automatic tournament until `manual-entry-registers`
  lands] → drawn without arrows, stating they hold no seat yet.
- [The `/queue` response shape changes] → only `QueuePanel` reads it, and it is replaced
  in the same change.
- [An organizer used to Export-then-Queue order] → the tab strip is the whole navigation
  and the phase keeps its URL segment.

## Migration Plan

No storage change. Deploy is the frontend and the slimmed endpoint together.

## Open Questions

None.
