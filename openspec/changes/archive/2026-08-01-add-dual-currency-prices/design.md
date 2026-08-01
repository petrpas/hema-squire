## Context

Verified against `main`:

- Prices live in `Discipline.fee` / `fee_early`, `ExtraItem.price`, the legacy `Tournament.weapon_rental_fee` / `afterparty_fee` pairs, and fixed-amount effects inside the `Tournament.discounts` JSON. All are integers in the tournament's `primary_currency`.
- `pricing.to_eur(amount, tournament)` divides by `tournament.eur_rate`; `from_eur_cents` is its inverse. Every fencer-facing EUR figure and the matching conversion funnel through them.
- `Registration.total_amount` is stored — computed once at registration and again on amendment. `matching.py` compares against `outstanding_cents`, derived from that stored total, so **reconciliation already does not recompute prices**.
- `pricing.registration_total()` reads `Discipline.fee` **live** and pins only the early-bird date to `registered_at`. Amendment calls it, so a price edit reaches anyone who subsequently amends.
- `Currency` is a closed enum of `CZK` and `EUR`, documented as singling EUR out because it is "the one currency the system can also convert to".

The convention that matters here is determinism: totals are a pure function of inputs and the pilot replay must reproduce historical figures. Two stored prices satisfy it more strongly than one price and a mutable divisor.

## Goals / Non-Goals

**Goals:**

- Both prices are decisions the organizer makes, and both are stored as typed.
- No exchange rate is read anywhere in the path from quote to reconciliation.
- An organizer filling the form gets arithmetic help without that help becoming a source of truth.
- Existing tournaments keep working, with EUR figures within rounding of what they show today.

**Non-Goals:**

- More than two currencies. A tournament prices in its local currency and optionally in EUR; a third is out of scope (Decision 6).
- Pinning unit prices per registration. The owner has decided that changing prices is permitted and that organizers will use the option responsibly; the warning is the mitigation (Decision 7).
- Aggregating payments across currencies. Two counters, no conversion between them (Decision 5).
- Improving payment matching generally — that is `harden-payment-matching`, which this change requires to be rebased.

## Decisions

### Decision 1 — Two prices per priced thing, both authoritative

| Column | Gains |
|---|---|
| `Discipline.fee`, `fee_early` | `fee_eur`, `fee_early_eur` |
| `ExtraItem.price` | `price_eur` |
| `discounts[].effect` where `kind == "fixed"` | `value_eur` |
| `Registration.total_amount` | `total_eur` |

All EUR columns are nullable, and `NULL` means "this tournament does not price in EUR". Percentage discounts are currency-neutral and gain nothing.

**The two totals will not reconcile at the rate, and must not be made to.** 800 Kč priced alongside 32 € is a 25.0 rate; 700 Kč alongside 28 € is also 25.0; but an organizer who prices 750 Kč / 30 € has chosen a 25.0 rate for that row and might price the next row at 26.0 without noticing or caring. Summed, the two totals imply some blended rate that equals nothing in particular. This is correct — it is the organizer's price list, not a conversion table. It should be stated in the spec so that nobody later files the discrepancy as a bug or "fixes" it with a consistency check.

Rounding stays exactly as it is: each currency's total is computed with the existing discount pipeline and rounded half-up to a whole unit exactly once, independently.

### Decision 2 — Currency mode is a tournament-level switch, and completeness falls out of it

Setup carries a currency mode above the price tables:

```
┌─ Currency ───────────────────────────────────┐
│  ( ) CZK only                                 │
│  (•) CZK + EUR      1 EUR = [ 25 ] Kč         │
│  ( ) EUR only                                 │
└───────────────────────────────────────────────┘

Disciplines                     CZK     EUR
────────────────────────────────────────────
Longsword Open                 [ 800]  [ 32]
Sabre Open                     [ 700]  [ 28]
                                  [recalculate missing]
```

Stored as `local_currency` plus the existing `eur_payments_enabled` flag:

| Mode | `local_currency` | `eur_payments_enabled` | EUR price columns |
|---|---|---|---|
| local only | CZK | false | NULL |
| local + EUR | CZK | true | filled |
| EUR only | EUR | false | NULL — `fee` already is EUR |

*Why this is better than the per-item completeness rule considered first:* if the mode renders two price columns, then "every price is filled" — the check that already exists — covers EUR completeness with no new rule and no separate error path. The organizer cannot end up with EUR half-configured, because the form does not offer that state.

