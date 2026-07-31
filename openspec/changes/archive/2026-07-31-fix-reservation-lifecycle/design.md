## Context

The reservation model in `openspec/specs/registration/spec.md` is sound: per-reservation windows rather than a global deadline, capacity held by unexpired reservations, a substitute queue, VS-only matching. This change does not revisit that model. It closes three states the implementation can enter and never leave.

Current state, verified against `main` at the time of writing:

- `backend/app/routers/registrations.py:254` exempts only `CANCELLED` from the `already_registered` guard, so `EXPIRED` is terminal.
- The router exposes `register`, `my_registration`, `my_registration_payment`, `cancel_registration`, `admit_substitute` — no amendment path. `cancel_registration` followed by `register` resets `paid_at`, `refund_state`, and assigns a new VS via `next_vs`.
- `backend/app/matching.py:116` flags a transaction whose VS resolves to a non-`RESERVED` registration, correctly refusing to absorb the money silently — but `apply_payment_links` also skips anything not `RESERVED`, so the organizer has no action that resolves the flag.
- `get_my_registration` filters out `CANCELLED` but not `EXPIRED`, so an expired registration is already reachable through the fencer's own endpoints.

Two constraints shape everything below. The `(tournament_id, fencer_id)` unique constraint on `Registration` forbids a second row per fencer per tournament, so every "start again" path reuses the existing row. And `openspec/project.md` makes determinism a convention — totals are a pure function of inputs — so anything that records money must be reconstructible rather than incrementally patched.

## Goals / Non-Goals

**Goals:**

- No registration state is terminal against the fencer's will while seats remain open.
- A fencer can change their selection without destroying the association between their registration and money they have already sent.
- Every payment that arrives with a valid VS reaches a resolution: paid, reinstated, or explicitly routed to refund by the organizer — never a permanently flagged row.
- Fix one representation of "what is still owed on this VS" that the later payment-matching-hardening change consumes unchanged.

**Non-Goals:**

- Aggregating multiple transactions against one VS. Matching still evaluates one transaction at a time; this change only makes the aggregate *representable*. Aggregation is the matching-hardening change.
- Automatic refund execution. Refunds stay manual, tracked through the existing `refund_state`, consistent with the current cancellation policy.
- Changing VS allocation, format, or lookup scope. That is the structured-VS change.
- Capping repeated expiry cycles per fencer (see Decision 2).
- Organizer-initiated amendment of someone else's registration. The endpoint is the fencer's own registration only.

## Decisions

### Decision 1 — Store what arrived, derive what is owed

`Registration` gains `amount_paid_cents: int`, defaulting to 0: the sum of payments credited to this registration, expressed in the tournament's **primary currency** in cents. The outstanding balance is never stored:

```
outstanding_cents = total_amount * 100 - amount_paid_cents
  > 0  → surcharge or partial payment due
  = 0  → settled (within the tournament's tolerance)
  < 0  → overpayment → refund_state
```

*Why:* there is exactly one writer of money (matching) and one writer of price (pricing recompute on amendment). An upward amendment raises `total_amount` and the surcharge falls out; a downward amendment lowers it and the overpayment falls out as a negative. No field can drift out of step with another because there is no second running total.

*Alternative rejected — an explicit `amount_due_cents` decremented by matching and raised by amendment.* Two writers mutating one counter is precisely the shape that goes wrong under a rerun, a re-ingested statement, or a rule removal.

*Alternative rejected — derive the balance from `BankTransaction` rows at read time, storing nothing.* It cannot drift by construction, but it re-converts foreign amounts at whatever rate is configured *now*, so a rate edit would retroactively change what a historical registration appears to have paid — a determinism violation. Storing the converted figure at match time snapshots the rate that was actually applied. It also puts a join on every email, matcher pass, and API read.

Consequence: the field stores the *converted* amount, and the conversion is the one `matching.paid_cents_in_primary` already performs. Matching writes `amount_paid_cents += converted` at the point it currently sets `state = PAID`, and `unapply_payment_link` subtracts symmetrically.

