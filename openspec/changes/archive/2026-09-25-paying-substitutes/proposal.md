## Why

After `demotion-hardening`, money sent by a fencer waiting in the queue is held for the
organizer, who seats them or refunds it. That is right for an oversubscribed tournament,
where the queue's order is a promise to the fencers in it. It is needless work for a
tournament that is not oversubscribed: its organizer would gladly let anyone who pays take
a free place the moment the money arrives, and today they must promote each one by hand
— or, before this, a fencer paid and silently became a paid fencer sitting in the queue.

## What Changes

- **A tournament setting: "Náhradníci, kteří zaplatí, zaplní volná místa sami"**, off by
  default. Offered in Setup's payment parameters, only on an automatic tournament whose
  payments feature is on; retained unchanged while hidden, as every hidden parameter is.
  It may be changed at any time, before or after seating settles.
- **With it on, a waiting registration is told how to pay.** A registration wholly in the
  queue — every individual placement queued, no seat held — whose clocks run is offered
  payment instructions for its **claim**: what it would owe with every queued individual
  placement seated, less what it has already been credited (a forfeited deposit counts).
  The full price, never a deposit. The instructions appear wherever instructions are
  shown — the fencer's registration detail, the confirmation of a registration queued at
  submission, and the demotion notice, which then offers them instead of saying not to
  pay. They state that the place is taken only if every discipline waited for is free
  when the payment is credited.
- **With it on, a payment seats.** A payment on such a registration whose amount matches
  the claim within tolerance, arriving while every discipline it waits for has a free
  place, seats all of them at once, is credited, and the fencer is told they have a place.
  That is the participation condition applied as the payment's own condition: the payment
  is for everything the registration waits for, so it seats everything or nothing.
- **Otherwise the payment is held**, as with the setting off, with a reason naming why —
  no place, or an amount that is not the claim. A held payment whose only obstacle was a
  full discipline is re-evaluated on every matching pass and **seats itself when the
  places free**; among several such, the one that arrived first is seated first. The
  organizer may still promote anyone or refund a held payment at any time.
- The Queue roster states, on a queued row, that its payment is held.
- Waitlisted teams are outside: a registration's claim covers its individual placements;
  its teams stay waitlisted.
- A registration whose clocks are dormant — hand entry, issued — is offered nothing and
  seated by nothing; its payments are held for the organizer as with the setting off.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `tournament-admin`: the setting among the payment parameters.
- `seating-queue`: the queue still holds no credited money, but may state a claim; a
  paying substitute takes free places by their payment; the "no automatic promotion"
  rule gains this single, fencer-triggered exception; the roster states a held payment.
- `payments`: a payment on a queued registration seats it where the setting allows and
  everything it waits for is free; a held payment re-evaluates into a seat when places
  free.
- `registration`: payment instructions, the confirmation of a queued registration and the
  demotion notice carry the claim where the setting is on.

## Impact

- Backend: `Tournament.queue_payment_seats` (bool, default false) and
  `Registration.claim_total` / `claim_total_eur` stored beside the totals and recomputed
  with them; matching's queued branch (from `demotion-hardening`) gains the seat path and
  two reasons; the flagged re-evaluation orders held queued payments by arrival;
  payment-instructions endpoint, confirmation and demotion mails branch on the setting;
  Setup schema and completeness untouched (a boolean has no incomplete state).
- Frontend: the setting in Setup's payment section with its explanation; fencer detail
  shows claim instructions; Queue roster marker for a held payment; flag reason labels.
- i18n: setting label and hint, claim wording in the app and mails, reasons (cs, en).
- Sequencing: after `participation-condition` (the claim is "everything waited for" only
  because a waiting registration is wholly queued) and `demotion-hardening`.
