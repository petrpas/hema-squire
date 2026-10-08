## Context

Squire stores one figure of money per registration: `total_amount`, plus
`total_eur` where the tournament also prices in EUR. Both are written by
`pricing.reprice`. No itemised price is stored. The module's own premise is
that a price is a pure function of (tournament, item, as-of date). Any
breakdown can therefore be computed again from the registration's selection
and `_priced_on(registration)`. That is how `registration_discounts` already
explains a total.

Money received is a journal (`PaymentCredit`, spec `payment-ledger`). What a
registration has been credited is the sum of its live credits in a lane.
`settled` is derived from them, or from a live waiver.

The Export band reads **replayed rows** (`sheet.base_rows` + `rules.replay`),
not registrations. A row carries `registration_id` where one is behind it,
`paid` (= `registration.settled`) and `settled_by_hand` (= waived). `Summary`
counts over these rows. Revenue counts over the same rows so that the two tabs
never disagree about who is in. It then follows `registration_id` to price
what each row holds.

Facts from the local copy of `na-duel-2026` (2026-10-08) that shaped the
decisions:
- 53 registrations: 41 settled by money, 9 waived, 3 unsettled.
- The tournament prices in CZK with EUR alongside (750 Kč / 30 €).
- Rentals cost 50 Kč, the afterparty costs 0 Kč.
- There is one fixed discount, "Both disciplines": −400 Kč / −15 € on entry.
- There is no early bird.
- Recomputed totals equal stored totals today (drift 0).

## Goals / Non-Goals

**Goals:**
- One table answering, per thing sold:
  - the price;
  - how many are paid out of how many;
  - how much has been paid;
  - how much is still to pay.

  Grouped as the organizer thinks of it, with discounts where they bite.
- Figures the organizer can check by hand: price × count = amount on every
  row.
- An honest bridge from "paid by items" to "credited in the journal", so the
  table is never mistaken for the account balance.

**Non-Goals:**
- Apportioning a partial payment or a deposit across a registration's items.
  The owner declined this (2026-10-08).
- Converting currencies. No exchange rate is read anywhere, as in `pricing`.
- Storing an itemised price. The table recomputes, and is therefore as good as
  the recompute (see Risks).
- Any money action. Export acts on no seat and no money.

## Decisions

### D1. One computation, two readers
`app/exportrevenue.py` returns structured lines: block, kind, name, unit price,
counts, amounts. The Revenue tab reads them through
`GET /tournaments/{slug}/export/revenue`. The Sheets export's `Revenue`
worksheet reads them too. This is the shape `exportsummary` already has. Labels
are composed in the reader's language, the console's or the English tick's.

*Alternative:* compute in the frontend from the existing row payloads. Rejected,
because the rows carry no prices, and pricing lives in `pricing.py`.

### D2. Which registrations a line counts
A line counts a row that is:
- not deleted;
- has a `registration_id`;
- is not waived.

It counts only the row's **seated** entries. A queued placement is priced at
zero by `_registration_selection`, so it owes nothing and has no line.

Extras are billed only where the registration holds an active entry. The same
`selection_total` rule applies, so a registration wholly in the queue
contributes nothing to any block.

Rows without a registration (imported, not yet issued) are counted only in the
reconciliation, as "N řádků bez registrace — neoceněno".

### D3. A line is one item at one unit price
For each counted registration, the breakdown is recomputed at
`_priced_on(registration)`:
- `discipline_fee(…, "local")` per seated individual entry;
- the same fee per team that is not waitlisted;
- `item.price × qty` per extra selection.

Lines are keyed by (block, item, unit price). An item sold at the early-bird and
the regular price has two rows, ordered by price descending. The row name
repeats the item's name; the price column tells them apart.

Paid / all counts pieces, as Summary does: two T-shirts count two. Paid amount
= unit price × paid pieces. Still to pay = unit price × unpaid pieces.

Within a block, items follow the Summary's order: disciplines in tournament
order, then items in the order the tournament holds them. Rows with an option
answer (size) are **not** split, because the price does not depend on the
answer.

Legacy-priced tournaments (no extra items, no discounts) price rentals with the
flat `weapon_rental_fee` per named rental and the afterparty with
`afterparty_fee`. Each becomes one line in a Rentals or Afterparty block, keyed
by fee in the same way.

