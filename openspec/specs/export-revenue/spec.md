# export-revenue Specification

## Purpose
Fix the Export phase's Revenue tab: what each discipline, extra item and discount has brought in and has still to bring — which blocks and lines it holds, how a line is priced and counted, where a discount stands, the block and grand totals, the reconciliation of the paid figure against the payment journal, and how the table leaves the screen and, only by the Include finances tick, reaches the spreadsheet.

## Requirements
### Requirement: The revenue is a table per block
The Revenue tab SHALL be a stack of tables, one per block, in this order:
- **Entry fees** (`Startovné`): the tournament's individual disciplines in its
  discipline order, then its team disciplines in the same order;
- then one block per extra-item category the tournament offers, in the order
  the band lists categories, its items in the order the tournament holds them;
- then the **reconciliation**.

Every category the tournament offers SHALL have a block, and an item it offers
SHALL have a line even where nobody bought it or its price is zero.

Every table except the reconciliation SHALL have five columns, the first headed by
the block's name, then **Price**, **Count**, **Paid** and **To pay**. Every table
SHALL have the same fixed width and the same fixed widths for its columns but the
first, so that every figure stands under the figure of its kind in the table
above; a name longer than its column SHALL wrap rather than widen it.

#### Scenario: Blocks in order
- **WHEN** a tournament offers Sabre Open and Longsword, a rental of a sabre and an afterparty
- **THEN** the tab holds Startovné with Sabre Open and Longsword, then Zápůjčky, then Afterparty, then the reconciliation

#### Scenario: A free item still stands
- **WHEN** the afterparty costs 0 Kč and thirty fencers chose it
- **THEN** the Afterparty block has a line at 0 Kč counting thirty, with 0 paid and 0 to pay

#### Scenario: A team discipline is priced
- **WHEN** a tournament offers team longsword at 1 500 Kč per team and four teams are entered and not waitlisted
- **THEN** the Startovné block has a team longsword line at 1 500 Kč counting four

### Requirement: A line is one item at one price
A line SHALL state one item, or one discipline, at one unit price. Its count SHALL
be the pieces sold at that price — the quantity of every selection, so two
T-shirts count two; for a discipline, the seated entries; for a team discipline,
the teams entered and not waitlisted — stated as paid / all. Its **Paid** SHALL be
the price times the paid pieces and its **To pay** the price times the rest.

