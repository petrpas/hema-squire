## Why

A registration moved to the substitute queue for non-payment is moved in silence, keeps
a stored total that still prices the seat it lost, keeps a queue place ahead of fencers
who waited from the start, and will quietly accept money that turns it into a paid
registration sitting in the queue — the one state `seating-queue` says the queue never
holds. None of it is visible to the organizer. Each piece is small; together they make
the queue untrustworthy exactly when seating settles and the organizer starts promoting.

## What Changes

- **Demotion is announced.** A registration moved below the line for non-payment — at
  seating settlement (deadline or organizer), on a lapsed promotion window, or on a
  lapsed window of a registration that also holds a queued placement — is mailed, as an
  expired one already is. The mail names the disciplines moved, the fencer's new queue
  position in each, that nothing is owed now and not to pay, and — where a deposit or
  other credit stands — that it stays recorded against the registration. A dormant
  registration is never mailed, as it is never demoted.
- **Demotion reprices.** Demoting recomputes the stored totals, exactly as the
  organizer's return-to-queue already does, so a demoted registration no longer states
  the price of a seat it does not hold.
- **A fully-queued registration never reads as paid.** A registration every placement of
  which is in the queue SHALL NOT read as settled, whatever it has been credited. Its
  credit stays recorded and counts on promotion. Without this, the repricing above would
  turn every forfeited deposit into a "paid" registration. **BREAKING** for the derived
  settled state: an overpaid registration whose total fell to zero by being queued no
  longer reads as paid (the amendment-to-zero case is unaffected, since it keeps a seat).
- **Demotion for non-payment goes to the end of the queue.** Queue order becomes a
  per-placement moment, `queued_since`, instead of the registration time. A new
  substitute placement counts from the registration time, as today; a placement demoted
  for non-payment counts from the moment of demotion; the organizer's return-to-queue
  restores the moment the placement held before, or the registration time. Teams follow
  the same rule on the team waitlist. Every reader of queue order reads it: the queue
  position a fencer is shown, the console's queue view (which states the moment it
  orders by), and the Export rosters' order below the line.
- **A lapsed promotion window takes back only what that promotion seated.** Today a
  registration that had paid for one seat, was promoted into another and did not pay the
  difference loses everything: before seating settles it expires whole — the paid seat
  with it, holding money — and after, it is demoted whole. A promotion now marks the
  placements (and teams) it seated; when its window lapses unpaid those return to the end
  of the queue, the registration is repriced, and what was paid for keeps its seat. Only
  if something is still owed after that does the ordinary lapse apply to the rest.
- **Money arriving on a fully-queued registration is not credited.** The transaction is
  flagged to the organizer with its own reason, and the fencer is told the payment
  arrived and the organizer will be in touch. The organizer resolves it by promoting the
  fencer — promotion re-evaluates that registration's flagged transactions at once, so
  the money is credited against the seat it now owes for — or by marking it for refund.

Out of scope: the tournament setting that lets paying substitutes fill free places by
themselves (a later change, `paying-substitutes`, built on this one); the Queue phase's
move to rosters with arrows (`queue-rosters`); any way back for a waitlisted team.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `seating-queue`: the queue's order is `queued_since`, not the registration time;
  return-to-queue restores a placement's previous queue moment; a lapsed promotion goes
  to the end; the queue view states the queue moment; money on a fully-queued
  registration is refused credit.
- `registration`: settlement and the lapsed-window demotion place the demoted placements
  at the end of the queue, reprice the registration and mail the fencer; the capacity
  requirement's "registration order" becomes queue order.
- `payment-ledger`: settled is never true of a registration sitting entirely in the
  queue, credit or not.
- `payments`: a payment on a fully-queued registration is flagged with its own reason,
  notified to the fencer, and resolved by promotion or refund; demotion joins the
  notices the system sends.

## Impact

- Backend: `models.RegistrationDiscipline.queued_since` and `Team.waitlisted_since`
  (migration backfilling the registration time); `Registration.settled` hybrid and its
  SQL expression gain the fully-queued exclusion; `scheduler._demote` sets the moment,
  reprices and is followed by a mail at every demotion site;
  `routers.registrations.queue_position`, `return_to_queue`, `admit_substitute`
  (re-evaluation of flagged transactions); `routers.tournaments.console_queue` and the
  teams view's waitlist position; `matching._is_payable` and a new flag reason;
  `emails.send_demoted`, `emails.send_payment_while_queued`; `sheet.base_rows` carries
  each queued placement's moment; `export_json` schema version 15 carrying the moments.
- Frontend: `export/ordering.rosterOrder` sorts the queued group by the moment;
  `QueueEntryLine` states it; the flag reason's label; `api.ts` types.
- i18n: two mails (backend catalogs, Czech and English), the flag reason and the queue
  moment label (frontend).
- Data: existing placements take the registration time as their moment, so no queue
  reorders on migration.