*`primary_currency` is renamed to `local_currency`.* "Primary" implies a secondary derived from it, which is exactly the model being removed. The rename is mechanical and Alembic handles it; leaving the old name would leave the old mental model in the code for whoever reads it next.

*`eur_payments_enabled` keeps its name* — it still means precisely what it says.

### Decision 3 — The rate survives, demoted to a calculator

`Tournament.eur_rate` stays, and its meaning inverts: it is a Setup convenience, stored so it persists between editing sessions, and read by exactly one thing — a **recalculate missing** action that fills empty price inputs from filled ones, rounded half-up to whole units, in either direction.

Rules for the action, which matter because it is the only place the rate touches money at all:

- It fills **empty** fields only, and never overwrites a value the organizer typed. Typed prices are decisions; overwriting them is the behaviour this whole change exists to remove.
- It is explicit and manual — no recalculation on save, on rate change, or on blur.
- It runs client-side on the form. The rate is persisted so it is there next session, but nothing server-side consults it.

*The demotion must be recorded prominently in the model,* because a surviving column whose meaning has reversed is exactly what a future change re-wires by accident. `pricing.to_eur` and `from_eur_cents` are **deleted** rather than left unused, so there is no function available to reintroduce a conversion without writing one.

*Alternative rejected — drop `eur_rate` entirely and make the calculator a transient form field.* Purer, but the organizer would retype the rate every session, and a rate that is not stored cannot be shown back as "the ratio you have been pricing at".

### Decision 4 — Matching selects a total; it never converts

```
transaction currency == local_currency   → compare against total_amount
transaction currency == EUR, EUR enabled → compare against total_eur
otherwise                                → flagged, currency not accepted
```

That is the entire currency logic in the payment path. `paid_cents_in_primary` and the `currency_unconvertible` reason disappear; the reason becomes `currency_not_accepted`, which is both simpler and more accurate — the issue was never that the system could not convert, it was that nobody had priced in that currency.

The consequence worth stating: the ±5 % tolerance now absorbs only bank fees and payer rounding — things outside the organizer's control. It no longer has to cover foreign-exchange spread or the organizer's own rate edits, which is why it could previously be blown through without anyone doing anything wrong.

### Decision 5 — Two paid counters, never added together

`Registration.amount_paid_cents` (local currency, already implemented) gains a sibling `amount_paid_eur_cents`. A registration is settled when **either** counter covers its own total within tolerance.

Sums are never taken across currencies, because doing so would require a rate and put it straight back into the money path — the one thing this change buys. A fencer who pays half in CZK and half in EUR is a rare human situation and is flagged for a human.

This is deliberately the minimum needed to keep the model coherent now that there are two totals. Aggregation behaviour proper belongs to `harden-payment-matching`.

### Decision 6 — Two currencies, and EUR is structurally the second

The model is "local currency, optionally plus EUR", not "N currencies". A Polish organizer gets PLN + EUR by setting `local_currency` to PLN once the enum is widened; a Czech organizer wanting CZK + EUR + PLN is not supported.

This is a real door being closed and it is worth closing knowingly. EUR is genuinely privileged in this domain — it is the cross-border currency for European HEMA — and a general N-currency model (a price table keyed by currency, a JSON map per item) costs typed columns, validation, and query simplicity to serve a case nobody has asked for. Widening later means adding columns or migrating to a map, which is a bounded change.

### Decision 7 — Prices stay editable; the warning states the real mechanism

Per the owner: organizers may change prices, and the system assumes the option is used responsibly rather than preventing its misuse. Unit prices are **not** pinned per registration.

The warning shown when registration is open must therefore describe what actually happens, which is not what it might appear to be:

```
Changing prices on a tournament with open registration

  · fencers already registered keep the amount they were quoted
  · a fencer who later amends is repriced at the new prices
  · new registrations use the new prices

  Changing prices mid-registration is bad practice. Continue?
```

Both first two lines are load-bearing and both are verified in code. `total_amount` is stored, so no existing quote moves and **payment reconciliation is unaffected** — the concern that pairing becomes imprecise does not hold, because matching compares against the stored total, not a recomputed one. But `pricing.registration_total()` reads `Discipline.fee` live, so a fencer who amends after a price rise has their whole registration repriced, not just the part they added. Under the archived `fix-reservation-lifecycle` behaviour, a *paid* fencer in that position receives a surcharge demand.

