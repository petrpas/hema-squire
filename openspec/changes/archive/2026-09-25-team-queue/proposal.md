## Why

A team that lands on its discipline's waitlist — because the discipline was full when it
was entered, or because its entering fencer still owed money when seating settled — stays
there for good. No endpoint admits a team and the Teams phase says so outright. When a
slot frees, the organizer can do nothing about it inside Squire; with `demotion-hardening`
moving unpaid teams to the end of the waitlist at settlement, this becomes a trap that
closes on every tournament with team disciplines and a seating deadline.

## What Changes

- **The Queue phase gains a tab per team discipline**, beside the individual rosters, while
  the team disciplines feature is on. Its rows are teams: name, entering fencer, member
  count against the discipline's minimum and maximum, and the money of the entering
  fencer's registration; the line falls at the discipline's capacity in teams, seated teams
  above it and the waitlist below it in waitlist order, each waitlisted team with its
  position and its moment.
- **↑ admits a waitlisted team** while the discipline has a free slot: the team is seated,
  its fee is billed to the entering fencer's registration, a payment window opens where the
  registration's clocks run, and the entering fencer is mailed that the team has a place and
  what is now due — the individual promotion, applied to a team. A promotion that is not
  paid is taken back alone, as `demotion-hardening` fixes; the entering fencer's paid seats
  stay.
- **↓ returns a seated team to the waitlist** while the entering fencer's registration is
  unpaid, keeping the team's moment, as the organizer's individual return does.
- The waitlist position counts only teams on live registrations; a cancelled or expired
  registration's team no longer takes a place in the count.
- **The Teams phase stays read-only**, for rosters: it no longer states that admission is
  offered nowhere, but that it is offered on the Queue phase.
- Teams stay outside the participation condition and outside paying substitutes.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `seating-queue`: a requirement for the team waitlist in the Queue phase — rows, line,
  admission and return.
- `team-disciplines`: the waitlist is admitted from by the organizer; the read-only teams
  view points to the Queue phase; waitlist position counts live registrations only.
- `registration`: **Capacity and substitutes** no longer says admitting a waitlisted team is
  not offered.

## Impact

- Backend: `POST /registrations/{id}/teams/{team_id}/admit` and `.../return-to-waitlist`,
  mirroring `admit_substitute` / `return_to_queue` over a `Team` (repricing, window, marks,
  audit, mail); `send_team_promoted`; `/queue` summary adds per team discipline capacity,
  taken and free; a team-rows endpoint for the Queue tab (or `console_teams` extended with
  money and the live filter); waitlist position over live registrations ordered by
  `waitlisted_since`.
- Frontend: `queue/` gains a team roster and its columns; the band lists team disciplines
  after individual ones; arrows and refusal texts; Teams phase copy.
- i18n: team arrows, hints, refusals, mail (cs, en).
- Sequencing: last — after `demotion-hardening` (moments, marks), `queue-rosters` (the
  phase), and `participation-condition` (the **Capacity and substitutes** text it edits).