*Migration:* backfill `amount_paid_cents = total_amount * 100` for rows already `PAID`, 0 otherwise, so every historical registration reads as exactly settled and no pre-existing row acquires a phantom balance.

### Decision 2 — Expired is re-registerable, on the cancelled path, uncapped

`EXPIRED` joins `CANCELLED` in the guard exemption and reuses the same row-reuse branch already written for cancellation: clear the discipline and extra selections, reset the lifecycle fields, allocate a fresh VS, open a fresh window. Capacity is re-checked at that moment like any new registration, so a fencer returning to a filled discipline enters the substitute queue rather than displacing a queue member.

A fresh VS on re-registration is deliberate and unchanged from today's behaviour: the previous cycle's VS may still be quoted on a payment in flight, and reusing it would credit an old instruction against a new selection at a new price.

*Uncapped, per the owner.* The seat is held only for the window length and the reminder and expiry emails already impose friction. Revisit with real data; a cap would need a per-fencer cycle counter, which is a new column for a problem not yet observed.

### Decision 3 — Amendment branches on state; a reserved amendment never renews the hold

One endpoint, `POST /my-registration/amend`, taking the same selection payload as `register` and running the same `_resolve_selection` / `_validate_options` / capacity checks, then:

| State | Effect |
|---|---|
| `RESERVED` | Selection replaced, `total_amount` recomputed. **`vs` and `expires_at` are read-only through this path.** Confirmation reissued with the updated QR and amount. |
| `PAID`, higher total | `total_amount` raised, state stays `PAID`, outstanding becomes positive, payment instructions for the difference emailed against the same VS. |
| `PAID`, lower total | `total_amount` lowered, outstanding becomes negative, `refund_state` set to `PENDING`. Organizer settles manually. |
| `EXPIRED` / `CANCELLED` | Rejected. These go through re-registration (Decision 2), which is a different operation with a different VS. |

The VS and expiry guarantee on the reserved branch is the load-bearing part. If amending extended `expires_at`, the window would be renewable indefinitely by toggling an extra, and the reservation model's whole point — that a hold is short and cheap to release — would be gone. If amending reissued the VS, the fencer's existing QR code would die on every edit.

A `PAID` amendment never reverts to `RESERVED`. The fencer has paid; they owe a difference. Reverting would re-arm the expiry scheduler against someone who has already sent money and would drop their seat out from under them over an afterparty ticket.

Adding a full discipline appends it as a substitute entry (`is_substitute=True`) rather than failing the amendment. Rejecting the whole submission because one added row is full would discard the parts that were fine — and `register` already has the `wait_for_all` shape for this, which amendment reuses.

*Alternative rejected — model amendment as cancel-then-register internally.* It is the current workaround and it is exactly what destroys the payment association. Amendment must mutate in place.

### Decision 4 — A separate `amendments_close` date, defaulting to the registration close

`Tournament.amendments_close: date | None`. When unset, amendment is available on the same window as registration. When set, amendment closes on that date even while registration remains open.

*Why a separate field, per the owner:* t-shirts get ordered and the afterparty gets booked against a roster that has to stop moving, and that moment is genuinely earlier than the registration close for most organizers. Reusing `refundable_until` was the cheaper option but conflates two unrelated policies — an organizer who refunds generously would be forced to accept late amendments.

Validation: `amendments_close` must not fall after `registration_closes` when both are set. A later value would be silently unreachable.

### Decision 5 — Grace reinstatement is capacity-gated and audited; everything else is an explicit organizer action

`Tournament.expiry_grace_hours: int`, default 48. In `matching.py`, before the existing non-`RESERVED` flag:

- Registration is `EXPIRED`, `now <= expires_at + grace`, and every non-substitute discipline still has a free seat → reinstate to `RESERVED`, then fall through to the normal tolerance comparison and payment path. Audited as `reinstated_in_grace`, distinct from `payment_matched`, so a reinstatement is never mistaken for a clean match in the trail.
- Registration is `EXPIRED` and either outside grace or a seat is gone → stays flagged, with the flag reason distinguishing the two so the console can explain which it is.
- Registration is `CANCELLED` → always flagged for refund, never reinstated, whatever the timing. A cancellation is a decision the fencer made; money arriving afterwards is a crossed-in-the-post payment, not a change of mind.
- Registration is `PAID` → unchanged from today (flagged as a conflict), and under Decision 1 this is where a surcharge payment will later be recognised. This change does not yet credit it automatically; the matching-hardening change does.

