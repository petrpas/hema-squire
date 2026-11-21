## Why

A team whose registration expired or was cancelled disappears from every place the organizer
reads teams: the Teams view, the Queue phase, the Export team tabs and the public roster all
list only teams on live registrations (`live_teams`). An expiry happens on its own, at night,
by the payment clock. The organizer is not told, the team is simply gone, and the only trace
left is a registration row reading "Rezervace vypršela" on the fencer list, and only when that
registration also held an individual entry. A team that the organizer expects at the venue can
vanish without the organizer ever learning about it.

The fencer list has the opposite problem. It still projects the roster members of a team on an
expired registration as start-field rows, so fighters who will not fight are listed as if they
would.

## What Changes

- The organizer's **Teams view** lists, under each team discipline, the teams on expired or
  cancelled registrations below the live teams. They sit beneath a line of their own, in
  greyed rows, and each states its reason (expired / cancelled), the moment it happened, the
  entering fencer and any money the registration still holds. The roster can still be unfolded
  but is read-only. These rows take no capacity and no waitlist place, and no action is
  offered on them.
- The **Queue phase**'s team tabs list the same teams the same way: below the waitlist,
  greyed, with no admit or return arrow. The tab's counts and free slots are unchanged.
- The **fencer list** stops listing the members of a team on an expired registration, which
  makes it agree with what cancellation already does. The registration's own row, stating
  its expired state, stays where it stands today.
- Unchanged: the Export team tabs, the public entrants roster, capacity and waitlist counting,
  the reinstatement rules, and a team cancelled alone (`Cancelling one team`), which takes its
  roster with it and so has nothing left to show.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `team-disciplines`: **Organizer's teams view** gains the lapsed teams beneath their own line.
- `seating-queue`: **The team waitlist in the Queue phase** lists lapsed teams read-only below
  the waitlist, which replaces the scenario "A dead registration's team is not listed".
- `etl-console`: **The fencer list is the tournament's start field** states that members of a
  team on an expired or cancelled registration are not listed.

## Impact

- Backend: `availability.py` (a reader of lapsed teams beside `live_teams`),
  `routers/tournaments.py` (`console_teams`, `console_queue_teams`), `schemas.py`
  (`ConsoleTeamDisciplineOut`, the queue team response), `sheet.py` (member rows only for live
  registrations).
- Frontend: `TeamsPanel.tsx` / `teams/`, `queue/TeamRoster.tsx`, i18n `cs.json` / `en.json`.
- No migration. The expiry moment is read from the existing `reservation_expired` /
  `expired_holding_payment` payment events, and the cancellation moment from
  `Registration.cancelled_at`.
