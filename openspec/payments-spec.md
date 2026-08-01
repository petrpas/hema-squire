# Change Analysis — Reservation Lifecycle, Payment Identity, Multi-Currency

**Audience:** Claude Code, working the OpenSpec `spec-driven` workflow in `petrpas/hema-squire`.
**Input state:** `main`, backend snapshot as reviewed. All line references are to that snapshot — re-verify before editing.
**Output:** four OpenSpec changes under `openspec/changes/`, proposed and implemented in the stated order. Do not merge them into one change; they have different risk profiles and CH-01 must ship first.

---

## 0. Method and scope

This analysis audits the pre-tournament payment path — registration → reservation → bank transaction → confirmed registration — against the current specs in `openspec/specs/{registration,payments,tournament-admin}/spec.md` and the implementation in `backend/app/`.

The specs are broadly sound. The registration spec already encodes per-reservation windows instead of a global deadline, VS-only matching, capacity held by unexpired reservations, a substitute queue, and a refundable-until date. This analysis is **not** a redesign of that model. It covers three classes of defect:

1. **Lifecycle dead ends** — states a registration can enter and never leave (CH-01).
2. **Payment identity** — VS generation and lookup scope (CH-02).
3. **Currency correctness** — an assumed feature that does not exist in the code (CH-03).
4. **Matching robustness** — cases that fall through to manual work unnecessarily (CH-04).

Each change below is written to be turned into `proposal.md` / `design.md` / `tasks.md` / spec deltas by the normal `openspec-propose` skill. The "Spec deltas" sections name the capability and the requirement to add or modify; write them as full `### Requirement:` blocks with `#### Scenario:` in the delta, per repo convention.

---

## CH-01 — `fix-reservation-lifecycle`

**Priority: ship first.** Two of these are live defects that will bite at the first real tournament.

### Finding 1.1 — An expired reservation permanently locks the fencer out

`backend/app/routers/registrations.py:211-218`:

```python
existing = session.scalar(select(Registration).where(
    Registration.tournament_id == tournament.id,
    Registration.fencer_id == fencer.id,
))
if existing is not None and existing.state != RegistrationState.CANCELLED:
    raise HTTPException(status_code=409, detail="already_registered")
```

Only `CANCELLED` is exempt. A reservation that expires unpaid leaves the row in `EXPIRED`, so the fencer receives `409 already_registered` forever and has no path back into the tournament — not even while seats are open.

This contradicts the intent of the reservation model. The short window exists so that an unpaid hold is released cheaply and the fencer can come back when they have decided; permanent exclusion is a punishment the spec never asks for. `openspec/specs/registration/spec.md` ("Reservation lifecycle") says only that an expired reservation frees its capacity — it is silent on what the fencer may do next, which is why the gap slipped through.

**Required behaviour:** `EXPIRED` SHALL be re-registerable on the same terms as `CANCELLED` — the existing row is reused in place (the `(tournament_id, fencer_id)` unique constraint forbids a second row), a fresh window opens, and a fresh VS is issued. Capacity is re-checked at that moment like any new registration; if the discipline filled meanwhile, the fencer enters the substitute queue.

Consider whether repeated expiry should be limited (e.g. after N expired cycles the fencer may only join as a substitute) to stop one account from cycling a scarce seat. Recommendation: **do not add a limit in this change** — the seat is only held for the window length and the reminder/expiry emails already create friction. Note it as a deferred decision in `design.md`.

### Finding 1.2 — No way to amend a registration

`backend/app/routers/registrations.py` exposes `register`, `my_registration`, `my_registration_payment`, `cancel_registration`, `admit_substitute`. There is no amendment endpoint, and `openspec/specs/registration/spec.md` has no requirement for one.

A fencer who wants to add an afterparty ticket or a second discipline after registering has exactly one path: cancel and re-register. That path is destructive — `registrations.py:242-247` resets `paid_at = None`, `refund_state = NOT_APPLICABLE`, and line 254 assigns a **new VS**. So a fencer who has already paid and then amends loses the association with their payment, and after `refundable_until` they are formally expected to pay a second time. The already-issued QR code now points at a dead VS.

This is also a second-order cause of the original business problem. If the selection cannot be changed after payment, the rational move for the fencer is to delay payment until they are certain — exactly the behaviour the reservation model was built to stop.

**Required behaviour:** an amendment endpoint on the fencer's own registration that recomputes the total from the current pricing rules and branches on state:

