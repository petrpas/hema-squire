## Context

`GET /api/tournaments/{slug}/participants` (`routers/registrations.py`) answers the
spec's public participant list. It reads live registrations directly, one flat list
in registration order, and nothing in the frontend calls it. The console's Export
discipline tabs and the printed roster read something else: `sheet.base_rows` →
`rules.replay` → `exporttables.table_rows`, which applies the organizer's corrections,
deletions and rating overrides, puts HEMA Ratings' nationality and club over the
fencer's, and carries `disciplines`, `substitute_for`, `conditional`, `queued_since`,
`ranks` and `paid` on each row.

The owner's decisions (explore session 2026-10-11) fix the public behaviour: rosters
per discipline on a detail-page tab, columns as the print, unpaid always shown, queue
public in automatic mode only, no line in manual mode, an empty Paid cell on queued
rows, teams with their members, held tournaments without a queue, the print left as
it is, and the hidden/greyed setting removed.

## Goals / Non-Goals

**Goals:**
- One public answer per tournament carrying every discipline's roster, already
  decided: what is listed, in what order, what each Paid cell says and what is
  faded. The client renders it and does not re-derive the rules from the mode.
- The public roster and the printed roster agree on names, clubs and the order of
  the seated rows.
- A roster can be linked to.

**Non-Goals:**
- Results. They will replace held tournaments' rosters later.
- Any change to the Export tables, the console's Queue phase or `roster-print`.
- A seeding order on the public roster.
- Caching or pagination (see Risks).

## Decisions

### D1. Rows come from the replayed Export rows, not from registrations

The individual roster is `exporttables.table_rows(replayed, discipline tab)`,
restricted to rows whose `registration_id` is in the set of live registration ids
(one query on `availability.live_registration()`).

*Why:* the owner keeps the Paid column on the printed roster, and that image is what
circulates. A public page reading raw registrations would show "Jan Novak" where the
image shows "Jan Novák", list a row the organizer deleted as a duplicate, and give a
different club. The replay is already the organizer's truth.

*Restriction:* the replay also holds imported rows not yet issued (`state` imported or
manual) and expired registrations, which the organizer sees and the public must not.
Filtering on live registration ids removes both with the predicate that counts seats,
so a reservation whose window passed before the scheduler swept it drops off exactly
when its seat frees.

*Alternative:* extend today's registration-based query with HR data. Rejected because
it would leave two projections of the same fencer that can disagree.

### D2. Queue numbers are queue positions, from `QUEUE_ORDER`

A queued row's number is computed as `queue_position` computes it: by counting live
substitute placements ahead in `QUEUE_ORDER`. It is done in one ordered query per
discipline rather than one count per row. It is not the row's index among the queued
rows the replay shows.

*Why:* the spec requires the number to equal what the fencer reads on their own
registration. If the organizer deleted a live queued row from the table, the index and
the position would differ. The position is the fencer's truth, so the public list can
show a gap, never a different number.

### D3. Teams are read from `Team` and `TeamMember`

Team disciplines have no Export tab, so there is no replay to reuse. Teams are read
from the model, restricted to live entering registrations. Seated teams come in entry
order (`waitlisted_since, id`) and waitlisted ones in waitlist order, numbered by
`team_waitlist_position`'s ordering. Members come in `ordinal` order. A seated team's
Paid cell is its entering registration's `settled`, under the same mode rules as a
fencer.

### D4. One endpoint, all rosters, decisions made on the server

`GET /api/tournaments/{slug}/entrants` replaces `/participants`:

```
EntrantsOut
  as_of: datetime | null            # organizer-kept roster only (unchanged rule)
  rosters: [RosterOut]              # tournament discipline order
RosterOut
  slug, name, kind: individual|team
  line: bool                        # draw the capacity line (automatic mode, not held)
  seated: [EntrantRowOut | TeamRowOut]
  queued: [EntrantRowOut | TeamRowOut]   # empty unless `line`
EntrantRowOut
  number, name, nationality, club, hr_id,
  paid: "yes" | "no" | null, faded: bool, conditional: bool
TeamRowOut
  number, name, paid, faded, members: [{name, nationality, club, hr_id}]
```

*Why one request:* the tab would fetch again on every discipline switch otherwise,
and a tournament's whole entrant list is
tens to a few hundred rows.

*Why the server decides `paid`/`faded`:* the mode rules (collects, does not collect,
queued) are a spec rule, not presentation. Sending raw `settled` plus the mode would
make every client restate them, and would put `settled` for queued rows on the wire,
where the spec says it means nothing.

