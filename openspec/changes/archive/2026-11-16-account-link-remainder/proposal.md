## Why

A payment link credits each registration it names up to what that registration owes, and whatever is left of the transaction is written nowhere: the transaction reads as matched, no registration is routed to refund, and the credits no longer add up to the statement (`openspec/payments_gaps.md`, P4). The same transfer quoting a variable symbol would have been credited whole and refunded as an overpayment. Worse, a link none of whose registrations can take money credits nothing at all and still marks the transaction matched, so the whole amount disappears from every queue.

## What Changes

- A link credits each registration it names what it owes, in the order named, and the **last registration that can take money takes everything left**. Beyond tolerance it reads as overpaid and is routed to refund, exactly as a VS overpayment is. What a link credits always adds up to the transaction.
- A link that would credit nothing — every registration it names settled, expired or cancelled, or the transaction in a currency the tournament does not take — is refused at creation with 409 `nothing_payable`, and the transaction stays among the uncredited.
- An existing link rule replayed later that finds nothing payable leaves its transaction uncredited rather than marking it matched.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `payments`: Manual matching — the link's distribution accounts for the whole transaction, and a link that credits nothing does not resolve it.

## Impact

- `backend/app/matching.py` (`apply_payment_links`), `backend/app/routers/payments.py` (`link_transaction`).
- Frontend: the link dialog surfaces `nothing_payable` in Czech and English.
- No data migration. Links already applied keep the credits they wrote; a remainder they lost stays visible only by comparing the transaction with its credits, as today.