The warning is the agreed mitigation. It earns its place only by being accurate about which of those two things happens.

### Decision 8 — Mode switching retains prices

Switching from local + EUR to a single-currency mode hides the EUR price column but keeps the stored values; switching back reveals them unchanged. Nothing is cleared.

This departs from the existing rule that disabling EUR payments clears the stored rate, and deliberately so: clearing one number the organizer can retype in seconds is not the same as discarding forty prices they entered by hand. The rate keeps its existing clear-on-disable behaviour or not, as convenient — it is now only a calculator setting either way.

### Decision 9 — Legacy fixed fee parameters stay single-currency

`Tournament.weapon_rental_fee`, `weapon_rental_fee_early`, `afterparty_fee`, and `afterparty_fee_early` gain no EUR counterparts. They exist so pre-itemized tournaments keep reproducing their historical totals; those tournaments predate EUR support entirely and will never enable it.

A tournament that still uses them therefore cannot enable EUR mode, and the setup checklist says so, naming the fixed parameters and pointing at itemized extra services as the route. This saves four columns that would be `NULL` forever and avoids extending a legacy path that exists only to be frozen.

## Risks / Trade-offs

**The two totals imply no single rate.** → By design (Decision 1), stated in the spec so it is not later "corrected". A consistency check between them would be a bug, not a feature.

**Backfilled EUR prices shift quoted figures slightly.** → Existing EUR-enabled tournaments have their EUR prices derived once from the current rate and rounded to whole units, so a fencer currently quoted 68.63 € may see 69 €. Bounded by half a unit per item, well inside tolerance, and it happens once. Alternative — leaving EUR prices NULL and disabling EUR until the organizer fills them — would break a live tournament to avoid a rounding shift.

**Amendment reprices at current prices.** → Owner-accepted (Decision 7); the warning is the mitigation and states it explicitly.

**`harden-payment-matching` describes a conversion step that will not exist.** → It is unstarted at 0/70; rebase before implementing it. This change deliberately keeps its own `Amount tolerance` edit minimal so the rebase is mechanical.

**The rename touches many call sites.** → `primary_currency` → `local_currency` is mechanical and compiler-invisible in Python, so it must be done by search. Grouped into one task so it is not spread across the change.

**A future change re-wires the rate.** → `to_eur` and `from_eur_cents` are deleted, not deprecated, so reintroducing conversion requires writing the function back and noticing why it was removed.

## Migration Plan

1. One Alembic revision: rename `tournaments.primary_currency` to `local_currency`; add `disciplines.fee_eur`, `disciplines.fee_early_eur`, `extra_items.price_eur`, `registrations.total_eur`, `registrations.amount_paid_eur_cents`, all nullable.
2. Data step, for tournaments with `eur_payments_enabled` and a positive `eur_rate` only: derive each EUR price as the local price divided by the rate, rounded half-up to a whole unit; derive `total_eur` per registration the same way from `total_amount`. Everything else stays `NULL`.
3. Data step for `discounts`: add `value_eur` to fixed effects on those tournaments, derived the same way. Percentage effects untouched.
4. Document in the revision that these EUR figures are a one-time derivation from the rate, are approximations of what was previously displayed, and are authoritative prices from that moment on.
5. Verify on a copy of `backend/hema_squire.sqlite`: every EUR-enabled tournament has complete EUR prices, no CZK-only tournament gained any, and a sample of registrations renders EUR totals within one unit of what they render today.
6. Rollback drops the added columns and reverses the rename. EUR prices typed by organizers after the deploy would be lost, so rollback is only safe immediately after deploy — note this in the revision.

## Open Questions

- **Should `recalculate missing` also offer an overwrite-all variant?** Fill-empty-only is the safe default and the one specified. An organizer repricing a whole tournament might want "recompute every EUR price from the local ones", which is a different and more dangerous action.
- **Widening `local_currency` beyond CZK and EUR.** PLN and HUF are the obvious next entries and the enum is designed for it, but nothing in this change adds them.
- **Whether the price-change warning should be gated on anything narrower than "registration is open"** — for example only when a discipline with existing registrations is repriced. Broader is safer to start.
- **Mixed-currency partial payments** (Decision 5) are flagged for a human with no aggregation. Whether that is ever worth more machinery depends on whether it happens at all.