Where one item was sold at more than one unit price — an early-bird price and the
regular one — it SHALL have a line for each price, the higher first. An item's
option answers (a T-shirt's size) SHALL NOT split its line, since the price does
not depend on them.

A piece's price SHALL be the price the registration is priced at: the tournament's
local-currency price for the day the registration was made, as `pricing` computes
its total. A registration settled in EUR SHALL be valued at its local-currency
price.

#### Scenario: Price times count
- **WHEN** eighteen fencers hold a seated entry in Sabre Open at 500 Kč and twelve of them are settled
- **THEN** the line reads Sabre Open, 500 Kč, 12/18, 6 000, 3 000

#### Scenario: Two prices, two lines
- **WHEN** ten fencers entered Longsword at the early-bird price of 600 Kč and eight at the regular 750 Kč
- **THEN** the block has a Longsword line at 750 Kč counting eight and, beneath it, one at 600 Kč counting ten

#### Scenario: Pieces, not people
- **WHEN** one settled fencer ordered two T-shirts at 300 Kč
- **THEN** the T-shirt line counts 2/2 and states 600 paid

#### Scenario: A euro payer at the crown price
- **WHEN** a fencer entered at 750 Kč or 30 € settled by paying 30 €
- **THEN** their entry counts on the 750 Kč line as paid, at 750

### Requirement: Paid is the registration's settled state
A line SHALL count a piece as paid where its registration is settled by money, and
as to pay otherwise, exactly as Summary reads it (`export-summary`). A partial
payment or a deposit SHALL NOT be apportioned: every piece of a registration not
yet settled is to pay.

A **waived** registration SHALL count on no line and in no total — neither paid,
since no money came, nor to pay, since none is owed. It is stated in the
reconciliation.

A line SHALL count only what the registration is billed for: its seated entries,
its teams not waitlisted, and its extras where it holds at least one of those. A
queued placement, and a registration waiting wholly in the queue, SHALL count on
no line.

A row a deletion took out, and a row with no registration behind it, SHALL count
on no line.

#### Scenario: A deposit is not apportioned
- **WHEN** a fencer entered at 800 Kč has paid a 300 Kč deposit and is not yet settled
- **THEN** their entry counts on the to-pay side at 800, and the 300 appears in the reconciliation

#### Scenario: A waived registration is on no line
- **WHEN** the organizer waived the price of a fencer entered in Sabre Open
- **THEN** Sabre Open's count leaves them out on both sides

#### Scenario: The queue owes nothing
- **WHEN** a fencer's only entry sits in Sabre Open's queue and they ordered a rental
- **THEN** neither the Sabre Open line nor the rental line counts them

### Requirement: A discount stands in the block it deducted from
A discount the tournament configures SHALL appear as a line, named `Sleva`
(`Discount`) followed by its name, in the block of every category it deducted
from on at least one counted registration. Its line SHALL state:
- as **Price**, the configured effect with a minus: the fixed amount in the local
  currency (`−400 Kč`) or the percentage (`−10 %`);
- as **Count**, the counted registrations it deducted from in this block, as
  paid / all;
- as **Paid** and **To pay**, the amounts it deducted in this block from the
  settled and from the other registrations, as negative figures.

The amount a discount deducted from a category SHALL be the amount pricing
deducted when it priced the registration's total — for a fixed discount
reaching several categories, the share it took from each — so that a block's
lines and discounts sum to what that category is billed.

A discount that applied to no counted registration SHALL have no line.

#### Scenario: A discount on entry fees
- **WHEN** a −400 Kč discount for entering both disciplines applied to twelve registrations, eight of them settled
- **THEN** the Startovné block has a line Sleva Both disciplines, −400 Kč, 8/12, −3 200, −1 600

#### Scenario: A discount across two categories
- **WHEN** a fixed −500 Kč discount reaching entry fees and rentals took 400 from a registration's entry fees and 100 from its rentals
- **THEN** the registration counts on the discount's line in Startovné at −400 and on its line in Zápůjčky at −100

#### Scenario: A discount nobody got
- **WHEN** an early-registration discount applied to no one
- **THEN** no block has a line for it

### Requirement: Every block has a total, and the table a grand total
Each block but the reconciliation SHALL end with a total line, named as the block
followed by `celkem` (`total`), stating as **Paid** and **To pay** the sums of the
block's lines, discounts included, and as **Count** the counted registrations
holding at least one piece in the block, as paid / all. It SHALL state no price.

After the last block, a grand total line `Celkem` (`Total`) SHALL state the sums
of the block totals and, as its count, the counted registrations, paid / all.

A total line SHALL be set apart from the lines above it by a rule, not by weight
or colour.

#### Scenario: A block total
- **WHEN** Startovné holds Sabre Open 6 000 / 3 000, Longsword 7 400 / 3 400 and Sleva Both disciplines −3 200 / −1 600, over twenty-four registrations of which twenty are settled
- **THEN** its total reads Startovné celkem, 20/24, 10 200, 4 800

#### Scenario: The grand total
- **WHEN** Startovné totals 10 200 / 4 800 and Zápůjčky 400 / 100
- **THEN** the grand total reads 10 600 / 4 900

### Requirement: The reconciliation states what the journal holds
The last table SHALL reconcile the paid figure with the payment journal
(`payment-ledger`). It SHALL have two columns, a label and an amount, and SHALL
state, in this order:
1. **Paid by items**: the grand total's paid amount;
2. **Credited to settled registrations**: the live credits of the counted settled
   registrations, per currency lane;
3. **Difference**: the second less the first, in the local lane only, so that
   money missing reads negative and money over reads positive, stated even
   when zero, with a hint naming what it holds — tolerated shortfalls,
   overpayments, rounding, and prices edited after the registrations were priced;
4. **Waived**: how many registrations were waived, what their selections are
   worth at their prices, and the live credits they hold;
5. **Deposits and partial payments**: the live credits of the counted
   registrations not yet settled, per lane;
6. **Payments from the queue**: the live credits of registrations waiting wholly
   in the queue, per lane;
7. **Cancelled and expired registrations**: the live credits of registrations
   whose lifecycle is cancelled or expired, per lane;
   - **Registrations whose row was deleted**: how many registrations stand
     behind a row a deletion took out of the table, and their live credits,
     per lane — stated only where they hold some, since deleting a row leaves
     its registration and its money standing;
8. **Rows without a registration**: how many there are, unpriced;
9. **Credited in the journal**: every live credit of the tournament, per lane.

Lines 2, 4 (its credits), 5, 6, 7 and the deleted rows' line SHALL sum to
line 9 in each lane. Each registration's credits SHALL count on exactly one of
them, the first that holds it in this order: a lifecycle that ended, a deleted
row, a waiver, the queue, then settled or not. An amount
in EUR SHALL be stated in EUR; no amount SHALL be converted.

A bank transaction credited to no registration SHALL NOT be counted here: it is
nobody's money yet, and the Payments phase lists it.

#### Scenario: The account agrees
- **WHEN** every settled registration was credited exactly its total and nothing else was credited
- **THEN** Difference reads 0 and Credited in the journal equals Paid by items

#### Scenario: A tolerated shortfall shows
- **WHEN** a fencer settled a 750 Kč entry within tolerance by a credit of 708 Kč
- **THEN** Paid by items counts 750, Credited to settled registrations counts 708, and Difference reads −42

#### Scenario: A forfeited deposit is accounted for
- **WHEN** a registration expired after a 300 Kč deposit was credited
- **THEN** Cancelled and expired registrations reads 300, and the journal total includes it

#### Scenario: Money on a deleted row is stated
- **WHEN** the organizer deleted the row of a registration credited 500 Kč
- **THEN** no line counts it, the reconciliation states one registration whose row was deleted holding 500, and the journal total includes it

#### Scenario: Euro stays euro
- **WHEN** two settled registrations were credited 30 € each
- **THEN** Credited to settled registrations states 60 € on its own line, and Difference compares only the crown lane

### Requirement: Finances reach the spreadsheet only by a tick
The export card SHALL offer a checkbox **Include finances** (`Zahrnout finance`)
under its row of actions. The English tick stands above the card, not in it
(`export-tables`). It SHALL be offered to every organizer, whatever
their language, and SHALL be off whenever the Export phase is opened. It SHALL
NOT be stored.

The Sheets export SHALL write the `Revenue` worksheet only when the tick is on.
When the tick is off, the export SHALL NOT write, clear or delete a `Revenue`
worksheet the spreadsheet already holds, and the card SHALL state, under the
tick, that a revenue worksheet from an earlier export is left as it was.

The tick SHALL govern the spreadsheet alone: the Revenue tab, its copy and the
JSON download SHALL be the same whether it is on or off.

#### Scenario: Off by default
- **WHEN** the organizer opens the Export phase and writes to Sheets without touching the tick
- **THEN** no Revenue worksheet is written, and the export reports the worksheets it did write without Revenue

#### Scenario: Ticked
- **WHEN** the organizer ticks Include finances and writes to Sheets
- **THEN** the Revenue worksheet is written whole

#### Scenario: An earlier revenue worksheet is left alone
- **WHEN** the spreadsheet holds a Revenue worksheet from an earlier export and the organizer writes to Sheets with the tick off
- **THEN** that worksheet still holds what it held

#### Scenario: Not remembered
- **WHEN** the organizer exported with the tick on, left Export and came back
- **THEN** the tick is off

#### Scenario: Offered in English too
- **WHEN** an organizer working in English opens the export card
- **THEN** no English tick is shown, and the Include finances tick is

### Requirement: The revenue leaves as the other tables do
The Revenue tab's copy action SHALL put its tables on the clipboard as
tab-separated values: each table as a header row followed by its lines, one blank
line between two tables. The count SHALL be written as two cells, paid and all,
and every price and amount as digits without a currency unit, so that a
spreadsheet reads them as numbers; a percentage price SHALL keep its `%`.

The English tick SHALL render the block names, column headers, `celkem`, `Sleva`
and the reconciliation's labels in English, and leave discipline, item and
discount names as the organizer wrote them.

The Sheets export SHALL write the same tables, in the same layout, as the
`Revenue` worksheet (`data-export`), and SHALL do so only when the organizer has
ticked **Include finances** for that export.

The tab SHALL only read. It SHALL offer no action that changes a seat, a total or
a credit.

#### Scenario: A copied revenue
- **WHEN** the organizer copies the Revenue tab and pastes into a spreadsheet
- **THEN** each block lands under its own header, the count in two columns, and the amounts sum as numbers

#### Scenario: The copy needs no tick
- **WHEN** the finances tick is off and the organizer copies the Revenue tab
- **THEN** the tables are on the clipboard

#### Scenario: An English copy
- **WHEN** a Czech-speaking organizer ticks English and copies the revenue
- **THEN** the first block is headed Entry fees and its total line reads Entry fees total