### D4. Values in the local currency
Every line is valued with the local price column, whatever lane the
registration settled in. The owner chose this over separate EUR tables. A
foreign fencer who paid 30 € is counted at 750 Kč on their row. The money that
actually arrived in EUR appears in the reconciliation, in €.

### D5. Discounts sit in the blocks they deducted from
`pricing._itemized_selection_breakdown` already computes, per discount:
- for a fixed discount, how much `_apply_fixed` took from each category;
- for a percentage discount, `before − after` across its scope.

It reports one figure per discount. It is extended to also return the
deduction **per category** for each discount, in the same pass, so that a
discount's lines and the total are one evaluation. The public
`registration_discounts` keeps its shape. A new function,
`registration_breakdown`, returns the per-category lines and per-category
discount deductions for one registration.

In the table, a discount is a line in each block it deducted from. The line
reads:
- **name**: `Sleva <name>`;
- **price**: the configured effect, either `−400 Kč` or `−10 %`;
- **count**: registrations it applied to in this block, paid / all;
- **paid**: −(sum of the deductions on settled registrations);
- **still to pay**: −(sum on unsettled ones).

A percentage deduction is rounded per discount, as it is today. A fixed
discount spread over categories by `_apply_fixed` appears in each category's
block with that category's share.

*Alternative:* a separate Slevy block. Rejected by the owner. Gross blocks
would make each block total overstate what that category earns.

### D6. Totals
Each block ends with a `<Block> celkem` line:
- **paid and still to pay**: the sum of the block's lines, discounts included,
  so the figure is net;
- **count**: registrations holding at least one counted piece in the block,
  paid / all;
- **price**: none.

A grand total line, `Celkem`, follows the last block. Its amounts are the sum
of the block totals. Its count is the counted registrations, paid / all.

### D7. Reconciliation, against the journal
The last block, `Sesouhlasení`, is a list of labelled amounts. It has no price
and no count columns, except where a line names a number of registrations.
Amounts are in the lane's own currency:

1. `Zaplaceno podle položek`: the grand total's paid amount.
2. `Připsáno na vyrovnané registrace`: live credits on settled, non-waived
   counted registrations, local lane in Kč. EUR lane on its own line in €,
   where the tournament shows EUR.
3. `Rozdíl`: (2) − (1), local lane only, so a shortfall reads negative
   (owner decision, 2026-10-08, during apply). The EUR lane cannot be compared,
   because its rows were valued in Kč. This covers:
   - tolerance shortfalls;
   - overpayments;
   - rounding;
   - prices edited after issue.

   The line says so in its hint. It is stated even when zero.
4. `Prominuto`: the number of waived registrations, and what their selections
   are worth at their prices (D3/D5 applied to them). Plus any money credited
   to them, which a partial waiver can hold.
5. `Zálohy a částečné platby`: credits on unsettled counted registrations,
   per lane.
