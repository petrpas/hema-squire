## Context

`pricing.py` is a pure function of (tournament, selection, date): totals are stored,
but every amendment, promotion and lapse recomputes them from the current
configuration through `pricing.reprice`. Automatic discounts live in a JSON column,
`Tournament.discounts`, and are public: `TournamentOut` carries them to everybody.

Two pricing worlds exist. `uses_itemized_pricing` is true when a tournament has extra
items or discounts; anything else takes the legacy path, which is also where every
plain disciplines-only tournament lands, and which still bills the flat rental and
afterparty fees.

`Registration.settled` is derived. Its rule is that money or a waiver settles and
owing nothing does not (`models.py:1086`), and the payment window, the reminder pass
and the expiry pass all key on it. The row of a cancelled or expired registration
stays and is reused by a re-registration; a late payment can revive an expired one.

## Goals / Non-Goals

**Goals:**
- A private discount that reaches only those who were given the code.
- One pricing pipeline: previews, registrations, amendments, promotions, claims and
  Revenue all read the same evaluation.
- A limit that holds under concurrent registration.
- A registration a code covers in full keeps its seat with no action by anyone.

**Non-Goals:**
- Validity dates on a code. A code is retired by lowering its limit.
- Codes bound to a person, a club or an email address.
- Scoping to individual items; scope is by category, as automatic discounts have it.
- Organizer-side attaching of a code in the console, and removing or swapping one.
  Issued, hand-entered and imported registrations carry no code.
- Bulk generation of unique single-use codes.
- Codes on a manual tournament, which has no form to type one into.

## Decisions

### D1. Codes are a table, not more rows in `Tournament.discounts`

`DiscountCode` (tournament, `code`, `name`, `max_uses` nullable, `effect_kind`,
`value`, `value_eur`, `scope` JSON) with `unique(tournament_id, code)`.
`Registration.discount_code_id` is a nullable foreign key.

The JSON list is served to the public by `TournamentOut`, is positional, and offers
nothing to count against or lock. Filtering secret rows out of it at every reader
would be a leak waiting for one forgotten reader. **Alternative rejected:** a `kind`
flag on JSON rows.

Organizers reach codes through their own endpoints, so `TournamentOut` carries only a
boolean, `accepts_discount_codes`, which is what decides whether the form shows the
field.

### D2. The code joins the existing pipeline as one more discount

`_itemized_selection_breakdown` already applies all fixed effects and then all
percentage ones. The code is appended to the discounts it iterates, its condition met,
so that order follows with no new branch: automatic fixed, code fixed, automatic
percent, code percent (owner decision). A 500 Kč voucher under a −15 % early-bird
therefore costs the tournament 425 Kč, which is the stated consequence of that choice.

A fixed code's scope is every category; a percentage code's is every category or the
ones chosen. The fixed amount is per configured currency, like any fixed discount.

**The legacy path has to price a code too**, and a code must not flip a tournament
between worlds: letting `uses_itemized_pricing` see codes would silently stop billing
the flat rental and afterparty fees the moment an organizer added the first one. So
the discount loop is extracted to run over subtotals, and the legacy path builds its
subtotals (`discipline`, `rental`, `afterparty`) and runs the code alone over them.
`registration_breakdown`'s legacy branch must then return deductions as well, since it
returns none today.

The preview's contract that its breakdown holds one entry per configured discount,
and is empty when none is configured, stands untouched: the code's outcome is a
separate `applied_code` field on the preview and on the registration. This also leaves
the form's index-aligned `DiscountList` as it is.

`CategoryDeduction.position` indexes `Tournament.discounts`, which cannot name a code.
It gains `code_id`, and `exportrevenue` tallies code lines by it. Without this a code
would fall into the `index >= len(discounts)` guard and vanish from Revenue, leaving
blocks that do not sum.

### D3. Uses are derived; the last use is taken under a lock

Uses = live registrations (`state == RESERVED`) carrying the code. No counter to keep
right, and a cancellation or expiry gives a use back by leaving the count (owner
decision). The queue counts: a queued registration holds the code.

A code is checked twice. Early, for a clean refusal before anything is written. Then
in `discount_codes.claim`, in the transaction that commits the registration: it
updates the code's row, which takes the write lock on SQLite and the row lock on the
eventual Postgres, then counts with the registration included and refuses past the
limit. Two fencers racing for the last use are serialized and the second is refused
with nothing created. The amendment path uses the same `claim`.

**A revival is not a claim.** The foreign key stays on an expired or cancelled row, and
the stored total was quoted to the fencer who paid it, so a late payment brings the
registration back with its discount even if that makes the code read 11 / 10 (owner
decision). A re-registration is a new cycle: the key is overwritten by what the new
submission states, and a code is claimed afresh.

