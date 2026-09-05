## Why

Squire assumes it owns the list of who is coming. Every tournament it holds is
one it registers people for: registration opens on the site, the fencer creates
an account, the scheduler runs clocks against what they submitted, and mail goes
out under the tournament's name.

Most tournaments the product wants are not like that. The organizer already runs
registration somewhere — a Google form, a club mailing list, a spreadsheet a
colleague maintains — and wants Squire for what comes after: the roster cleaned
up, matched against HR, deduplicated, priced, exported. That path exists and is
well built (`table-import`, `edit-rules`, `etl-console`, `console-operations`,
`data-export`) but it has no name, so nothing in the system knows a tournament is
on it.

The consequence is that the automatic machinery stays armed under a roster it
should never have touched. `issue-imported-registrations` had to face this
directly, and its own risk section says it plainly:

> A registration that reaches `scheduler.py` without it opens a payment window
> and sends expiry and reminder mail to people who registered a year ago.

Its answer is a per-registration mark, `clocks_dormant`, set at the moment a row
is issued. That mark is correct and stays. But it is currently the *only* thing
standing between an imported roster and the mail, and it is set by one code path.
A club added by hand to an otherwise-imported tournament, a row issued by a
future path that forgets the flag, a registration created before the flag
existed — each is a way for the single guard to be missed.

A tournament that states who keeps its registrations turns that into a structural
guarantee: the scheduler does not look at such a tournament at all. The per-row
mark stays as the second line, for the mixed case it was designed for — a club
registering late into an otherwise-automatic tournament.

The axis is not one of the four features in `tournament-modes`, and must not
become a fifth. Those four are a rule about *visibility*: "Disabling a feature
hides its settings without changing them", and "a hidden extra item SHALL still
be offered on the registration form and still be sold". This axis does the
opposite — it changes who owns the roster and withdraws the registration form
altogether. `payments` is already the one exception to that rule, with a
requirement of its own to carry it; one exception is a precedent, not a pattern.

## What Changes

- **A tournament states who keeps its registrations**, stored as its own value —
  `registrations_kept_by`, either Squire or the organizer — separate from the
  four features and from any notion of easy or advanced mode.
- **The scheduler does not look at a tournament the organizer keeps.** Not
  registration by registration: the tournament is excluded from the pass over
  tournaments, so no lifecycle code runs against it at all.
- **In-app registration never opens on such a tournament.** Registration
  availability answers with a stated reason of its own, in the one place that
  already decides whether a submission may proceed.
- **It is the third cause of dormancy**, landing in the predicate the preceding
  change built rather than in a condition of its own.
- **It is chosen when the tournament is created and changed on `OTHER`**, in a
  section of its own beside the mode section rather than inside it, so that the
  visibility rule the four features rest on is not broken by a fifth switch that
  changes behaviour.
- **Every existing tournament is Squire's**, backfilled, because that is what
  they all are today.
- **BREAKING for a tournament switched to organizer-kept:** its registration form
  closes and its scheduler clocks stop. Switching is warned and confirmed, and
  states what will stop, in the manner `tournament-modes` already warns about
  turning a feature off.
- `tournament-modes` gains a sentence saying the four features are a different
  axis from this one, so the next reader does not repeat the question.

Not in scope: the external registration URL and the public surfaces that read it,
which follow in their own change; the precedence of an organizer's edit over a
fencer's, which is deferred; migration from organizer-kept back to Squire-kept
beyond the switch itself.

## Capabilities

### New Capabilities
- `registration-ownership`: who keeps a tournament's list of entrants — what is
  stored, when it is chosen and changed, what Squire never does on a tournament
  it does not keep the list for, and how it relates to the four features and to
  the per-registration dormancy mark.

### Modified Capabilities
- `registration`: registration availability gains organizer-kept as a reason a
  submission is refused, and the dormancy predicate gains its third cause.
- `tournament-modes`: the purpose states that the four features govern which
  advanced surfaces a console offers and are a different axis from who keeps the
  registrations, so that neither is read as a value of the other.

`tournament-admin` is deliberately not modified. The new capability owns the
field, its choice and its change end to end; restating it inside the tournament
definition would put one value in two specs. What `tournament-admin` does owe
this axis — how setup completeness branches on it — belongs with the external
registration URL, which is the item that branch turns on.

## Impact

**Backend** (`backend/app/`): a column and enum on `Tournament` in `models.py`
with an Alembic migration backfilling every existing row to Squire-kept; a
condition in `setup.registration_availability` — the single funnel for whether a
submission may proceed, with two callers; a filter in `scheduler.run_tick`'s
select over tournaments; the third cause in the dormancy predicate; the field on
the tournament schemas and the `PATCH` handler in `routers/tournaments.py`.

**Frontend** (`frontend/src/`): a section of its own in the creation flow and on
Setup's `OTHER` tab. `TournamentModeDialog.tsx` already splits its fields out as
`TournamentModeFields` so `TournamentPicker` can embed them at creation; the new
section follows that split rather than joining those fields. `setup/ModeSection.tsx`
is the neighbour it sits beside. `i18n/{en,cs}.json`.

**Interaction with `issue-imported-registrations`**: that change is implemented,
and its `clocks_dormant` mark stays exactly as it is. This change makes it the
second guard rather than the only one. Its tests must pass unchanged.

**Depends on `unify-lifecycle-dormancy`**: the third cause has one place to land
only once that change has made one. Doing this first would mean adding the third
condition to four passes and then removing it again.

**Design constraints**: `CLAUDE.md` and `openspec/squire-design-spec.md` bind the
new section — a static confirmation, no animation, and system copy that states
what stops rather than warning about it in the abstract.

**Risk**: the switch is a behaviour change on a live tournament. The guard is
that it is confirmed and that what it stops is named — an organizer who switches
a tournament mid-registration must not discover it from a fencer who could not
sign up.

**Verification**: `pytest` for the availability refusal, the scheduler exclusion
and the dormancy cause; `vitest` for the section and its confirmation; and one
test that matters more than the others — a tournament the organizer keeps, run
through the full lifecycle with registrations aged past every deadline, sending
nothing and moving nothing.