6. `Platby registrací ve frontě`: credits on registrations waiting wholly in
   the queue (a paying substitute's claim).
7. `Platby zrušených a propadlých registrací`: credits on registrations whose
   lifecycle is cancelled or expired. A forfeited deposit lands here.
7a. `Platby registrací se smazaným řádkem`: credits on registrations whose row
   a deletion took out, with their count; stated only where nonzero. Deleting
   a row does not cancel its registration (owner decision, 2026-10-08, taken
   during apply: on `na-duel-2026` five such registrations hold 2 163,69 Kč).
8. `Řádky bez registrace`: count only.
9. `Celkem připsáno v žurnálu`: every live credit of the tournament, per lane.

Lines 2, 4 to 7 and 7a add up to 9. That identity is a test.

Uncredited bank transactions are deliberately absent. They are the Payments
console's uncredited table, and a reconciliation that also counted them would
state money not yet anybody's.

### D8. Layout
`RevenueTable` reuses the Summary's table-per-block layout and its fixed widths.
There are five columns:
- name, which takes what is left;
- price, `8rem`;
- count, `7rem`, as `12/18`;
- paid, `9rem`;
- still to pay, `9rem`.

Money is right-aligned in tabular figures, formatted as the console formats
money elsewhere. Negative amounts read with a true minus (`−`). Total lines are
set off by the strong rule above them, not by weight. Design prohibition: no
weight 600+. The reconciliation is a two-column table of the same width.

### D9. What leaves
**Copy.** The copy is TSV in the Summary's shape. Each block is headed by its
name and the column labels, with a blank line between blocks. Amounts are
digits without a currency unit. The price cell carries the unit only for a
percentage (`-10 %`), since a spreadsheet reading `−400 Kč` as text would break
a sum. Count cells are written as two columns, `zaplaceno` and `celkem`, so
that they stay numbers.

On screen the count stays one `12/18` cell.

**Sheets.** The `Revenue` worksheet is written whole on each export, like
`Summary` (spec `data-export`), but only when the finances tick is on (D11).
Numbers are written as numbers.

**English.** The English tick renders Squire's words in English: `Entry fees`,
`total`, `Discount`, the reconciliation labels. The organizer's names stay as
written.

### D10. The band
`exporttables.tabs` appends `Tab(kind=REVENUE)` after Summary on every
tournament, as Summary is on every one. A free tournament still has entries to
total, at zero.

Revenue states no count, has no active-only switch, and its rail card offers
only the copy. These are the same reasons as Summary: it states both sides
already.

### D11. Finances leave for Sheets only by a tick
The export card gains a checkbox, **Zahrnout finance** (`Include finances`),
directly under the English tick.
- It is offered to every organizer. The English tick is hidden from organizers
  already working in English; the finances tick is not, because it changes
  something for them too.
- It is off by default.
- Like the English tick, it is held in `Console` state for the session and not
  stored. Each visit to Export starts with it off, so money never reaches the
  workbook because of something ticked last week.

`POST /export/sheet` takes `finances: bool = False` beside `english`.
`export_to_sheets` writes the `Revenue` worksheet only when it is true, and the
`worksheets` list it returns names `Revenue` only then.

Without the tick, a `Revenue` worksheet left by an earlier export is **not
touched**: not rewritten, not cleared, not deleted. The owner chose this on
2026-10-08 over deleting it. It keeps `SheetsClient` at read/write. The cost is
that the stale worksheet keeps the figures of the last export that included
finances. The card's hint under the tick says so.

The tick governs the spreadsheet only. The Revenue tab and its clipboard copy
are the organizer's own and are always available. The JSON download is
unaffected.

*Alternative:* store the tick per tournament. Rejected. A stored "on" would make
a later export carry money without anyone deciding it that time.

## Risks / Trade-offs

- [The recompute uses today's prices; stored totals keep the prices of the day
  they were last repriced.] An item price edited after registrations exist makes
  the lines disagree with what people owe. → D7 line 3 states the difference
  instead of hiding it. The hint names "ceny změněné po vystavení" as one cause.
  Storing itemised prices would fix it properly. That is out of scope and is
  recorded as a follow-up if the difference turns out to matter.
- [Settled-based "paid" hides deposits.] On a deposit tournament most money may
  sit on unsettled registrations, which leaves the paid column nearly empty while
  the account is full. → D7 line 5 states exactly that sum.
- [A partial waiver holding money.] Its money appears in line 4, not line 2, so
  the identity in D7 still holds.
- [Performance.] The table prices every registration on every read: one pass
  over at most a few hundred registrations, with relations already loaded by
  `base_rows`. It is not cached.
- [Sharing money in the Sheets workbook.] The workbook goes to downstream staff.
  → Money is written only with the finances tick, off by default and not
  remembered (D11).
- [A stale `Revenue` worksheet.] After one export with finances and later ones
  without, the workbook keeps the old figures. → The owner accepted this. The
  tick's hint states it, and the worksheet is named `Revenue` so it is easy to
  delete by hand.

## Open Questions

None. All eight decisions were taken by the owner on 2026-10-08:
- paid = settled + reconciliation;
- waived apart;
- a row per price;
- the tab in Export, after Summary, written to Sheets only with the finances
  tick, which is off by default and leaves an existing worksheet alone when off;
- discounts in their blocks, with a minus;
- a block total counts people;
- every offered category, including at 0;
- the queue, cancelled and expired registrations only in the reconciliation.
