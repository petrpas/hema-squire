## Context

The current lifecycle is one shape, implemented across four places:

```
  register()                    expires_at = registered_at + reservation_validity_days
                                is_substitute = taken_seats >= capacity   (decided once)
  availability.taken_seats()    PAID or (RESERVED and not expired), is_substitute = False
  process_expiries()            RESERVED and expires_at <= now  →  EXPIRED
  admit_substitute()            one entry, organizer-triggered, refuses if no seat free
```

Everything about "who is in" is decided at registration time and never recomputed in bulk. There is no tournament-wide moment. Three facts from the code shape the design:

- **`queue_position` already ranks by `Registration.registered_at`** (`routers/registrations.py:60-72`). Demoting a registration therefore places it in the queue in registration order for free — no sorting code is needed to preserve "order still by reservation order".
- **`expires_at IS NULL` is currently used as a proxy for "is a substitute"** — `process_reminders` filters `expires_at IS NOT NULL` (`scheduler.py:34`) and `register()` writes `None` for substitutes. A mode that seats a fencer with no private clock breaks that proxy.
- **Substitutes are unbilled at the pricing level**, not just gated in the router: `pricing.py:354` excludes substitute entries from the total, so an all-substitute registration is priced at zero. This is load-bearing for the decision below.

## Goals / Non-Goals

**Goals**
- Express all three organizer models with one mechanism and one new date.
- Keep `expires_at` single-meaning, so no ordering accident can release a seat that should have been queued.
- Preserve registration order across demotion without new sorting.
- Keep money out of the substitute queue entirely.
- Leave existing tournaments byte-identical in behaviour.

**Non-Goals**
- Notifying demoted fencers (deferred; the pass emits audit events, mail comes later).
- Card payments — still out of scope everywhere, and still the only thing that would make `immediate` actually immediate over a bank transfer.
- Automatic promotion by any rule. After the deadline the system shows data; the organizer decides.
- Percentage deposits.

## Decisions

### Decision 1 — Two clocks with two distinct terminal outcomes

The change turns on separating them:

| Clock | Field | Scope | Running out means |
| --- | --- | --- | --- |
| payment window | `Registration.expires_at` | one registration | `EXPIRED` — seat released, out of the queue |
| seating deadline | `Tournament.seating_deadline` | whole tournament | moved to the substitute queue, seat released, **still queued** |

The deadline is **never written into `expires_at`**. If it were, `process_expiries` — which runs early in `run_tournament_tick` by deliberate design, so an expired reservation cannot receive a reminder — would set `EXPIRED` before settlement ran, releasing the seat *and* dropping the fencer out of `queue_position` (which filters `state == RESERVED`). Keeping the deadline in its own field makes that failure unrepresentable rather than merely avoided.

`settle_seating` nonetheless runs **before** `process_expiries` in the tick. In `deposit` mode a fencer can hold both clocks at once, and without a fixed order the outcome of a deposit expiring on the deadline date would depend on tick timing. Settlement first makes it deterministic: everything still `RESERVED` at the deadline is queued, uniformly.

### Decision 2 — `expires_at` means the payment window, and `None` means "no money has been requested"

Per mode, for a seated registration:

```
  immediate     expires_at = registered_at + reservation_validity_days
  deposit       expires_at = registered_at + reservation_validity_days   (for the deposit)
                → cleared to None once the deposit is credited
  reservation   expires_at = None from the start
```

`taken_seats` already treats `expires_at IS NULL` as holding (`expires_at.is_(None) | expires_at > now`), so a `reservation`-mode seat is held correctly with no change to the capacity predicate.

What must change is `process_reminders`, which uses `expires_at IS NOT NULL` to mean "not a substitute". It is re-anchored to whichever clock applies and filters on substitute status directly, reusing the existing fully-queued predicate (`emails.py:98`: every entry substitute **and** every team waitlisted):

```
  seated, expires_at set   →  remind reminder_day days before expires_at
  seated, expires_at None  →  remind reminder_day days before the seating deadline
  fully queued             →  never (nothing is owed)
```

### Decision 3 — Paying the deposit clears the window rather than extending it

`harden-payment-matching` Decision 3 records that a partial payment does not extend the validity window — otherwise a hold is renewable by dribbling money. A deposit is a published threshold, not an arbitrary partial, so it cannot be used that way; and the mechanism is not extension. Reaching the deposit **discharges** the payment window: `expires_at` is set to `None`, and the seating deadline becomes the only remaining obligation. The earlier decision stands unmodified.

### Decision 4 — Flat deposits only

A percentage deposit recomputes when a registration is amended, so the amount owed can move after it has been paid — and combined with Decision 3 that produces a registration which was correctly deposit-paid, had its window cleared, and is now silently under-deposited with no clock running. A flat amount cannot do this. `deposit_amount` is a price like any other: a whole-unit local amount plus an independent `deposit_amount_eur` under the dual-currency rules, both authoritative, no conversion, participating in the "all prices filled" completeness check.

### Decision 5 — The queue holds no money

Substitutes are unbilled at the pricing level (`pricing.py:354`), and this change keeps it that way. A fencer below the line owes nothing and can pay nothing; money is requested only on promotion. This is what removes the whole refund surface the alternative design would have created — a fencer paying for a seat that may never exist.

Two consequences follow directly:

- **`queue_length` and `queue_position` stay correct as written.** Both filter `Registration.state == RESERVED`. A `PAID` substitute would be invisible to both; because no substitute can pay, none can exist.
- **The return-to-queue endpoint refuses a `PAID` registration.** Demoting someone who has paid would put money in the queue. The organizer's route for that case is cancellation, which already carries the refund path.

