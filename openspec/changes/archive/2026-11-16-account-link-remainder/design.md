## Context

`matching.apply_payment_links` replays every active `payment_link` rule. For each, it walks the named registrations, credits `min(outstanding, remaining)` to each payable one, then marks the transaction `matched` / `manual_link` unconditionally. The loop never credits what is left, and never asks whether it credited anything. `routers/payments.link_transaction` creates the rule and calls the replay.

## Goals / Non-Goals

**Goals:** the link's credits sum to the transaction; a link crediting nothing never resolves a transaction.

**Non-Goals:** repairing links applied before this change (their remainder was never written; the reconciliation already shows the gap); multi-VS automatic links (they only fire when the sum matches within tolerance, and go through the same replay).

## Decisions

### D1. The last payable registration takes the remainder

Collect the payable registrations first (`_is_payable`, in rule order). Credit each but the last `min(outstanding, remaining)`; credit the last `remaining`. `_settle` already decides overpayment from the lane balance after the credit — refund state, event and mail are the same as for a VS overpayment, so nothing new is needed there.

Alternative considered: an "unallocated" amount carried on the transaction. Rejected by the owner: a new state and console surface for what refund tracking already handles.

### D2. A link that credits nothing does not resolve

If the currency is not taken or no registration is payable, `apply_payment_links` skips the rule without touching the transaction. `link_transaction` checks the same two conditions before creating the rule and raises `409 nothing_payable` (`currency_not_accepted` stays its own reason where the currency is the cause). Pre-checking at the endpoint rather than detecting "applied 0" afterwards keeps the rule from being written at all. `matching.link_refusal` answers it once; confirming a name-assisted proposal goes through the same link path and asks it too.

The link dialog used to read every 409 as "a concurrent poll matched this first" and close itself. The two refusals are told apart by their detail and keep the dialog open with the reason.

`test_payments_console` held a test of the console showing such a pairing as `paired_uncredited`. Reached through the endpoint, that pairing is now refused; the test asserts the refusal. The disposition stays for rules that find nothing payable on a later replay.

## Risks / Trade-offs

- [The organizer meant the remainder for a different registration] → they withdraw the link and relink with the order they want; the last named one takes the remainder, which the dialog's order makes visible.
- [A rule recorded before this change now replays differently] → replay skips already-matched transactions, so only a transaction re-ingested after a clear sees the new distribution — the correct one.