### D4. A total a code covers is a stored fact, and `settled` reads it

`settled` gains a third arm: not waiting in the queue, and `code_covered`. The flag is
written only by `pricing.reprice`: true when the code deducted something and a lane's
total came to zero.

**Why either lane:** the fencer chooses the lane, and a lane at zero means they owe
nothing. **Why stored rather than `total == 0 and code is not null`:** a registration
holding a code on a free selection would read as paid though the code did nothing,
contradicting the rule that owing nothing and having paid differ. Pre-discount money
is not available to the SQL expression `settled` needs for the expiry query.

Being recomputed on every reprice, the flag falls when an amendment leaves something
owed, `settled` falls with it, and `apply_amendment`'s existing unsettling path opens a
fresh window. No new state, and no journal row: no money moved and nobody waived
anything. **Alternatives rejected:** auto-writing a waiver, which goes stale on
amendment and needs a human reason; suppressing only the clocks, which leaves the
fencer showing unpaid for good (owner decision).

`settling_lane` is None here as for a waiver, so readers assuming a lane behind
`settled` must take the waiver's branch; the task list names them. One reader differs
from the waiver case and matters: `cancel()` reads `settled` as "money may be due
back" and would open a refund on nothing, so the refund standing asks for held credit.

### D5. Locking instead of snapshots

Because price is recomputed from configuration, an effect edited after use would give
one fencer the old price and, at their next amendment, another the new one. So effect,
scope and code text refuse a change while any registration row carries the code; name
and `max_uses` stay open. `max_uses` may be lowered to the current uses, which retires
the code without a separate switch, but not below them. Delete is refused likewise.
A cancelled row still blocks it: it can come back only as a new cycle, but its history
names the code and the cost is one retired row in a list. (Owner decision.)

**Alternative rejected:** snapshotting the effect onto the registration, which gives
one code several meanings and Revenue several lines per code.

### D6. One answer for every failure, and a throttled oracle

Unknown, foreign and exhausted codes all answer `code_unavailable`, identically.
`/price-preview` is public, unthrottled and fires on every selection change, so it
stays code-free. A code is previewed through a separate route with the same body plus
the code, limited to 60 a minute per address: generous for a live form behind a club's
shared address, slow for guessing. Codes compare trimmed, case-folded and with
diacritics stripped, so `ŠKOLA ` finds `skola`.

A held code must keep pricing after it runs out, or the holder's own amendment form
would report it as unavailable. So a managed registration previews through its own
route, which prices the held code and applies the availability check only to a code
being newly added.

### D7. The redemption table is a third table in the Payments phase

Setup defines; the phase shows who used what (owner decision). A third tab on the first
band, offered only while the tournament has a code, so the great majority of
tournaments see no change. It carries no count, for the reason the fencer tab has none:
those counts mean outstanding work. It loads independently. On a payments-off
tournament the phase exists holding the settled state, and the tab appears there too.
Rows are live registrations only, so the table agrees with the uses figure.

### D8. The deposit is capped at the total

A code can take a total below the flat deposit, and the due mail would then ask for
more than is owed, with a QR for it. The deposit asked becomes `min(deposit, total)`
per lane in `emails` and wherever instructions state it. The threshold in `matching`
needs no change: a registration that paid its whole total settles and leaves the
window regardless.

## Risks / Trade-offs

- [A slug of a name is guessable: "student" is a likely code] → The prefill is what was
  asked for and stays editable; the rate limit only slows guessing. A limit caps the
  damage. The section's help text says so.
- [`/register` itself answers `code_unavailable`] → It needs a verified account or the
  guest throttle, so it is a far worse oracle than the preview. Not throttled further.
- [The form shows the code field, disclosing that codes exist] → Accepted: the field
  disappears when none is usable, and a code is worthless without its text.
- [A wider `settled` reaches every reader] → It stays narrow: the flag is true only
  where a code brought a total to zero. The waiver has already proved those readers
  tolerate settled with no lane.
- [Adding a code to a paid registration makes an overpayment the organizer must refund]
  → Existing behaviour, already named in the balance column. Accepted (owner decision).
- [Amendment re-pricing at the fixed-before-percent order differs from what a fencer
  might expect of a voucher] → Stated in the form's preview before submission.

## Migration Plan

One additive Alembic revision: the `discount_code` table, and
`registration.discount_code_id` and `registration.code_covered` (default false). No
backfill. Export schema moves to v20; older documents load with no codes. Rollback is
the revision's downgrade while no code exists; afterwards it would strip discounts
from live registrations whose stored totals keep them.

## Open Questions

None. The owner settled stacking, release of uses, zero totals, late adding, placement,
scope granularity, locking and the redemption table on 2026-11-01.
