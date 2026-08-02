## Why

Not every discipline is individual. Team events — typically three fencers plus a
reserve — are a normal part of a HEMA tournament, and Squire cannot express one at all:
a discipline is priced per fencer, its capacity is counted in fencers, and an entry is
a row on one fencer's registration.

Teams break all three, and they break them in a specific way that the domain forces on
us. A team is entered by one fencer on behalf of people who mostly are not Squire users
and will never become Squire users — the standing reality of team events is that rosters
fill with less active fencers who answer "ok, write me in" by text and register nowhere.
The team fee is one fee for the team, paid by the fencer who enters it, and the roster is
routinely unknown when that fee is paid. So the composition has to be nameable later,
against a deadline of its own, by someone other than the people named.

## What Changes

**Disciplines become individual or team**

- A discipline carries a kind. An individual discipline is exactly what it is today. A
  team discipline additionally carries a minimum and maximum roster size (typically 3
  and 4) and is entered by teams, not by fencers.
- For a team discipline, `capacity` counts **teams**, and the configured fee is the fee
  for **one team**, not per member. The organizer types one number and it is charged
  once per team entered.
- Team disciplines are excluded from the HR category map: they have no HR rating
  category to map to.

**A team is a line item on the entering fencer's registration**

- A registration may carry teams alongside its individual discipline entries. Each team
  has a name, a team discipline, and a roster. The fee lands on that registration's
  total, on its VS, in its QR code, under its expiry — one payment covering the entering
  fencer's own entries and every team they entered.
- One fencer MAY enter more than one team, in the same team discipline or across
  several. Clubs send two teams and one person does the paperwork for both.
- A team entered into a full team discipline joins a waitlist in entry order and is not
  charged, exactly as an individual substitute placement is not charged. Admitting a
  waitlisted team into a freed slot is **out of scope** for this change.
- A registration that carries only teams is valid: the entering fencer need not compete
  individually.

**A roster member is a named person, not an account**

- A team member is a name, optionally bound to a HEMA Ratings profile, with the club and
  nationality that binding carries. A member is never a `Fencer` row and never has an
  account, an email, a registration, a payment, or a login.
- Members are named through the existing nationality-filtered HR similarity search — the
  same picker the profile page already uses. A member HR has never heard of is stored as
  free text with no `hr_id`. This is expected, not an error state.
- The roster is an ordered list of names with no roles. There is no captain field and no
  reserve field: who fences and who sits out is decided on the day. The entering fencer
  is prefilled as the first member as a convenience only, and may be edited or removed
  like any other row.
- The roster is stored per team, and a member's identity is local to that roster. Two
  teams naming the same person produce two independent member rows.

**A composition deadline that checks rather than enforces**

- A tournament carries an optional team composition deadline, the date by which rosters
  are expected to be complete. It is meaningful only when the tournament offers a team
  discipline.
- The deadline **checks, it does not enforce**. It does not lock the roster, does not
  cancel a team, and does not free capacity. After it passes, a team below its
  discipline's minimum is flagged for the organizer, who decides what happens through
  the controls that already exist. Rosters stay editable up to the tournament date.
- The entering fencer is reminded before the deadline when a roster is still short,
  reusing the reservation-reminder mechanism's shape.

**Roster editing lives outside the amendment path**

- Because the fee is per team, editing a roster cannot change any total. Roster edits
  therefore SHALL NOT recompute a price, reissue a VS, resend a confirmation, touch
  refund state, or check capacity, and SHALL NOT be gated by the amendment window.
  Adding, removing, or renaming a *team* is an amendment and is gated as one; editing
  the names inside a team is not.
- This makes the composition deadline independent of `amendments_close` in both
  directions: money can close early while names stay open late, which is what team
  events actually want.

**Organizer visibility, deliberately cheap**

- The console gains a read-only view of teams per team discipline: team name, entering
  fencer, roster with HR bindings, member count against the discipline's minimum and
  maximum, and waitlist position where applicable. Teams below minimum after the
  composition deadline are marked.
- The organizer acts through existing controls. No admit-from-waitlist action, no
  edit-roster-on-behalf, no team cancellation action in this change.

**Export**

- **BREAKING (export format)**: canonical JSON schema version 5 → 6. Teams and their
  rosters round-trip, because without them a restore silently loses every roster.
  Versions 1–5 keep loading and restore with no teams.
- The Google Sheets export and the public participant list are **explicitly unchanged**.
  How a non-registered roster member should appear to the public, and how team results
  reach HR, are deferred: in most team tournaments only the individual pool phase feeds
  HR, and not even that is a rule.

## Capabilities

### New Capabilities
- `team-disciplines`: the team kind of discipline and its roster bounds; per-team pricing
  and team-counted capacity; the team as a registration line item; the roster of named,
  optionally HR-bound members; the composition deadline and its check-not-enforce
  semantics; the organizer's read-only teams view.

### Modified Capabilities
- `tournament-admin`: the disciplines table gains a kind and roster bounds, and the
  meaning of `capacity` and `fee` becomes kind-dependent; the tournament gains the
  composition deadline; setup completeness covers team-discipline configuration.
- `registration`: the priced checklist gains a team section with a distinct control (a
  team is named and entered, not checked); capacity and substitute rules gain their team
  counterpart; the price preview prices team entries; amendment explicitly excludes
  roster editing.
- `setup-navigation`: the composition deadline is allocated to a tab.
- `data-export`: the canonical JSON export covers teams and rosters; the Sheets format is
  unchanged.
- `fencer-home`: the tournament detail lists team disciplines with their team counts, and
  registration management offers roster editing under the composition deadline.

## Impact

- **Schema**: `disciplines.kind`, `disciplines.team_min`, `disciplines.team_max`;
  `tournaments.team_composition_deadline`; new `teams` (tournament, discipline,
  registration, name, waitlisted, created_at) and `team_members` (team, ordinal, name,
  hr_id, club, nationality). Alembic migration backfills every existing discipline as
  individual.
- **Backend**: `app/models.py`, `app/schemas.py`, `app/pricing.py` (team fees join the
  discipline subtotal without joining `discipline_count`), `app/availability.py` (team
  seat counting), `app/setup.py` (completeness, composition-deadline availability),
  `app/routers/registrations.py` (teams on create/amend, roster CRUD),
  `app/routers/tournaments.py` (discipline kind and bounds, deadline, organizer teams
  view), `app/emails.py` (team lines in the confirmation, composition reminder),
  `app/scheduler.py` (composition reminder), `app/export_json.py` (v6).
- **Frontend**: registration form team section and roster editor with the HR picker,
  Setup disciplines table (kind, bounds) and the deadline field, `SetupPreview.tsx`,
  console teams view, `api.ts`, `i18n/cs.json` + `i18n/en.json`.
- **Reused unchanged**: `GET /accounts/hr/search` for member binding; VS allocation,
  bank matching, reminders, refunds and the payments console, none of which learn that
  teams exist.
- **Out of scope**: waitlisted-team admission, organizer roster editing, team results,
  the public participant list, the Sheets export, per-member pricing.
- **Sequencing**: independent of `add-explicit-publishing` and
  `refine-setup-and-preview`, but touches the disciplines table and the Setup tabs that
  both of those move. Apply after them.