- **`RESERVED`** — replace the selection in place, recompute the total, **keep the VS and the existing `expires_at`** (amending must not extend the hold; otherwise the window is trivially renewable), reissue the confirmation email with the updated QR and amount.
- **`PAID`, new total > paid amount** — record the surcharge as an amount due against the same VS, keep the registration `PAID`, and email payment instructions for the difference. Do not revert the registration to `RESERVED`.
- **`PAID`, new total < paid amount** — record an overpayment on the registration and route it into the existing refund tracking (`refund_state`); the organizer settles it manually, consistent with the current refund policy.
- Adding a discipline that is at capacity SHALL add that discipline as a substitute entry rather than rejecting the whole amendment.
- Amendment SHALL be refused once registration for the tournament is closed, and SHALL be refused for `CANCELLED` / `EXPIRED` (those go through re-registration per 1.1).

The partial-amount tracking this needs overlaps with CH-04's payment aggregation. Implement the aggregation in CH-04 first if the sequence allows, or model the amount-due field here and let CH-04 consume it — either order works, but they must agree on one representation of "how much is still owed on this VS". State the chosen representation in `design.md`.

### Finding 1.3 — A payment landing on an expired or cancelled reservation has no resolution path

`backend/app/matching.py:87-95` flags a transaction whose VS resolves to a non-`RESERVED` registration:

```python
if registration.state != RegistrationState.RESERVED:
    _finish(transaction, "flagged", f"registration_{registration.state.value}")
```

The flagging itself is correct — the money must not be silently absorbed. But `openspec/specs/payments/spec.md` has no requirement or scenario covering it, and the organizer has no action to take: the console's manual-matching tools link an unmatched transaction to a *reserved* registration (`matching.py:apply_payment_links` skips anything not `RESERVED` at line 152). So the transaction sits flagged, the money sits in the account, and the fencer believes they paid.

This happens at every tournament: a payment sent on the last day of the window and credited the next morning, or a bank that batches overnight.

**Required behaviour:**

- A grace rule: a VS-matched payment arriving within a configurable grace period after expiry (`Tournament.expiry_grace_hours`, default 48) SHALL reinstate the reservation and mark it paid **if the discipline still has a free seat**. Reinstatement is audited as its own `PaymentEvent` kind.
- Outside the grace period, or when the seat is gone, the transaction SHALL stay flagged and the organizer SHALL have two explicit console actions on it: *reinstate* (where capacity allows) and *mark for refund* (recording the amount against the fencer for manual settlement).
- The fencer SHALL be notified in both directions — reinstated, or "payment received but the reservation had expired, the organizer will contact you". Do not leave the fencer with only the earlier expiry email.
- Payments landing on a `CANCELLED` registration SHALL go straight to the refund path, never reinstate.

### Spec deltas — CH-01

- `registration` — MODIFIED `Reservation lifecycle`: expired reservations are re-registerable; scenario for re-registration after expiry, and for re-registration when the seat has since filled (→ substitute queue).
- `registration` — ADDED `Registration amendment`: the state branching above, with scenarios for reserved-amend (VS and expiry preserved), paid-amend-upward (surcharge due, stays paid), paid-amend-downward (overpayment to refund tracking), and amend-into-a-full-discipline.
- `payments` — ADDED `Payments arriving after expiry`: grace reinstatement, organizer actions outside grace, fencer notification, cancelled-registration handling.
- `tournament-admin` — MODIFIED `Payment and reservation parameters`: add `expiry_grace_hours` to the configurable set.

### Impact — CH-01

`models.py` (grace column on Tournament; amount-due / overpayment representation on Registration; new `PaymentEvent` kinds), Alembic revision, `routers/registrations.py` (re-registration guard, amendment endpoint), `matching.py` (grace branch, capacity check on reinstatement), `routers` for the console payment actions, `emails.py` + `locales` (amendment confirmation, reinstatement, expired-but-paid notice), `schemas.py`, frontend `MatchPanel.tsx` / `FencerHome.tsx` / `TournamentDetail.tsx`, i18n cs/en.

### Tests — CH-01

New: re-registration after expiry (seat free → reserved; seat taken → substitute); amendment in each state branch; VS and `expires_at` stability across a reserved amendment; payment inside grace reinstates; payment outside grace stays flagged and offers organizer actions; payment on cancelled goes to refund. Existing `test_registration_gating.py` and `test_registrations.py` will need updating where they assert the current 409 behaviour.

---

## CH-02 — `add-structured-vs`

### Finding 2.1 — VS is globally sequential but matched tournament-scoped

`routers/registrations.py:59-61` allocates `max(Registration.vs) + 1` across **all** tournaments, while `matching.py:78-83` resolves a VS only within the tournament being processed. Two tournaments sharing one bank account therefore put each other's transactions into their own unmatched queue with `unknown_vs`, and the organizer manually triages traffic that belongs to a sibling event. `bank.ingest` is likewise tournament-scoped, so the same transaction is stored twice under two `tournament_id`s.

