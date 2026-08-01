## Why

The system prices a tournament in one currency and derives the EUR figure by dividing by an organizer-set rate, live, every time it is shown or compared. That single derivation is the root of every EUR problem the project has accumulated: a rate edit silently moves what unpaid fencers owe, the emailed QR and the in-app QR can disagree, matching converts an incoming EUR transfer at a rate the payer never saw, and the ±5 % tolerance has to absorb foreign-exchange drift on top of the bank fees it was designed for.

None of that reflects how organizers actually work. In practice an organizer either publishes both prices — 800 Kč / 32 € — or publishes one and sticks to it. The two figures are both *decisions*, not one decision and one calculation. 32 € is not 800 Kč converted; it is the price in euros, chosen to be a round number a payer will recognize.

Modelling the second price as a derivation therefore encodes something untrue and pays for it everywhere. Storing both prices makes the exchange rate what it really is: a pocket calculator the organizer uses while filling in the form.

## What Changes

- Every priced thing gains a second, optional EUR price alongside its local-currency price: disciplines (standard and early-bird), and extra-service items. Both are authoritative; neither is computed from the other.
- Fixed-amount discounts gain a EUR amount. Percentage discounts are currency-neutral and are unchanged.
- A registration stores **both** totals, each summed from prices in its own currency. **BREAKING**: the EUR figure a fencer sees is no longer derived, so it is stable by construction — there is nothing left to snapshot, recompute, or re-quote.
- Setup gains a currency mode above the price tables — local only, local + EUR, or EUR only — which decides whether the price tables render one price column or two. Completeness follows from the form: two columns rendered means two prices required, covered by the existing "all prices filled" rule rather than a new one.
- **`eur_rate` survives with almost the opposite meaning.** It is demoted to a Setup convenience powering a *recalculate missing* action that fills empty price fields from filled ones, rounded to whole units. It is never read by pricing, matching, emails, or QR generation again.
- Matching compares a transaction against the total **in the transaction's own currency**. No conversion happens anywhere in the payment path. A transaction in a currency the tournament does not price in is flagged as not accepted, rather than converted at a rate and compared.
- Payment instructions and QR codes carry each currency's stored amount, with SPAYD `CC` taken from that currency.
- Switching currency mode retains stored prices rather than clearing them, so switching back reveals them again.
- Changing prices stays permitted. When registration is open the organizer is warned, in terms that state what actually happens: existing registrations keep the total they were quoted, a fencer who later amends is repriced, and new registrations use the new prices.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `tournament-admin`: MODIFIED `Tournament currency` — the three currency modes, the demoted rate, recalculate-missing, mode switching retaining prices, and the warning on price edits during open registration. MODIFIED `Pricing configuration` — a second price per item, per-currency fixed discounts, and two independently computed totals.
- `registration`: MODIFIED `Amounts presented in the tournament's currency` — EUR figures come from stored EUR prices, never from conversion. MODIFIED `Confirmation email with QR payment` and `In-app payment instructions retrieval` — each QR carries its currency's stored amount. MODIFIED `Price preview` — both totals returned, each summed in its own currency.
- `payments`: MODIFIED `Amount tolerance` — comparison is against the total denominated in the transaction's currency, with no conversion step and no rate.

## Impact

**Supersedes `snapshot-exchange-rate`,** which has been deleted. That change existed to make a derived EUR figure reproducible; a stored EUR price is reproducible by construction, so the problem is dissolved rather than solved. It also retires the argument over decision D3 of the archived `2026-07-30-registration-form-and-currency` change: D3 chose derived-never-stored for the EUR *amount*, and that instinct is preserved — the amount is still never stored as a derivation, because it is no longer a derivation at all.

**Requires rebasing `harden-payment-matching`** (proposed, 0/70, unstarted). Its `Amount tolerance` delta and its currency-conversion tasks describe a conversion step this change removes. Rebase it before implementing, not before merging this.

**Backend.** `models.py`: `Discipline.fee_eur`, `Discipline.fee_early_eur`, `ExtraItem.price_eur`, `Registration.total_eur`, `Registration.amount_paid_eur_cents`; `Tournament.primary_currency` renamed to `local_currency`; `eur_rate` retained and re-documented. Discount JSON gains `value_eur` on fixed effects. One Alembic revision, additive plus the rename, deriving initial EUR prices once from the existing rate so no live tournament breaks. `pricing.py`: a currency-parameterised total, and `to_eur` / `from_eur_cents` deleted. `matching.py`: the conversion step removed, replaced by selecting which stored total to compare against. `emails.py`, `spayd.py`, `routers/registrations.py`: each QR and amount from its own stored figure.

**Frontend.** `SetupPanel.tsx`: the currency mode box, the second price column, the recalculate-missing action, and the price-change warning. The registration form and fencer views read stored figures rather than converting. i18n cs/en.

**Legacy tournaments.** The fixed weapon-rental and afterparty fee parameters on `Tournament` do not gain EUR counterparts; they belong to pre-itemized tournaments that predate EUR support entirely. A tournament still using them cannot enable EUR mode, and the completeness checklist says so.
