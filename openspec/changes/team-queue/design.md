## Context

A `Team` belongs to its entering fencer's `Registration`, carries `waitlisted` (and, after
`demotion-hardening`, `waitlisted_since` and `promoted_unpaid`), and is priced on that
registration only while not waitlisted (`pricing`). Capacity is counted by
`availability.taken_team_slots` over live registrations. `console_teams` lists every team
of a discipline ordered by `created_at`, with no filter on the registration's state, and
numbers the waitlist as it goes. No endpoint admits or returns a team.

After `queue-rosters`, the Queue phase is a band of individual rosters built from the
Export discipline tables, with a `/queue` seating summary and an arrow cell; team
disciplines have no Export table.

Owner decisions (2026-09-24): team tabs in the Queue phase with ↑/↓; the Teams phase stays
read-only for rosters; no teams in the participation condition or in paying substitutes.

## Goals / Non-Goals

**Goals:**
- A way back from the team waitlist, with the same money and mail rules as an individual
  promotion.
- Waitlist positions that count only teams that still exist.

**Non-Goals:**
- Roster editing by the organizer, team cancellation.
- Teams in Export.
- Teams in the participation condition or seated by payment.

## Decisions

### D1. Team rows from a team endpoint, not the sheet

`GET /{slug}/queue/teams/{discipline_slug}` returns the discipline's teams on live
registrations, ordered seated first then waitlisted by `(waitlisted_since, created_at,
id)`, each with name, entering fencer, member count, min/max, waitlist position and moment,
and the entering registration's money fields (paid, settled by hand, outstanding, expires)
in the shape `SheetRow` states them, so the money cell is shared. `console_teams` adopts the
same live filter and order for its waitlist position.

*Alternative:* add teams to the sheet projection. Rejected: the sheet is a fencer list; a
team is not a row of it, and `data-export` keeps teams out of it deliberately.

### D2. Admit and return mirror the individual actions over a `Team`

`POST /registrations/{rid}/teams/{tid}/admit` and `/return-to-waitlist`:
- admit: team waitlisted, registration not cancelled/expired,
  `taken_team_slots < capacity`; flip `waitlisted`, reprice, set `promoted_unpaid` when left
  unsettled, open the promotion window where `clocks_run`, audit `team_promoted`, mail
  `send_team_promoted` (suppressed for a registration Squire sends nothing to).
- return: team seated, registration reserved and not settled; flip, reprice, clear the
  window if nothing seated remains owed under it, keep `waitlisted_since`, audit
  `team_returned`.

The shared steps (reprice, window, marks) are factored out of `admit_substitute` so the two
promotions cannot drift.

### D3. The Queue band

`/queue` gains per team discipline `capacity`, `taken`, `free`. The band lists team
disciplines after individual ones when `feature_teams` is on; a team tab renders
`TeamRoster` with its own column set and reuses the arrow cell with team predicates:
↑ when waitlisted and `free > 0`; ↓ when seated and the registration is unpaid.

## Risks / Trade-offs

- [An organizer admits a team whose roster is below minimum] → the row shows the count
  against the bounds; composition is the Teams phase's concern and the deadline checks,
  never enforces.
- [Two organizers admit into the last slot] → the server refuses the second with a worded
  reason.
- [Excluding dead registrations changes positions an organizer has seen] → they were
  counting teams that no longer exist; the new numbers are the true ones.

## Migration Plan

No storage change beyond `demotion-hardening`'s.

## Open Questions

None.