`max(...) + 1` is also racy: two concurrent registrations can read the same maximum. There is no unique constraint on `Registration.vs` to catch it.

### Finding 2.2 — Owner decision: structured VS `YYNNnnn`

The owner specifies a structured VS: `YY` = year, `NN` = tournament series within that year, `nnn` = registration sequence within the tournament. Example `2605003` = 2026, tournament 05, registration 003.

Adopt it, with one constraint that must be explicit in the spec: **the prefix is documentation, not routing.** Matching SHALL resolve a registration by looking up the complete VS in a global unique index and SHALL derive the tournament from the resolved row. It SHALL NOT parse `YY`/`NN` to select a tournament — a payer's single mistyped digit would otherwise route money into a sibling event's reconciliation.

Format constraints to state in the spec:

- 7 digits, well inside the Czech 10-digit VS limit and the SPAYD `X-VS` field.
- `nnn` caps a tournament at 999 registrations; `NN` caps a year at 99 tournaments. Both are comfortable for the domain, but allocation SHALL fail loudly on overflow rather than wrapping or colliding.
- No leading-zero hazard while `YY >= 26`; banks strip leading zeros from VS, so an all-numeric prefix beginning with a nonzero digit is required. Note this in `design.md`.

### Required behaviour

- `Tournament` gains a `vs_series` (the `NN`), assigned at creation as the lowest free series for the tournament's year, unique per year, editable in Setup **only until the tournament's first registration exists**.
- Sequence allocation is per tournament, race-safe: a unique constraint on `Registration.vs` plus insert-retry, or a per-tournament counter row updated under lock. Do not rely on `max() + 1` alone.
- VS lookup in `matching.py` becomes global; the resolved registration's tournament governs tolerance, currency, and grace settings. Ingestion may stay tournament-keyed for statement provenance, but a transaction SHALL be reconcilable against any tournament's registration.
- **Existing VS values are never rewritten.** Payment instructions and QR codes are already in fencers' inboxes. Legacy VS keep working because lookup is a plain global index hit; only newly issued VS use the structured format. Say this explicitly in the spec so no future change "tidies up" the old numbers.

### Spec deltas — CH-02

- `payments` — MODIFIED `Payment identity via variable symbol`: state the `YYNNnnn` format, global uniqueness and global lookup, prefix-is-not-routing, and legacy VS compatibility. Add a scenario for a transaction whose VS belongs to a sibling tournament on the same account (resolves to the correct tournament, not the unmatched queue).
- `tournament-admin` — MODIFIED `Tournament definition`: `vs_series`, its per-year uniqueness, auto-assignment, and the freeze after the first registration.

### Impact — CH-02

`models.py` (`Tournament.vs_series`, unique index on `Registration.vs`, per-tournament counter if chosen), Alembic revision with a backfill that assigns `vs_series` to existing tournaments without touching issued VS values, `routers/registrations.py` (`next_vs` rewrite), `matching.py` (global resolution), Setup UI + `schemas.py` for the series field, `SetupPanel.tsx`.

### Tests — CH-02

Format assertion on a newly issued VS; per-tournament sequence independence; series uniqueness within a year and reuse across years; overflow raises; concurrent registration does not produce duplicate VS; legacy sequential VS still matches; a transaction carrying tournament A's VS ingested while processing tournament B resolves to A.

---

## CH-03 — `add-multi-currency-payments`

### Finding 3.1 — The feature the owner expected is not in the repo

Multi-currency handling with an organizer-set exchange rate does not exist anywhere in the codebase or specs. Evidence:

- `Tournament` (`models.py:134-146`) has no currency and no rate column; prices are bare integers.
- `spayd.py:18` hardcodes `CC:CZK`, and the module docstring states outright that currency is CZK "until multi-currency enters scope".
- `matching.py:96-97` compares `transaction.amount_cents` against `registration.total_amount * 100` with no reference to `transaction.currency`. The currency string is ingested (`bank.py:25`, `:75`, `:100`, `:158`), stored (`models.py:316`), exported (`export_json.py:53`) — and never read by any decision.
- `backend/tests/test_matching.py:108-118` (`test_vs_in_message_matches_sepa_style`) imports a statement row of `1 000,00 EUR` and asserts `matched == 1` against a CZK amount due. The current test suite therefore **locks in** the defect: a EUR payment of the right numeral pays a CZK registration.

