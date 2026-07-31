## Why

VS allocation and VS lookup disagree about scope. `next_vs` takes `max(Registration.vs) + 1` across **every tournament in the deployment**, while matching resolves a VS only within the tournament being processed. Two tournaments sharing one bank account — the normal case for an organizer running a spring and an autumn event — therefore each poll the same account, ingest each other's transactions, and drop them into their own unmatched queue as `unknown_vs`. Every organizer manually triages traffic that belongs to a sibling event, and nothing in the console tells them that is what they are looking at.

The allocation is also racy. `max(vs) + 1` lets two concurrent registrations read the same maximum; the unique constraint on `Registration.vs` now catches the collision, but there is no retry, so the second registration fails with a server error instead of taking the next number.

Separately, the owner wants a VS that is legible on a bank statement: `YYNNnnn` — year, the tournament's ordinal within that year, and the registration's sequence within the tournament. `2605003` reads as the third registration to the fifth tournament of 2026. Today's `1000001`-and-up counter carries no information at all.

## What Changes

- Newly issued variable symbols take the structured form `YYNNnnn`: two digits of the tournament's year, two digits of its series within that year, three digits of registration sequence within the tournament.
- `Tournament` gains a VS series (`NN`) and the year it belongs to, derived from the **tournament date**. The series is auto-assigned at creation as the lowest free value for that year, is unique within the year, and is editable in Setup only until the tournament's first registration exists — after which the prefix is frozen and a later date change does not renumber anything.
- **The prefix is documentation, not routing.** Matching resolves a registration by looking the complete VS up in a global unique index and derives the tournament from the resolved row. It never parses `YY` or `NN` to choose a tournament — a payer's single mistyped digit would otherwise route money into a sibling event's reconciliation.
- VS lookup in matching becomes global. A transaction whose VS resolves to a **different** tournament's registration is recorded as belonging elsewhere and disappears from this tournament's unmatched queue, with no payment, no email, and no state change. The owning tournament's own ingestion matches it. The console reports how many such transactions were parked so an organizer can tell "nothing to do" from "nothing happened".
- Sequence allocation becomes per-tournament and race-safe: an atomic counter increment on the tournament row, with the existing unique constraint on `Registration.vs` as a backstop and a bounded retry.
- Allocation fails loudly on overflow rather than wrapping or colliding: a 100th tournament in one year, or a 1000th registration to one tournament, is refused with a clear message.
- **Existing VS values are never rewritten.** Payment instructions and QR codes are already in fencers' inboxes; legacy sequential VS keep matching because lookup is a plain global index hit. Only newly issued VS use the structured format.

## Capabilities

### New Capabilities

None. Both affected areas are existing capabilities.

### Modified Capabilities

- `payments`: MODIFIED `Payment identity via variable symbol` — the `YYNNnnn` format, deployment-wide uniqueness, global lookup with the tournament derived from the resolved registration, the explicit prohibition on parsing the prefix for routing, legacy VS compatibility, and the handling of a transaction whose VS belongs to a sibling tournament on the same account.
- `tournament-admin`: ADDED `Variable symbol series` — the series and its year, auto-assignment as the lowest free value, uniqueness within a year, the freeze once a registration exists, and overflow refusal.

## Impact

**Backend.** `models.py`: `Tournament.vs_year`, `Tournament.vs_series`, `Tournament.vs_next_seq`, a unique constraint on `(vs_year, vs_series)`; `Registration.vs` already carries `unique=True` and needs no change. One Alembic revision assigning a series to every existing tournament from its date year in a deterministic order, **without touching a single issued VS**. `routers/registrations.py`: `next_vs` is rewritten from a global maximum to a per-tournament atomic counter — note that CH-01 (`fix-reservation-lifecycle`) also touches this function to document why re-registration issues a fresh VS. `routers/tournaments.py`: series assignment at creation, the freeze check on update, and the overflow refusal. `matching.py`: the VS lookup drops its `tournament_id` predicate and gains the sibling-tournament branch before the existing unknown-VS path. `bank.py` keeps its per-tournament ingestion — statement provenance stays with the console that fetched it.

**Frontend.** `SetupPanel.tsx`: the series field, shown read-only once registrations exist, with the resulting VS prefix displayed so the organizer can see what payers will quote. `MatchPanel.tsx`: the parked-transaction count. `schemas.py` and i18n cs/en for both.

**Risk of collision with legacy values.** `VS_START` is `1000001`, so legacy VS occupy `1000001` upward and would need roughly 1.6 million registrations to reach the structured range, which begins at `2600000` for 2026. The two ranges cannot meet in practice; the unique constraint covers the theoretical case.

**Sequencing.** Independent of CH-01 — the two changes touch `next_vs` and `matching.py` in different places and can land in either order, though CH-01 is already in implementation. The later payment-matching-hardening change depends on this one: its bare-number VS matching is safe only because a structured 7-digit VS with a known prefix rarely collides with an invoice number or a date.
