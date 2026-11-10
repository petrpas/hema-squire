## Why

A roster save deletes every member of the team and inserts the list again
(`routers/registrations.py:1664`). A member therefore has no identity that
survives a save, and nobody can say who changed a roster, when, or what it said
before. Three things the console needs next all rest on that missing identity:

- **Matching cannot reach a team's fighters.** A member is the only population of
  real people outside the console's processing pipeline: no module matches them,
  and the ratings snapshot reads `hr_id`s from sheet rows alone
  (`routers/hr_api.py:52-62`). On a tournament whose fencer list holds 18
  registrations and whose rosters hold 67 people, 49 fighters are unmatched and
  unrated — and the team disciplines' pools are drawn from HEMA Ratings. The
  verdicts and corrections that would fix this are rules keyed on a row id
  (`rules.py:39-93`); against a member they would point at a row the entrant's
  next save destroys.
- **The organizer cannot swap a fighter.** A team arrives at the venue and the
  person who entered it cannot reach their manage link. Today the console's teams
  view is read-only by spec, and the fencer list's substitution hands over the
  *registration* — who pays and who gets mail — not a place on a roster.
- **Nothing the organizer does to a roster could be accountable.** Every
  organizer change in the console is a recorded, replayable act. A
  delete-all-and-reinsert write has nowhere to record one.

## What Changes

- **A roster member keeps its identity across saves.** The save becomes a diff: a
  member sent with its id is updated, one sent without is added, one the request
  omits is removed. Ordinals are rewritten from the order sent; order carries no
  meaning and no identity.
- **A removed member is retained rather than erased** — marked removed, excluded
  from every count and every list that states a roster, and restorable. A later
  verdict or rating hanging off a member therefore cannot be orphaned by a
  removal, and a member removed by mistake at the venue can be put back rather
  than re-typed.
- **The organizer may edit a roster from the console**, which reverses the
  current read-only rule. **BREAKING** for the spec, not for any data: the Teams
  view keeps everything it shows and gains the editor.
- **Every roster change is recorded in one log** — the entrant's own edits and the
  organizer's alike, each naming what changed, who changed it, and when. One log
  rather than two, so a disputed roster has a whole story rather than half of one.
- The organizer's edit **sends nothing to the entrant**, following
  `amendment.SURCHARGE_ONLY`: a roster edit moves no money, and a letter per
  corrected row would cost more than the error. The change is visible on the
  team's own page.
- Neither the composition deadline nor the amendment window constrains any of
  this, for the entrant or the organizer — the roster save already ignores the
  amendment window deliberately, and the whole point is the day of the event.

Out of scope, and the next piece of work: members do not become rows of the
console's sheet, matching does not reach them yet, and the console's phase
layout does not change. The Teams view stays where it is in the phase order.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `team-disciplines`: a member has a stable identity across saves; a removed
  member is retained; roster changes are logged; the organizer may edit a roster
  from the console, where the view is read-only today.

## Impact

- `backend/app/models.py` — `TeamMember` gains a removal mark; a new log of
  roster changes.
- `backend/alembic/` — one migration: the column and the table.
- `backend/app/schemas.py` — `RosterMemberIn` carries an optional id;
  `RosterMemberOut` states it; the log's shape.
- `backend/app/routers/registrations.py` — the roster save becomes a diff and
  writes the log.
- `backend/app/routers/tournaments.py` — the console's teams view gains the
  editor's endpoint and the log.
- `backend/app/export_json.py` — the backup document carries removed members and
  the log; `SCHEMA_VERSION` 21 → 22.
- `frontend/src/TeamsTab.tsx` — the editor sends the server's member ids; its
  client-side `rowId` gives way to them.
- `frontend/src/TeamsPanel.tsx` — the console's teams view gains editing and the
  history.
- No change to pricing, placement, capacity, mail, or the public entrants roster.