Today this fails safe only by accident — a realistic EUR amount against a CZK total is far enough out that the ±5 % tolerance rejects it. It fails *unsafe* whenever the numerals happen to be close, and it will fail systematically the moment a tournament prices in EUR.

### Required behaviour

- `Tournament` gains a **base currency** (`CZK` or `EUR` initially) — all item prices, discounts, and totals are denominated in it — and an optional **organizer-set exchange rate** for the other accepted currency, with the rate's effective date.
- The rate is organizer-set and stored, not fetched. It is a business decision, not a market quote, and it must be reproducible for audit: a registration's totals must recompute identically later. Snapshot the rate used onto the registration or the payment event rather than recomputing from the tournament's current rate.
- Payment instructions SHALL state the amount in the base currency and, when a rate is configured, the equivalent in the accepted foreign currency. SPAYD `CC` SHALL derive from the base currency rather than the current hardcoded `CZK`. Note in `design.md` that SPAYD is a Czech-domestic standard — for a EUR-based tournament the QR is a convenience for CZ-banked payers, not the primary instruction.
- Matching SHALL convert a transaction in an accepted foreign currency to the base currency at the tournament's configured rate **before** applying the tolerance comparison. A transaction in a currency that is neither the base nor the accepted one SHALL be flagged, never compared numerically.
- The ±5 % tolerance keeps its original job — absorbing bank conversion spread and fees around the organizer's rate — and is now applied to a correctly-denominated comparison rather than papering over a unit mismatch.

### Spec deltas — CH-03

- `tournament-admin` — MODIFIED `Pricing configuration`: base currency; ADDED `Currency and exchange rate`: accepted currencies, organizer-set rate, effective date, snapshot-for-reproducibility.
- `payments` — MODIFIED `Amount tolerance`: conversion precedes comparison; scenario for a EUR transaction against a CZK-priced tournament converting correctly; scenario for an unaccepted currency being flagged rather than compared.
- `registration` — MODIFIED `Confirmation email with QR payment` and `In-app payment instructions retrieval`: currency in the stated amount, foreign equivalent where configured, SPAYD `CC` from base currency.

### Impact — CH-03

`models.py` (`Tournament.currency`, `accepted_currency`, `exchange_rate`, `rate_effective_from`; rate snapshot on Registration or PaymentEvent), Alembic revision defaulting existing tournaments to `CZK` so historical totals are untouched, `spayd.py` (parameterised `CC`), `matching.py` (conversion step), `pricing.py` (currency-aware rounding — keep the single half-up rounding at the end), `emails.py` + locales, `schemas.py`, Setup UI, export paths.

### Tests — CH-03

**Rewrite `test_vs_in_message_matches_sepa_style` first** — it currently asserts the defect. Split it into: SEPA-style VS-in-message parsing (currency-neutral, base currency amount), and a separate EUR-against-CZK case that must convert at the configured rate. Add: no rate configured → foreign transaction flagged, not matched; unaccepted currency flagged; conversion + tolerance boundary at the tolerance edge; recompute reproducibility across a later rate change (snapshot honoured); legacy CZK-only tournaments byte-identical in totals and SPAYD output.

---

## CH-04 — `harden-payment-matching`

Lower priority, individually small, all reducing manual reconciliation.

### Finding 4.1 — Partial payments are never aggregated

`matching.py:96` compares a **single** transaction against the full amount due. Two transfers carrying the same VS — an installment, a correction after an underpayment, a bank that split the transfer, a payer covering a CH-01 amendment surcharge — each fail tolerance independently and both land flagged. The registration never becomes paid even though the account holds the full amount.

**Required:** matching SHALL evaluate the sum of all VS-matched transactions against the amount due (converted per CH-03). A registration becomes paid when the aggregate reaches the amount due within tolerance; below it, the reservation stays reserved with a recorded partial amount and the fencer is told the outstanding balance rather than being left to guess. The aggregate representation must be the same one CH-01's amendment surcharge uses.

### Finding 4.2 — Foreign VS parsing is narrower than the spec

`matching.py:23`:

```python
VS_IN_MESSAGE = re.compile(r"\bVS[:\s]*(\d{1,10})\b", re.IGNORECASE)
```

`openspec/specs/payments/spec.md` requires that ingestion "parse message fields for a VS". The implementation requires a literal `VS` token. A foreign payer following the instruction *"put 2605003 in the payment message"* writes a bare number and does not match. Only `column16` (zpráva pro příjemce) is read — Fio places SEPA references in other columns depending on the originating bank.

