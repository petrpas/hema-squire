## Context

`PaymentPanel` is complete and unreachable whenever its fetch fails. The endpoint
refuses in three named ways (`registrations.py:686-697`):

| refusal | condition | reachable today? |
| --- | --- | --- |
| `404 no_bank_account` | `tournament.bank_account` unset | yes — nothing requires it |
| `409 no_payment_due` | every entry queued **and** every team waitlisted | yes — frontend predicate ignores teams |
| `409 not_unpaid` | state is not `RESERVED` | only as a race against a concurrent match |

`setup.py` is the single source of truth for publication readiness: `setup_missing()`
returns stable item keys, the PUBLISH tab renders them as a checklist, publication
is refused while any remain, and `guard_published_completeness()` prevents a
published tournament being edited back into incompleteness. Adding an item to that
list buys all four behaviours at once.

Constraints: `CLAUDE.md` / `openspec/squire-design-spec.md` ("Bureau 1952") are
binding. The frontend has no test runner; `npm run lint` is `tsc -b --noEmit`.

## Goals / Non-Goals

**Goals:**
- A fencer holding a reservation always learns either how to pay or why they
  cannot yet.
- A tournament cannot reach the state where a reservation is payable in principle
  and unpayable in fact.
- The "is anything due" question has exactly one implementation.

**Non-Goals:**
- No change to how instructions, SPAYD strings or QR codes are computed.
- No deposit, no payment deadline — that concept is unmodelled and is its own
  change.
- No new payments console surfaces; `add-payments-console-ui` owns those.
- No refund-queue work, though `RefundState.REFUNDED` remains unreachable.

## Decisions

### Decision 1 — The gate rides `setup_missing()`, not a bespoke check

`setup.py` gains `MISSING_BANK_ACCOUNT = "bank_account"` and one condition in
`setup_missing()`. Nothing else changes: `publish_tournament` already raises `422
{"reason": "setup_incomplete", "missing": [...]}`, the PUBLISH tab already renders
whatever keys come back, and `guard_published_completeness` already refuses a save
that would empty a mandatory field on a published tournament.

`registration_availability()` is deliberately **not** touched. Its docstring
states that completeness is not re-checked there because a published tournament is
guaranteed complete — that guarantee is exactly what this change extends to the
bank account.