### D5. Publication and cancellation answer not-found

The check `fencer_tournament_detail` makes inline (`published_at is None or
cancelled_at is not None` → 404 `tournament_not_found`) is lifted into one helper used
by both endpoints, so the two public reads cannot drift. `/availability` keeps its
current behaviour, which is out of scope.

### D6. "Held" uses the public list's boundary

`tournament.date < datetime.now(UTC).date()`, the split `_published_tournaments` uses
(`day-boundaries`: UTC for the public listing). A tournament moves from the Open list
to the Past list at the same moment its queue disappears.

### D7. The Entrants tab is routed, the other tabs are not

`routes.ts` gains `entrants(slug, discipline?)`. `App.tsx` maps
`t/:slug/entrants` and `t/:slug/entrants/:discipline` to the same `TournamentDetail`
element. The detail derives "Entrants is selected" from the matched route and keeps
its existing local state for the other tabs. Selecting Entrants or a discipline is a
`<Link>`. Selecting any other tab while on an entrants address navigates to
`detail(slug)` with `replace`, so Back does not toggle between tabs.

An unknown discipline slug renders `NotFound`, once the entrants have loaded and the
slug is known to be absent.

*Alternative:* carry the tab in `?tab=`, as the home page does. Rejected because a
discipline then needs a second parameter, and a path reads better when shared.

### D8. Frontend files

Following the panel convention, the code goes in `frontend/src/entrants/`:
`EntrantsTab.tsx` (fetch, `as_of` line, band via `useTabBand`), `IndividualRoster.tsx`,
`TeamRoster.tsx`. The faded row uses the existing faded-ink token, and the conditional
mark is a word, not an icon (design prohibitions). `TournamentFace.tsx` takes a prop
saying whether counts link; `SetupPreview` passes false.

### D9. Removing `unpaid_list_treatment`

- An Alembic migration drops `tournaments.unpaid_list_treatment`. The downgrade
  re-adds it with default `greyed`.
- `UnpaidListTreatment` is removed from `models.py`, and the field is removed from
  `TournamentUpdate`/`TournamentOut` and `api.ts`.
- `export_json`: the field leaves `_TOURNAMENT_FIELDS` and `SCHEMA_VERSION` becomes 18.
  Importing a document of version ≤ 17 drops the key, the same way earlier versions'
  retired fields are dropped.
- Setup: the radio group, its state and its i18n keys go from
  `setup/PaymentModeSection.tsx`.

### D10. Counts state the roster, seats stay as they are

Owner decision 2026-10-11: a count beside a capacity means who is listed above the line,
so a reader can tell whether places are left. A row the organizer deleted or merged
away is not counted. `entrants.removed_registration_ids` derives the removed set from
the rule set alone (`row_delete`, `row_restore`, `dedup_decision`: the only writers of
a row's removal), so `/availability` and the card listing need not build the
projection. `AvailabilityOut` and `OpenDisciplineOut` gain `entered`; `taken` and
`free` keep counting seats, which still decide placement.

*Accepted gap:* a removed row's registration still holds its seat, so the count may show
a place free while a new entry is queued. What removal means for the seat, the money and
the mails is a separate change (owner decision: option A now, B apart).

## Risks / Trade-offs

- **`base_rows` is the console's projection, now on an anonymous path.** It builds
  match evidence per row against the HR index, which is more work than a public read
  needs. → Measure on the largest real tournament before archiving. If it is slow,
  give `base_rows` a flag that skips the evidence. Add no cache until there is a
  number to justify one.
- **A gap in queue numbers** when the organizer deletes a live queued row (D2). → It is
  accepted: the number agrees with the fencer's own page, and the deletion is the
  organizer's act on the table.
- **The public roster can disagree with the print on queued rows' Paid** (empty vs
  yes/no). → This is the owner's explicit choice: the print is the organizer's tab,
  the web is the public statement.
- **The card does not link to the roster.** The owner asked for counts on the card to
  link. `fencer-home` already rules out a link inside the card, which is one link. The
  counts on the information screen link instead, one click further. → Raised with the
  owner for confirmation.

## Migration Plan

One deploy: migration, backend, frontend together. The removed column holds no value
that needs keeping, because every stored `hidden` becomes "shown faded" by owner
decision. Rollback is the migration's downgrade, which restores the column as
`greyed` for every tournament.

## Open Questions

- Confirm the count link on the information screen in place of the card (see Risks).
