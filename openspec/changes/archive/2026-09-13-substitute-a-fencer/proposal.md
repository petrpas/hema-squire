## Why

A fencer who has paid and then cannot come usually sends somebody in their
place. The organizer has no way to record that: today the row can only be
deleted and a new one entered by hand, which throws away the registration's
place in the list, its variable symbol and everything credited against it, and
then asks the organizer to reconcile money that arrived under a name no longer
on the roster. The substitution is a single fact — *this seat changed hands* —
and Squire should record it as one.

## What Changes

- The fencer table offers **Nahradit** at the end of a row, beside the existing
  delete. Delete stays what it is: a seat given up. Replace is a seat handed on.
- The action opens a dialog, *Výběr náhradníka*, which finds the substitute by
  name in the HEMA Ratings index — the picker account creation and the profile
  page already use. A profile is offered, not required: a name HEMA Ratings does
  not carry is accepted and the row goes on to matching like any other.
- On an automatic tournament the dialog additionally requires an e-mail address,
  offering the replaced fencer's own as the value to keep — a club that entered
  three people under one address keeps that address — and states plainly that
  the substitution will be mailed there.
- The substitute takes the seat whole: the row's fixed number, its registration
  moment and therefore its place in the list, its position above or below the
  line in every discipline's substitute queue, its variable symbol, its total,
  and everything credited against it where the tournament collects payments.
  Nothing is charged, refunded or moved in the payment journal; what the two
  fencers settle between themselves is not Squire's business.
- Where the address entered belongs to an existing Squire account, the seat is
  transferred to that account and the substitute sees it in their profile. Where
  that account already holds a registration on this tournament, the substitution
  is refused with a stated reason.
- Two mails go out on an automatic tournament: one to the substitute confirming
  what they have inherited, one to the replaced fencer saying who took their
  place. Where the address was kept, the two coincide and one mail is sent.
- The substitution is a rule in the manual-edits log like every other manual
  action: it names both fencers, and withdrawing it returns the seat to the
  fencer it was taken from.

## Capabilities

### New Capabilities
- `fencer-substitution`: replacing the fencer behind a row while the seat —
  order, symbol, total and credits — stays put; who may be named as a
  substitute, what the dialog requires in each mode, which accounts are joined
  to the seat, what mail is sent, and how the substitution is withdrawn.

### Modified Capabilities
- `etl-console`: the row-actions column offers substitution beside removal, on
  the two phases that settle the roster, and the fencer table states a
  substituted row's provenance.
- `edit-rules`: a third kind of rule, whose subject is the identity behind the
  row rather than a projected field or a registration's billing.
- `registration`: a registration's fencer is no longer fixed for its lifetime;
  the confirmation trail says so.

## Impact

- Backend: `app/rules.py` (new kind, its validation and replay), `app/sheet.py`
  (projection of a substituted row), `app/models.py` + a migration (the
  substitution's stored subject), `app/emails.py` and `app/locales/*.json` (two
  new messages), `app/routers/rules_api.py`, `app/accounts.py` (finding or
  making the substitute's fencer record).
- Frontend: `src/SheetArea.tsx` (the second row action), a new
  `src/substitute/` directory holding the dialog and its sections,
  `src/api.ts`, `src/i18n/*.json`.
- No change to the payment ledger, the bank feed, matching, or export.
