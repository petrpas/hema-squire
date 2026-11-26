## Context

A payment on an expired reservation outside grace is flagged in
`matching._evaluate_single_vs` (`expired_outside_grace` / `expired_seat_taken`)
and appears only in Payments → Nepřipsané. The registration's row in Payments →
Registrace is drawn by `StateCell`, which falls back to `StateBadge`; for an
expired row holding credit, `StateBadge` already prints "Vypršela s platbou"
from the row's `held_amount` / `held_currency` (`sheet.py`). A flagged payment
leaves no trace on the row at all. Owner decisions of 2026-11-26 fix the label,
the scope (expired only, both cases) and the link-and-mark behaviour.

## Goals / Non-Goals

**Goals:**
- The organizer reading the registration table sees which expired registrations
  have money against them, and gets to that money in one press.

**Non-Goals:**
- Cancelled registrations (not drawn by the sheet; refund is already on the
  payment's row).
- Mail to the organizer; actions in Fronta or Týmy; an Agenda tab.
- Any change to matching, reinstatement or what counts as paid.

## Decisions

**D1. The row states where its late money lies; the client does not join.**
The sheet projection adds, for an expired registration, `late_payment`:
`{table: "uncredited" | "credited", key, amount, currency, day, count}`. `key`
is the transaction id for the uncredited table, and the credited table's own
address `(source_kind, source_id)` for held credit. Alternative: let the console
match rows of `/uncredited` to sheet rows by VS. Rejected — the two lists load
independently, the registration table would draw a stamp that depends on a
table that may not have loaded or may have failed, and the resolution of a
flagged payment to a registration already has one server-side answer
(`_flagged_registration`) that the reinstate action uses.

**D2. Flagged payments are resolved to registrations the way the reinstate
action resolves them.** One read per projection of the tournament's
transactions with status `flagged`, reason in `{expired_outside_grace,
expired_seat_taken}` and no live credit, each mapped by `matching.effective_vs`
to its registration. Using the same resolution means the stamp leads to exactly
the rows on which the reinstate action is offered. Most recent first by
transaction date then id; `count` is how many.

**D3. Held credit points at the latest live credit entry.** `held_amount`
already sums it; the link needs one payment to arrive at, and the most recent
live entry on the registration is the one most likely to be the question.

**D4. The stamp lives in `StateBadge`, the link in the Payments phase only.**
`StateBadge` gains the muted stamp for a row carrying `late_payment` or
`held_amount`, replacing today's "Vypršela s platbou" word. It is wrapped in a
button only where a handler is supplied, which the Payments phase's
`StateCell` does; other phases draw the stamp without the link, since the money
tables live in Payments. Alternative: stamp only on Payments. Rejected — the
same row would then read "Vypršela s platbou" in one phase and "Pozdě" in the
next for the same fact.

**D5. Muted ink by a modifier, no new token.** `.stamp-paid.stamp-muted` sets
border and text to `--ink-faded`, an existing token, so no hex leaves
`tokens.css` and `--stamp` stays the only saturated colour. Rotation is kept
from `PaidStamp` so it reads as the same kind of mark.

**D6. Arrival is a selection in the console, not a URL.** `Console` holds
`arrivedAt: {table, key} | null`. Pressing the stamp sets the payments tab and
`openTab` to that table and `arrivedAt` to the key; the table marks the row with
`aria-current="true"` and a `--paper-shade` ground, and scrolls it into view
once on mount (`scrollIntoView({block: "center"})`, no smooth behaviour, no
animation). `arrivedAt` is cleared when `openTab` changes. Alternative: a query
parameter. Rejected — nobody shares a link to "the row I arrived at", and a
parameter would outlive the reading it serves.

## Risks / Trade-offs

- [A flagged payment whose only VS is a bare token resolves to no registration
  through `effective_vs`] → it gets no stamp, exactly as it gets no reinstate
  action today; it still sits in Nepřipsané. Not widened here.
- [The projection reads flagged transactions on every sheet render] → one
  indexed select per tournament, normally returning nothing.
- [Export or tables reading `state` text] → unchanged; the stamp is display of
  the same `expired` state, and the row's `state` value does not change.