**Required:** parse all textual fields of the transaction, not just the message. Accept a bare numeric token when it matches a VS in the issued range; this is safe precisely because CH-02 makes the VS a structured 7-digit number with a known prefix, so accidental collisions with invoice numbers or dates are rare. A bare-number match MAY be treated as a candidate requiring organizer confirmation rather than an automatic match — decide in `design.md`, but do not leave it unparsed.

### Finding 4.3 — A single transfer covering several registrations is manual-only

`apply_payment_links` supports one transaction → many registrations, but only after the organizer builds the link by hand. A club paying for six members in one transfer is routine in this domain.

**Required:** when a transaction's text carries **several** VS values, the matcher SHALL treat it as a multi-registration payment candidate: if the sum of those registrations' amounts due matches the transaction within tolerance, mark all of them paid and record the equivalent of a payment link automatically. Otherwise present it as a pre-filled candidate in the manual matching UI rather than a bare unmatched row. This is a natural extension of the existing rules engine — the auto-created link SHALL be a removable rule like any manual one, so `unapply_payment_link` reverts it unchanged.

### Finding 4.4 — `reminder_day` is not validated against `reservation_validity_days`

`scheduler.py:run_tournament_tick` expires before reminding (correctly, and documented in the comment). But if an organizer sets `reminder_day >= reservation_validity_days`, the reservation is always expired before the reminder fires and no reminder is ever sent — silently. `models.py:135-136` defaults are 10 and 5, so the default is fine; nothing stops a bad edit.

**Required:** validate `reminder_day < reservation_validity_days` on tournament update, rejecting the combination with a clear message.

### Spec deltas — CH-04

- `payments` — MODIFIED `Amount tolerance` (aggregate across VS-matched transactions, partial balance recorded and communicated); MODIFIED `Foreign transfers without a VS field` (all textual fields, bare-number tokens in the issued range); MODIFIED `Manual matching` or ADDED `Multi-registration payments` (auto-detected multi-VS payments become removable rules).
- `tournament-admin` — MODIFIED `Payment and reservation parameters` (reminder day must precede expiry).

### Impact — CH-04

`matching.py` (aggregation, widened parsing, multi-VS detection), `bank.py` (expose all text fields on `IncomingTransaction`; check which Fio columns carry SEPA references before choosing), `rules.py` (auto-created payment links), `schemas.py` validation, `emails.py` + locales (outstanding-balance notice), `MatchPanel.tsx` / `MatchDialog.tsx` (candidate pre-fill).

### Tests — CH-04

Two half-payments with one VS aggregate to paid; a partial payment leaves the reservation reserved with the correct balance and notifies; bare numeric VS in a non-message field matches; a number outside the issued range does not; one transfer listing three VS values with a matching sum pays all three and creates a removable rule; removing that rule reverts all three; `reminder_day >= reservation_validity_days` is rejected.

---

## Sequencing and risk

| Change | Depends on | Risk | Note |
|---|---|---|---|
| CH-01 | — | Medium | Amendment touches pricing recompute; the reserved-amend path must not extend `expires_at` |
| CH-02 | — | Low | Additive; existing VS untouched. Migration must not renumber |
| CH-03 | CH-02 (nice, not required) | **High** | Rewrites a green test that encodes the defect; determinism/replay tests must stay green |
| CH-04 | CH-01 (shared amount-due representation), CH-03 (converted amounts) | Low | Each finding independently shippable |

CH-01 and CH-04 must agree on **one** representation of an outstanding balance on a VS. Fix that representation in CH-01's `design.md` and have CH-04 consume it.

CH-03 is the one to be careful with. `openspec/project.md` makes determinism a project convention — totals are a pure function of inputs, and the pilot replay must reproduce historical figures. Default every existing tournament to `CZK` in the migration and assert in tests that legacy totals and SPAYD strings are byte-identical before and after.

## Open questions for the owner

1. **Repeated expiry** — cap the number of re-registration cycles per fencer per tournament, or leave uncapped? Recommendation: uncapped for now, revisit with real data.
2. **Amendment window** — should amendment stay open until registration closes, or close earlier (organizer needs a stable roster to order t-shirts and book the afterparty)? A separate `amendments_close` date may be warranted; not assumed here.
3. **Bare-number VS matching** — automatic, or organizer-confirmed candidate? Affects how much manual work CH-04 actually removes.
4. **`vs_series` semantics** — this analysis reads `NN` as the tournament's ordinal within the year. If it was meant as the month, say so: two tournaments in one month would then collide and the sequence would have to absorb the difference.
   5. **Card payments** — deliberately out of scope everywhere in the specs. Confirm that stays true; a payment link would remove the entire reconciliation surface for foreign payers at roughly 1.5 % of the fee.