### Decision 6 — Settlement is one-shot, stamped on the tournament

The demotion predicate is "`RESERVED` and seated". `admit_substitute` produces exactly that: it promotes, opens a payment window, and mails instructions, leaving the fencer reserved, seated, and unpaid. Without a guard the next scheduler tick would demote them again, and the organizer's promotions would silently unwind on a loop.

`Tournament.seating_settled_at` is set by the pass and checked by it, mirroring the `composition_reminded_at` stamping already used by `process_composition_reminders`. Settlement runs at most once per tournament, ever.

**The organizer may also trigger it by hand**, before the deadline arrives — the equivalent of closing seating early once the roster looks right. It is the same pass through the same stamp, so a manual settlement and a scheduled one cannot both happen: whichever fires first is the one that ever runs. Manual settlement is available in every mode, including `immediate`, where it demotes nobody but still closes seating so that later registrations join the queue instead of taking seats.

It is not reversible. Demoting a field of registrations and then undoing it would need every demotion individually remembered, and the organizer already has promotion to correct any individual case. The console SHALL therefore confirm before firing it.

### Decision 6a — "Seating has settled" is one predicate, satisfied two ways

Everything downstream — post-deadline registration, the reminder anchor, whether the pass may run — asks the same question, and manual settlement means the answer is no longer "has the deadline passed":

```
  seating_has_settled(t, today) =
        t.seating_settled_at is not None        # settled, by hand or by tick
     or today > seating_deadline_for(t)         # deadline passed, tick not yet run
```

Both disjuncts are needed. The stamp alone leaves a gap between the deadline passing at midnight and the next scheduler tick, during which registrations would still be seated. The deadline alone ignores an early manual settlement. The predicate lives beside `seating_deadline_for` in `setup.py` so no caller reconstructs it.

### Decision 7 — An unset seating deadline falls back to registration close

`seating_deadline` is optional. Unset, it resolves to `registration_closes`, which itself already falls back to `Tournament.date` (`setup.py:156`). This mirrors `amendments_close`, documented as "unset means the same window as registration". A tournament with no explicit deadline therefore has no organizer-managed tail: seating settles when registration closes.

Resolution lives in one helper in `setup.py` alongside `registration_availability`, so no caller spells the fallback chain out a second time.

### Decision 8 — Promotion after the deadline is clamped to the tournament date

`admit_substitute` currently opens `now + reservation_validity_days` unconditionally. Promoted three days before a tournament with a seven-day window, that outlives the event. The window becomes `min(now + reservation_validity_days, end of Tournament.date)`, honouring both rules that apply: money requested always gets a payment window, and no reservation outlives the tournament it is for.

**A promoted fencer whose window lapses returns to the queue rather than expiring out of it.** After settlement the queue is the tournament's holding area, and `EXPIRED` would discard someone the organizer deliberately chose, in registration order they would then lose. Before settlement, expiry keeps its current meaning. This was the one behaviour here that was a judgement call rather than a consequence; **the owner confirmed it on 2026-08-04** — a lapsed window on a settled tournament demotes rather than expires.

### Decision 9 — Existing tournaments default to `immediate`

Current behaviour — full amount owed at registration, held for the payment window, expired if unpaid — is exactly `immediate`. Defaulting the column to it makes the migration behaviour-preserving with no data rewrite. `immediate` mode also has nothing to settle: no unpaid reservation survives its window, so `settle_seating` is a no-op there and every existing tournament is untouched by the new pass.

The 2–7 range on `reservation_validity_days` is enforced **on write only**. The shipped default is 10 and live tournaments carry it; clamping stored values would change their behaviour to satisfy a UI range. Existing values are left alone and validated on the next edit.

## Risks / Trade-offs

- **`reminder_day` does not survive a 2-day window.** It defaults to 5 and is validated only `gt=0`. With the tightened range the only legal low-end value is 1, and `reminder_day >= reservation_validity_days` means the reminder fires after expiry — silently, and already a known unimplemented finding (`harden-payment-matching` 4.4). This change makes the validation mandatory rather than nice to have.
- **Two dates that both read as "until when can I sign up".** `registration_closes` is the hard close; `seating_deadline` is a soft cutoff inside it. An organizer conflating them sets one thinking it is the other. Mitigated by validation (`seating_deadline <= registration_closes`) and by help text that states the difference in one line, but it remains the main usability risk in the change.
- **`immediate` is not immediate.** Fio publishes with minutes-to-hours of lag and matching runs on a scheduler tick, so the seat is held on trust for the settlement lag. The mode is honest about this by giving a 2–7 day window; a genuinely immediate flow needs card payments, which stay out of scope.
- **The organizer must actually work the queue.** After the deadline nothing promotes automatically. A tournament whose organizer never opens the console leaves paid-up fencers sitting below the line. This is the deliberate consequence of "the system just shows the data"; the queue view has to make the pending work obvious.
- **First select-typed field in `ParamPanel.tsx`**, which currently understands only `number`, `date` and `text`, and whose dependent fields (deposit amounts, seating deadline) are relevant only in some modes. Conditional visibility in that panel is new.

## Open Questions

None. Decision 8's second half — whether a promoted fencer who lets the window
lapse returns to the queue or expires out of it — was resolved by the owner on
2026-08-04 in favour of returning to the queue, and is folded into Decision 8
and task 7.5.
