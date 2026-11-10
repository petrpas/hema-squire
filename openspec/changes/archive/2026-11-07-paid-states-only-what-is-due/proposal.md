## Why

In reservation mode nothing is owed at registration — the seat is held until the
seating deadline, by which the full amount is owed (`registration`, Payment
mode). The public roster does not know that: it asks only whether Squire
collects the money and whether the registration is settled, so from the moment
of registration it prints Paid **no** and draws the row faded. That is a claim
that somebody has failed to pay, made about fencers nobody has asked for money
yet — the distinction `Registration.settled` itself is careful about ("Owing
nothing and having paid are different statements").

It is not a corner case. A reservation-mode tournament reads this way for every
seated entrant from the day registration opens until the seating deadline, which
is most of its public life.

## What Changes

- Where Squire collects the money, a seated row's Paid cell SHALL read **no**,
  and the row SHALL be drawn faded, only once that registration's money is
  actually due: a payment window is running, or the obligation the seat is held
  under has fallen due.
- A seated row on which nothing has been asked yet SHALL leave Paid empty and
  SHALL NOT be drawn faded — the same silence the spec already requires where
  Squire does not collect, for the same reason: the absence of a mark is not a
  claim that anybody has failed to pay.
- A settled row SHALL read **yes** whenever it is settled, as now, whether or
  not anything was due — paying early is not a thing the roster hides.
- Unchanged: queued rows and waitlisted teams state nothing in every mode;
  ordering stays paid-first; the fading rule stays the backend's to decide and
  the client restates none of it.
- The organizer's surfaces are untouched. The Export tab and the printed roster
  (`roster-print`) state the settled flag to a reader who knows the mode and is
  owed the raw fact; the public roster is the surface making a claim to someone
  who does not.

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

- `public-entrants`: the Paid column's **no** and the faded row become
  conditional on money being due, not merely on Squire collecting it.

## Impact

- `backend/app/entrants.py` — `_conduct`/`_paid` gain the question "is this
  registration's money due now", answered per registration (an items-only
  registration on an event owes at once whatever the stored mode says —
  `setup.owing_mode`).
- `backend/tests` — the entrants roster tests; new cases for reservation mode
  before and after the seating deadline.
- No frontend change: `faded` and `paid` already arrive decided
  (`frontend/src/entrants/*` restates no rule). No migration: nothing is stored.