*Alternative considered*: a dedicated check at registration time ("refuse a new
registration when the tournament has no bank account"). Rejected — it moves the
failure from the organizer, who can fix it, to the fencer, who cannot, and it
duplicates a guarantee the publication record already carries.

### Decision 2 — The bank account is mandatory only for a tournament that charges

`setup_missing()` treats a fee of `0` as complete — only `None` is incomplete. So a
club-internal event priced entirely at zero is publishable today, and an
unconditional bank-account rule would refuse it publication over money it will
never collect. The owner chose the conditional form (2026-08-03): **required when
the tournament can produce a nonzero total, and not otherwise.**

"Can charge" is any of the following above zero — every column a total can be
built from, in both currencies, since under `add-dual-currency-prices` the local
and EUR prices are independently authoritative and either can carry the charge:

```
Discipline    fee   fee_early   fee_eur   fee_early_eur
ExtraItem     price   price_eur
Tournament    weapon_rental_fee   weapon_rental_fee_early
              afterparty_fee      afterparty_fee_early     (legacy fixed fees)
```

Discounts are excluded — they only reduce a total, so they cannot make a free
tournament charge.

*Consequence*: completeness now depends on price values, not merely on their
presence, so a tournament can move from complete to incomplete when someone sets
the first nonzero price. That is the correct behaviour — the moment it can charge
is the moment it needs somewhere to be paid — but it means the `PAYMENTS` tab's
marker can appear as a result of an edit on `DISCIPLINES`. The marker mechanism
already recomputes from `setup_missing()` on every save, so this needs no new
wiring; it does need a test.

*Consequence*: a published free tournament that later adds a priced discipline is
refused that save by `guard_published_completeness` until a bank account is
supplied. This is right, and the refusal names `bank_account`, so the message is
actionable.

### Decision 3 — The frontend stops deciding whether payment is due

The current bug is a duplicated predicate that drifted. Correcting the duplicate
would fix today's symptom and leave the drift class intact — the next change to
team or substitute semantics reopens it.

Instead the frontend stops asking. `PaymentPanel` renders unconditionally for a
`RESERVED` registration, fetches, and renders whichever of four outcomes it gets:
instructions, "nothing is due yet — every place you asked for is queued", "no
payment details are configured", or a generic failure. `TournamentDetail`'s
`fullyQueued` computation and its `registration.fullyQueuedHint` branch are
deleted; the hint's text moves into the panel's `no_payment_due` state.

The backend becomes the only place that knows the rule, which is where the rule is
already correctly written and commented.

*Consequence*: the "all queued" hint now costs a round trip instead of rendering
from data already in hand. Accepted — it is one small authenticated GET on a page
that has already made several, and it buys the elimination of a class of bug that
has now shipped once.

*Alternative considered*: returning a `payment_due: bool` on `RegistrationOut` so
the frontend can branch without a second call. Rejected as a wider API change for a
latency problem nobody has reported; it also re-creates the two-places problem in a
new form.

### Decision 4 — Already-published tournaments are reported, not migrated

`guard_published_completeness` fires on save. A tournament published before this
change with no bank account stays published, keeps taking registrations, and keeps
failing silently — the gate cannot reach backwards, and this is the state the
reporting organizer is in right now.

There is no correct automatic repair: a bank account cannot be invented. So the
change ships a one-shot report (a short script under `backend/`, in the style of
the existing operational scripts) listing published tournaments with no bank
account, to be run once after deploy. Fixing them is a manual Setup edit, which the
new section makes possible.

*Alternative considered*: refusing new registrations on such tournaments until
repaired. Rejected — it converts a silent failure for some fencers into a hard
closure for all of them, and the publish gate plus the report cover the case
without that.

### Decision 5 — `bank_account` moves out of `ParamPanel` onto the `PAYMENTS` tab

Setup already has a `PAYMENTS` tab — `setup-navigation` allocates it the currency
and exchange-rate section, the VS series statement, and the discount list, and
`SetupPanel.tsx:113-120` renders exactly those. It is where an organizer already
looks for money settings, and it is missing the one field that makes money
collectable.

`bank_account` is configuration completed before opening, not a parameter tuned
during reconciliation, and leaving it in both places creates two editors for one
value. It is removed from `PHASE_PARAMS.payments` and appears in a new
`setup/BankAccountSection.tsx` on that tab, first — the account precedes the
currency it is denominated in.

The remaining six payments params (`reservation_validity_days`, `reminder_day`,
`amount_tolerance_percent`, `refundable_until`, `expiry_grace_hours`,
`amendments_close`) stay in the console rail. They are operational, and moving them
would pull tolerance and grace away from the queue where the organizer reads their
effect.

*Note*: this section is also where a deposit amount and payment deadline would land
if that change proceeds. It is being created one field wide on purpose.

## Risks / Trade-offs

- **A publish gate on a field organizers have never been asked for** → Every
  tournament published before this change is unaffected until its next save; the
  gate applies to new publications. The report (Decision 4) covers the rest.
- **Decision 2 unresolved blocks task 1.2** → Named explicitly in the tasks so the
  work stops rather than guessing. Everything else in the change is independent of
  it.
- **Deleting `fullyQueuedHint`'s branch touches a shipped fencer-facing string** →
  The i18n key moves rather than being dropped, so the Czech translation is
  preserved rather than re-authored.
- **The extra GET for a fully queued registration** → Decision 3; accepted and
  argued there.
- **No frontend tests** → Verified by typecheck, build, and driving a registration
  through each of the four panel states against a seeded tournament.

## Migration Plan

No schema change, no migration, no data backfill. The only persistent effect is
that publication now requires one more field. Rolling back is reverting the
`setup.py` condition — tournaments published under the gate remain valid, since
having a bank account is never a problem.