The capacity gate is what keeps this honest. Reinstating past a full discipline would seat a late payer ahead of a substitute who has been waiting — the queue exists precisely to allocate a freed seat, and grace must not override it.

Outside grace, the organizer gets two actions on the flagged transaction: **reinstate** (offered only where capacity allows, applying the same path as the automatic grace branch) and **mark for refund** (records the amount against the fencer and sets `refund_state`). Both are audited. Both leave the transaction resolved rather than flagged.

*Why 48 hours, per the owner:* it covers the common case — sent on the last day of the window, credited the next morning — plus one weekend day of bank batching, without holding a seat against the substitute queue for a materially longer time than the window itself already did.

### Decision 6 — The fencer hears about it in both directions

Three new mails, localized cs/en like the rest: amendment confirmation (carrying the updated summary, the amount, and the QR — the same content `send_registration_confirmation` builds), reinstatement, and payment-received-after-expiry. The last one matters most: without it the fencer's last word from the system is the expiry notice, while their money sits in the organizer's account. It states plainly that the payment arrived, that the reservation had expired, and that the organizer will be in touch — it does not promise a seat, because at that point there may not be one.

## Risks / Trade-offs

**Grace reinstatement takes a seat a substitute could have had.** → Capacity-gated: reinstatement happens only where a seat is genuinely free, so it never displaces a queue member. The window is short and bounded by `expiry_grace_hours`, and an organizer who wants none of this sets it to 0.

**An amendment loop could be used to renew a reservation indefinitely.** → `expires_at` and `vs` are not writable through the amendment path, enforced in code and asserted by a dedicated test rather than left as a convention.

**A downward amendment after payment creates a refund obligation the organizer may not want.** → It surfaces as `refund_state = PENDING` in the existing manual refund tracking rather than as an automatic payout; the organizer decides. `amendments_close` is the lever for stopping the pattern.

**`amount_paid_cents` stores a converted figure, so a later exchange-rate edit does not restate history.** → That is the intent, and it is the determinism convention. The trade-off is that the stored figure can disagree with what the transaction would convert to today; the audit trail already records both the raw amount and the converted one at match time, which is what makes the disagreement explainable.

**Existing tests assert the current blanket 409.** → `test_registration_gating.py` and `test_registrations.py` are updated in the same change, with the expired case turned into positive coverage rather than deleted.

**Alembic on SQLite.** → All schema changes are additive columns with defaults; no table rebuild, no rewrite of `vs` or any issued value.

## Migration Plan

1. One additive Alembic revision: `Tournament.expiry_grace_hours` (default 48), `Tournament.amendments_close` (nullable), `Registration.amount_paid_cents` (default 0).
2. Data step in the same revision: set `amount_paid_cents = total_amount * 100` where `state = 'paid'`. Every other row keeps 0. No registration acquires a balance it did not have.
3. No backfill of `amendments_close` — unset means "same as registration close", which is the pre-change behaviour.
4. Rollback is a column drop; no issued VS, total, or payment record is rewritten at any point, so a rollback loses only the new fields.

## Open Questions

- **Repeated expiry cycles** — uncapped by owner decision. Revisit with real data if one account is seen cycling a scarce seat; a cap would need a per-registration cycle counter.
- **Surcharge payments are not yet credited automatically.** A payment arriving against a `PAID` registration with a positive outstanding balance is flagged for the organizer in this change. The matching-hardening change credits it via aggregation over `amount_paid_cents`. If that change slips, organizers settle surcharges through manual matching.
- **Substitute entries and grace.** Reinstatement checks the non-substitute disciplines only; a registration whose disciplines are all substitute entries has no `expires_at` today and so cannot expire. Confirm this holds once the substitute admission path also opens a window.
