## Why

The preceding change lets a tournament say that its organizer keeps the
registrations. It does not yet give a fencer anywhere to go. Such a tournament
publishes, appears in the listings, offers its disciplines and prices — and then
refuses every registration, correctly, with nothing to offer instead.

Three surfaces need it, and none of them exists:

**The way out.** There is no field anywhere in the system holding the address of
an external registration form. A grep across the specs finds the phrase only in
`table-import`'s prose about importing "an external registration table". It is a
new field, not a reconfiguration of one.

**The public participant list.** It reads confirmed as `state == PAID`. On a
tournament Squire does not collect for, nothing ever reaches `PAID` — money is
never requested and reconciliation is refused — so the list is either empty or
entirely "unconfirmed", according to a setting about unpaid reservations that
does not apply. This is already live on every payments-off tournament, and
`registration`'s own lifecycle requirement contradicts it in the same document:
such a registration "SHALL be presented to the fencer as confirmed rather than as
awaiting payment". The list is the last requirement that still reads payment
state as attendance.

**Mandatory setup.** Completeness requires a bank account "on a tournament Squire
collects money for". It has no answer for a tournament Squire does not register
for: the registration window is enforced as a gate that will never open, and the
one item that actually matters — where the fencer should go instead — is not
asked for at all.

And one payment rule belongs with them, because it is the same shape of
constraint. `reservation with deposit` holds a seat on a deposit and expires it
when the deposit does not arrive on a per-registration clock. That only works
against a feed that arrives by itself. A tournament whose statements are uploaded
by hand in batches cannot answer a sliding per-registration window; it can answer
a single check after one deadline. Offering the deposit mode without a configured
Fio token offers a promise the intake cannot keep.

## What Changes

- **A tournament carries the address of its external registration**, offered
  where the tournament is defined and required to publish where the organizer
  keeps the registrations.
- **The public surfaces send the fencer there instead of to a form.** The card's
  Register action, the detail page's registration tab, and the tournament
  information all point outward, stating plainly that registration is kept
  elsewhere rather than presenting a closed window.
- **The public participant list stops reading payment state as attendance.**
  Where Squire does not guarantee a payment state — the organizer keeps the
  registrations, or the payments feature is off — the list SHALL present who is
  entered without marking anyone unconfirmed, and SHALL state how current the
  list is, since on an imported roster that is a real question with a real
  answer. **This fixes payments-off tournaments too**, which have the defect
  today.
- **Mandatory setup branches on who keeps the registrations.** The external
  address becomes mandatory where the organizer keeps them; the bank account is
  not asked for, since nothing is collected; the registration window stops being
  enforced as a gate and becomes what it is — a statement of when the organizer's
  own registration runs.
- **`reservation with deposit` requires a configured Fio token.** Without a feed
  that arrives by itself, the two modes that remain — immediate payment and
  reservation without deposit — are both due at one seating deadline, which a
  batch of uploaded statements can answer. The tournament keeps its reminders and
  its confirmations; what it loses is the per-registration sliding window.
- Setup stops offering the sections nobody operates on an organizer-kept
  tournament.

Not in scope: migrating an organizer-kept tournament into a Squire-kept one with
its roster intact; the precedence of an organizer's edit over a fencer's. Both
deferred.

The Mine tab needs no change, contrary to the working brief. It lists tournaments
the account is bound to by registration **or by organizing**, so an organizer-kept
tournament appears there for its organizer, correctly, and is absent for a fencer
who never registered in the application — which is already what it does.

## Capabilities

### New Capabilities
- `external-registration`: where a tournament's registration lives when Squire
  does not hold it — the address, what requires it, how the public surfaces send
  a fencer there, and what a participant list means when no payment state stands
  behind it.

### Modified Capabilities
- `registration`: the public participant list no longer equates confirmed with
  paid where no payment state is guaranteed, and states the currency of what it
  shows.
- `tournament-admin`: setup completeness branches on who keeps the registrations;
  a new constraint binds the deposit payment mode to a configured payment feed.
- `fencer-home`: an upcoming tournament whose registrations the organizer keeps
  offers a way out rather than a Register action.
- `setup-navigation`: the tabs stop carrying sections that govern a registration
  Squire does not run.

## Impact

**Backend** (`backend/app/`): a URL column on `Tournament` with an Alembic
migration and validation of the address as a URL (`fieldtypes.py`, `constraints.py`
hold the existing patterns); a branch in `setup.setup_missing`; the participant
list in `routers/registrations.py:251` and the freshness value it must state; the
deposit/feed constraint beside the existing payment-parameter validation.

**Frontend** (`frontend/src/`): the field in Setup's identity or timeline
section; the card action in `FencerHome.tsx`; the registration tab in
`TournamentDetail.tsx`, which today decides `canRegister` from availability and
free places; the participant list; `api.ts`; `i18n/{en,cs}.json`.

**Depends on `add-registrations-kept-by`**, which introduces the value everything
here branches on.

**Reaches beyond the mode cut**: the participant-list fix and the deposit/feed
constraint both apply to tournaments that have nothing to do with this axis. That
is intended — both defects were found by asking what a tournament without
guaranteed payment state should do, and neither is worth leaving in place until
someone rediscovers it.

**Design constraints**: `CLAUDE.md` and `openspec/squire-design-spec.md`. The
outward link is a link to somewhere else on a page that is otherwise entirely
Squire's, so it needs to read as a destination and not as a default blue anchor.

**Risk**: the participant list changes what the public sees on tournaments that
exist today. A payments-off tournament's list goes from empty or all-grey to a
plain list of entrants. That is the fix, but it is publicly visible and the owner
should know before it ships.

**Verification**: `pytest` for the branch in completeness, the list under each
combination of feature and ownership, and the deposit/feed refusal; `vitest` for
the card, the detail page and the list; and a read of the pilot's own public page
under the new rules, since the pilot is exactly the roster this is for.
