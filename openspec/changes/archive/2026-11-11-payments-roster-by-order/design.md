## Context

The Payments phase's registration table is the console's fencer table under
payment columns. `rowsForPhase("payments")` returns every row of the projection
(`frontend/src/Console.tsx`): registrations, imported rows, hand-entered rows and,
since team disciplines arrived, every roster member (`mem:` rows). Member rows
already read dashes in every money cell (`carriesPaymentState`). On TTT Test that
is 59 of 75 rows.

What an order is billed for is already computed: `pricing.registration_breakdown`
returns `PricedPiece`s and per-category `CategoryDeduction`s, and Export ›
Revenue reads it. Two things are missing from it. Team pieces carry their
discipline but not the team, and queued placements are dropped rather than
marked.

The link dialog (`payments/LinkDialog.tsx`) filters the ranked roster from
`transaction_roster` by the holder's name alone.

Owner decisions (2026-11-11): variant A (orders only), the tab renamed to
Registrace, every row unfolds, lines in local currency, queued lines greyed and
italic, the simplest honest handling of a post-issue price change, and pairing
lookup by team and club.

## Goals / Non-Goals

**Goals:**
- Payments lists orders, one row per registration, with no member rows.
- Every order states what it holds, as a summary and as unfolded priced lines.
- Pairing finds an order by team or club name.

**Non-Goals:**
- Per-team extra items. Items stay per registration (a later change).
- Freezing a breakdown at issue time, or changing `total_amount`.
- Teaching the automatic name resolver about clubs or teams.
- Any change to the credited and uncredited tables beyond what pairing needs.

## Decisions

### D1. Payments drops member rows in `rowsForPhase`, nothing else moves

`rowsForPhase` for `payments` becomes `rows.filter(row => !isMemberRow(row))`
before the removal filter. The registration rows of team-only holders stay, as they
are listed today. Imported and hand-entered rows stay too: they are or will be
orders. Footer counts already exclude member rows (`carriesPaymentState`), so they
do not change.

*Alternative:* split Payments into a fencers tab and a teams tab. Rejected because
one variable symbol is one order, and a mixed order (teams plus an individual entry
plus rentals) belongs to neither tab. It would have to appear twice or be divided,
and a credit is attached to the whole registration.

### D2. A new `pricing.registration_lines`, built over the existing breakdown

`registration_lines(registration, tournament) -> list[OrderLine]` returns the lines
in display order:

- `kind`: `discipline` | `team` | `item` | `legacy_rental` | `legacy_afterparty` | `discount` | `code`
- `discipline_slug` / `team_id` + `team_name` / `item_id`
- `qty`, `unit_price`, `amount` (negative for discounts)
- `queued: bool`

The billed lines come from the same selection and date `registration_breakdown`
uses. They are not recomputed separately, so the lines never disagree with the
Revenue tab. Team lines are produced per `Team` (not per repeated discipline) by
walking `registration.teams`. Queued lines (`is_substitute` entries, `waitlisted`
teams, and the extras of an order whose every placement is queued) are priced with
`discipline_fee` / `item.price` at the same date and flagged `queued`. Discount
lines are the breakdown's `CategoryDeduction`s summed per discount (position or
code), because the reader wants "Sleva klub −300", not one figure per category.

*Alternative:* add the lines to the console projection (`SheetRow`). Rejected
because the projection is a replay shared by every phase and the export, and the
lines are read on one phase only.

### D3. One read endpoint, loaded with the Payments phase

`GET /tournaments/{slug}/payments/order-lines` returns
`{registration_id: {lines, lines_total, currency}}` for the tournament's issued
registrations. The console fetches it the way `usePaymentTables` fetches its
tables: only while Payments is active, and reloaded on the same "money moved"
signal. The tables and the lines load independently, so a failed lines request
leaves the table usable with Contents reading absent.

The currency is `tournament.local_currency`. That gives EUR on an EUR-local
tournament for free, and the local currency where EUR is merely accepted.

### D4. The summary and the labels are composed in the frontend

The structured lines arrive language-free. The Contents summary (one team named,
otherwise counted; disciplines by short name; items as a quantity sum; parts joined
by `·`) and the line labels are composed by a pure function in
`payments/orderLines.ts`, which both the table and `LinkDialog` use. Queued lines
are skipped by the summary.

### D5. The difference line is a frontend subtraction

`issued = row.total_amount` (local, frozen at issue). `counted = sum(amount of
non-queued lines)`. Where `issued !== counted`, a closing line reads the difference
"oproti vystavené částce". This is the cheapest honest option the owner allowed.
The organizer's existing tools (waiver, recorded payment, amendment) close the gap.
Nothing is frozen and nothing is written.

A waived row compares against its original total (`waived_amount` + what stands),
not against zero.

### D6. Unfolding reuses the Teams console idiom

The Contents cell is the disclosure control, as the roster count is on the Teams
table (8782eb1). The unfolded lines render as indented sub-rows under the order,
with amounts in the Částka column. Queued lines use the existing muted token and
`font-style: italic`. The design prohibitions hold: no new colour, no zebra, no
animation. The open/closed state is local to the table and not persisted.

### D7. Pairing lookup reaches club and teams

`RankedFencerOut` gains `club: str | None` and `team_names: list[str]`. The dialog
filters with `nameMatches` over the name, the club and each team name, and shows
the same Contents summary from the order-lines load. The ranking score and the
proposal are unchanged.

## Risks / Trade-offs

- [The lines are recomputed at current prices, so after a price change the
  difference line shows on many rows] → This is intended (owner, 2026-11-11). The
  line names the cause rather than hiding it.
- [A legacy-priced tournament has no item identity for rentals and afterparty] →
  The `legacy_*` kinds are labelled by category, as Revenue already does.
- [Discount deductions are whole-unit apportioned per category] → They are summed
  per discount for display. Per-category rounding cancels out in the sum.
- [A fencer who paid in EUR on a CZK tournament sees CZK lines beside an EUR
  balance] → The lines state their currency, and the owner chose local.
- [N+1 loading of registrations with entries, teams, extras and items] → The
  endpoint loads with `selectinload`, as `exportrevenue` does.

## Migration Plan

None. This is a read-only addition and a frontend filter. Rollback is a revert.

## Open Questions

None outstanding. All are resolved in the owner's answers of 2026-11-11.
