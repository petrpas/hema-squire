## Context

After `demotion-hardening`, matching flags a payment on a registration wholly in the queue
(`registration_queued`) and mails the fencer that it is held; flagged transactions are
re-evaluated on every pass; `admit_substitute` re-evaluates a registration's held
transactions after promoting it. After `participation-condition`, a registration either
holds a seat or waits wholly, so "everything it waits for" is well defined for a wholly
queued registration: all its individual placements.

Totals are stored (`total_amount`, `total_eur`) and recomputed by
`pricing.registration_total` with fees frozen to the registration date; instructions,
mails and QR codes state stored totals.

Owner decisions (2026-09-24): a setting, default off; full price, never a deposit; a
multi-discipline waiter's payment seats all or nothing; applies before and after
settlement; offered only on an automatic tournament with payments on, in Setup's payment
section.

## Goals / Non-Goals

**Goals:**
- A paying substitute on a willing tournament takes a free place with no organizer action.
- The fencer knows the amount, the condition and what happens if the place is not free.
- No credited money on a registration without a seat, ever.

**Non-Goals:**
- Mixed registrations' queued placements (a met condition with an outside discipline
  queued): they are promoted by the organizer; their payment path is their seat.
- Teams.
- Refunds (the existing mark-for-refund is the organizer's tool).

## Decisions

### D1. The claim is stored beside the totals

`Registration.claim_total` / `claim_total_eur`, nullable, recomputed wherever totals are
recomputed: the price of the registration with every individual placement seated, from the
same `pricing.registration_total` on a hypothetical placement set. Null where the
registration is not wholly queued, or its clocks do not run, or the setting is off at
recomputation — and the instructions endpoint recomputes on read when the setting is on
and the stored value is null, so turning the setting on needs no backfill.

The claim *outstanding* is `claim_total × 100 − credited` per lane, which is what the
instructions state and the matcher compares; it is never stored, as outstanding never is.

*Alternative:* compute the claim on every read. Rejected: the registration spec requires
every stated amount and QR to be a stored total, so that a price change between a mail and
a later read cannot change what the fencer was told.

### D2. The seat path sits in matching's queued branch

In the branch `demotion-hardening` adds for a wholly queued registration:

```
if not setting or not clocks_run:            flag registration_queued        (as before)
elif amount !~ claim outstanding (tolerance): flag queued_amount_mismatch
elif any queued discipline has no free place: flag queued_no_place
else: seat every queued individual entry; reprice; credit; audit
      "queue_payment_seated"; mail payment received with a place
```

The seat step reuses the promotion internals (entry flip, reprice) without the promotion
window or promotion mail: the money is already in. Bare tokens reach the same branch
through `_is_payable`'s guard; the multi-registration split never seats (a split payment
is not a claim) and flags.

### D3. Re-evaluation order is arrival order

The flagged re-evaluation already runs each pass. For `queued_no_place` transactions it
iterates them ordered by the transaction's booking date then id, and evaluates each against
the free places *as they stand after the previous one seated*, so two held payments for one
freed place resolve to the earlier. `queued_amount_mismatch` is not re-evaluated into a
seat (it may still be re-evaluated for other reasons, as flagged transactions are).

### D4. Turning the setting off

Held `queued_no_place` transactions stay flagged and stop being seatable; their reason is
re-labelled to the plain `registration_queued` on the next pass, so the console does not
promise a self-resolution that will not happen. Stored claims are left; nothing reads them
while the setting is off.

### D5. Surfaces

- Setup: a checkbox with the two one-line consequences, under the payment mode choice,
  hidden unless automatic and payments on.
- Instructions endpoint: the "nothing owed, queued" reason becomes claim instructions when
  the setting is on and the registration qualifies.
- Confirmation (queued at submission) and demotion notice: the claim block with QR, and
  the condition sentence.
- Queue roster (from `queue-rosters`): a marker on a queued row with a held transaction.

## Risks / Trade-offs

- [The queue order stops meaning much on a willing tournament] → stated in the setting's
  own text; the organizer chooses it knowingly.
- [A fencer pays, the place is not free, and waits with money held for weeks] → the held
  notice says so; the organizer sees the marker and may refund.
- [Two payments race for one place within one pass] → D3 orders them.
- [The claim of a registration whose prices changed] → fees are frozen to the registration
  date; the claim is recomputed only when totals are.

## Migration Plan

Add `tournaments.queue_payment_seats` (not null, default false) and the two nullable claim
columns. No backfill.

## Open Questions

None.
