# payments-console Specification

## Purpose
Define the Payments phase's two tables — what each holds, what an organizer does
from it, and what the fencer table states about money beside them: the payments
that arrived and were credited to somebody, and the payments that arrived and
lie on nobody.

Two rather than the seven queues this replaces, because every one of those was
one of these two questions with a filter on it, and the same fact showed on up
to three of them at once. Which table a payment belongs to is the credit
journal's answer; what is to be done about it is a column.

Each row is stated on the evidence its decision needs, so that resolving one
costs a reading and an action rather than a hunt through the transaction list.
## Requirements
### Requirement: Manual link dialog
The organizer SHALL be able to open a link dialog from any unmatched transaction. The dialog SHALL offer the transaction's detected candidate VS values as one-click choices, SHALL accept a VS entered by hand, and SHALL allow several registrations to be selected together so that one transfer covering several fencers is linked in a single action. Confirming SHALL call the manual-link endpoint, and on success the transaction SHALL leave the uncredited table.

#### Scenario: Candidate accepted
- **WHEN** the organizer opens the dialog on a transaction whose message contains a VS that resolves to a registration
- **THEN** that VS is offered as a candidate and one click selects it

#### Scenario: One transfer covers two fencers
- **WHEN** the organizer selects two VS values in the dialog and confirms
- **THEN** both registrations are linked to the transaction in one request and both are marked paid

#### Scenario: Unknown VS rejected
- **WHEN** the organizer types a VS that belongs to no registration and confirms
- **THEN** the dialog reports which VS was not recognised and stays open with the entry preserved

#### Scenario: Dialog dismissed
- **WHEN** the organizer closes the dialog without confirming
- **THEN** no link is created and the transaction stays in the queue

### Requirement: Recording a payment from the console
The Payments phase SHALL offer an action that records a payment Squire never saw, reachable from a registration's own row in the fencer table rather than from a queue: the queues hold money looking for a registration, and this is a registration whose money never arrived in a statement.

It SHALL sit at the end of the row, among the row's actions, and SHALL NOT take a column of the table. It is an action and not a value, and the phase's table is already wide.

The action SHALL ask for the amount, the currency where the tournament prices in two, the date the money arrived, how it arrived, and an optional note, and SHALL state what the registration is owed as it asks, so the organizer records against a balance rather than from memory. Confirming SHALL credit the registration and refresh the table so the outstanding column answers immediately.

The action SHALL be refused with a stated reason where the registration cannot take a credit, and the dialog SHALL stay open with what was typed preserved.

#### Scenario: Cash recorded from the row
- **WHEN** the organizer opens the record-payment action on a reserved registration owing 1750 and confirms 1750 in cash
- **THEN** the registration is credited, the row reads paid, and the outstanding column reads zero without a reload

#### Scenario: The balance is stated as it asks
- **WHEN** the organizer opens the action on a registration owing 1250
- **THEN** the dialog states that 1250 is outstanding before any amount is typed

#### Scenario: Dialog dismissed
- **WHEN** the organizer closes the dialog without confirming
- **THEN** nothing is credited and the registration is unchanged

### Requirement: The settled mark is offered wherever it applies
The Payments phase SHALL offer the settled-by-hand mark on every tournament, not only where Squire collects nothing. Where Squire handles the payments the mark is the waiver, and setting it SHALL require a stated reason before it is accepted; the reason SHALL be shown wherever the mark is shown, so that a paid row holding no money explains itself in place.

Where Squire collects, the mark SHALL be offered **on the registration's state cell** and SHALL NOT take a column of its own. It changes exactly that cell — from reserved to paid with no money behind it — and a column that would be empty on almost every row does not earn its width in a table already carrying the symbol, the total, the balance, the dates and the state. Only where the phase is boned out, and the mark is its whole content, SHALL the mark have a column.

The mark SHALL be offered on a **reserved** registration and, to unset, on one a person waived. It SHALL NOT be offered on a registration the money settled — unsetting a mark nobody made would return it to reserved and strand its credit — nor on a state the lifecycle or the fencer chose.

A waived registration's outstanding figure SHALL be presented as waived rather than as a balance owed, in the fencer table and everywhere else the two are shown together.

#### Scenario: Waiving from the state cell
- **WHEN** the organizer opens the mark on a reserved registration in the Payments phase of a tournament whose payments Squire handles
- **THEN** a reason is asked for, the mark is not written until one is given, and the row's state afterwards reads paid with the reason on it

#### Scenario: No column for the mark where the ledger is live
- **WHEN** the organizer opens the Payments phase of a tournament whose payments Squire handles
- **THEN** the table carries no settled column, and the mark is reached on the state cell instead

#### Scenario: A refused mark says so where it was asked for
- **WHEN** the organizer confirms a waiver and the request is refused
- **THEN** the dialog stays open stating the reason it was refused, with what was typed intact, and the row is unchanged

#### Scenario: A registration the money settled is not the cell's to unset
- **WHEN** the organizer reads the state cell of a registration paid by a transaction or a recorded payment
- **THEN** it states the state and offers no mark to unset

#### Scenario: The waived balance does not read as a debt
- **WHEN** a waived registration with a total of 1750 is shown in the fencer table
- **THEN** its outstanding column states that the balance is waived rather than showing 1750 owed

### Requirement: A refused payment names a hand-settled cause
WHERE a payment is uncredited because its registration is no longer reserved,
the uncredited table SHALL state whether that registration was settled by hand
and, where it was, show the mark or the recorded payment that settled it. An
organizer resolving the row is deciding whether the payment is further money or
the same money arriving twice, and that decision needs the earlier act in front
of it.

#### Scenario: The earlier act is shown
- **WHEN** an uncredited payment names a registration a recorded cash payment had settled
- **THEN** the row states that the registration was settled by a payment recorded by hand, with its amount and date

#### Scenario: An ordinary conflict is unchanged
- **WHEN** an uncredited payment names a registration paid by an earlier bank transaction
- **THEN** the row states that as it does today, with no hand-settled claim made

### Requirement: Uncredited payments are one table
The console SHALL list every payment that arrived and holds no live credit,
showing the payer, the amount with its currency, the date, and the payment's own
message text, so the organizer can judge who sent the money.

Money set aside as a sibling tournament's, on a bank account several
tournaments share, SHALL NOT appear here. It holds no credit and never will
hold one on this tournament — its own console is what resolves it — so listing
it would put work in the table that nobody reading that table can do. Holding
no credit is therefore necessary but not sufficient: the table is the payments
that lie on nobody **and are this tournament's to resolve**.

Beside that evidence each row SHALL state **what is to be done with it**, which
is one of three things: the fencer a resolver read in the payment's text, the
reason nothing could be credited, or nothing at all where the payment simply
carries no usable reference. The actions offered on a row SHALL follow from what
that column says — confirming a proposal, assigning the payment by hand,
reinstating a reservation, or marking the money for refund.

A payment whose pairing credited nothing SHALL appear here with that as its
reason, and SHALL leave the table by itself once a credit exists, without an
organizer having to withdraw anything.

#### Scenario: Foreign transfer with no VS
- **WHEN** a SEPA transfer arrives with the fencer's name but no parsable VS
- **THEN** it appears in the uncredited table with its payer name, amount, date and message, and nothing is claimed about who it is for

#### Scenario: A proposal is one row among them
- **WHEN** a resolver reads a fencer's name in an uncredited payment's text
- **THEN** that payment appears in the same table with the fencer named as what is to be done, and can be confirmed or rejected in place

#### Scenario: A refusal states itself
- **WHEN** a payment carries a VS whose reservation had already expired outside the grace period
- **THEN** the payment appears in the uncredited table stating that reason, with the reinstate and refund actions on the row

#### Scenario: A pairing that credited nothing is work, not a result
- **WHEN** an organizer pairs a payment with a registration and the registration is cancelled before the pairing can credit anything
- **THEN** the payment appears in the uncredited table naming the registration it was paired with and stating that nothing was credited

#### Scenario: Credited money is not here
- **WHEN** a transaction holds a live credit
- **THEN** it does not appear in the uncredited table, whatever its status says

#### Scenario: A sibling tournament's money is not this console's work
- **WHEN** a statement from a shared bank account brings a payment carrying another tournament's variable symbol
- **THEN** it does not appear in the uncredited table, the phase stating instead that its own console will match it

### Requirement: Credited payments are one table
The console SHALL list every payment holding a live credit — a bank transaction
and a payment recorded by hand alike — showing the date the money arrived, where
it came from, the amount with its currency, and every registration it credited,
since one payment may credit several.

Each row SHALL state **why** it was credited, distinguishing at least a symbol
the matcher read, a pairing an organizer made, and a payment a person recorded,
so that a reader asking why a registration is paid is not left to infer it.

The organizer SHALL be able to reverse a payment's credit from this table and to
pair the payment with somebody else. Both act on **the whole payment**: reversal
SHALL release every live credit that payment made, and the payment SHALL return
to the uncredited table.

Reversal SHALL state its consequence before it is confirmed, naming the
registrations that stop reading as paid or stating plainly that none does. That
statement SHALL be asked of the current state rather than read from the listing,
because whether a registration reads as paid is a derivation and the listing may
be older than the answer; the confirmation SHALL NOT be offered until it has
been obtained.

Which payments hold credit SHALL be answered from the credit journal and not
from a transaction's matched registration or its status: what a payment credited
is what its live entries say.

#### Scenario: An automatically matched transaction is listed
- **WHEN** a transaction is credited to a registration by an automatic VS match
- **THEN** it appears in the credited table with its date, payer, amount and the fencer it credited, and states that a symbol is why

#### Scenario: A hand-recorded payment sits beside the bank's
- **WHEN** the organizer records a cash payment
- **THEN** it appears in the same credited table, stating that a person recorded it and who

#### Scenario: A payment covering three registrations names all three
- **WHEN** the credited table lists a payment that credited three registrations
- **THEN** all three fencers are named on its row, each with the amount credited to them

#### Scenario: The consequence is stated before it is confirmed
- **WHEN** the organizer opens the reversal action on a payment whose credit is the whole of what settled a registration
- **THEN** that registration is named as one that will stop reading as paid, and nothing is reversed until the organizer confirms

#### Scenario: Nothing stops reading as paid
- **WHEN** the organizer opens the reversal action on a payment whose registrations remain settled without it
- **THEN** the action states that no registration stops reading as paid

#### Scenario: A reversal moves the row to the other table
- **WHEN** the organizer confirms the reversal
- **THEN** the credits are reversed and the payment appears in the uncredited table instead

#### Scenario: Removal of a hand-recorded payment is the same act
- **WHEN** the organizer reverses a payment they had recorded by hand
- **THEN** exactly the amount it credited is released, the consequence is stated first as for any other payment, and the row leaves the table

### Requirement: A line beside the tab band states one thing about the open table
The space beside the payments tab band SHALL carry one line about **the table
being read**, not about the band. It SHALL state something the table's own count
cannot: how many of the uncredited payments are proposals awaiting a person, or
what the credited payments come to in total.

The line SHALL be worded so that a subset reads as a subset and not as a second
count that could disagree with the tab's. It SHALL be absent where there is
nothing to say, rather than stating a zero. It SHALL NOT be a control: reading
it changes nothing about which rows are shown.

The fencer table SHALL carry no such line, because the phase's footer already
states its totals.

#### Scenario: A subset is stated as a subset
- **WHEN** seven payments are uncredited and three of them carry a proposal
- **THEN** the tab states seven, and the line beside the band states that three of those are proposals

#### Scenario: Nothing to say
- **WHEN** no uncredited payment carries a proposal
- **THEN** no line appears beside the band, and no zero is stated

#### Scenario: The line follows the open table
- **WHEN** the organizer moves from the uncredited payments to the credited ones
- **THEN** the line changes to what the credited table has to say, rather than continuing to describe the table that was left

#### Scenario: The fencer table says nothing here
- **WHEN** the fencer table is the open tab
- **THEN** the space beside the band is empty, the phase's footer stating the roster's totals as before

### Requirement: The phase is a set of tables behind two bands
The Payments phase SHALL present the organizer's payment work as **two tables**
in the phase's main area, with the **discount codes table** beside them on a
tournament that has any code, reached through two tab bands: the first choosing
between the registration table, the payments and the codes, the second — shown only while the
payments are chosen — choosing between **credited** and **uncredited** payments.
Each band SHALL carry the console's own tab idiom, and each payments tab SHALL
state its own count, so that work in a table nobody is looking at is still
visible. The registration tab and the codes tab SHALL carry no count: these counts mean
outstanding work, and a roster size among them would read as more of it. The registration tab SHALL be labelled as the registrations ("Registrace" / "Registrations"), not as the fencers: the table it opens lists orders, and on a team tournament many of its rows belong to holders who do not fight. The phase's rail
SHALL hold only the operation's parameters and the manual-edits log, as every
other phase's rail does.

Which table a payment belongs to SHALL be decided by **the credit journal** —
whether the payment holds a live credit — and not by the transaction's status. A
payment the matcher marked resolved while crediting nothing is uncredited money
and belongs with the work.

Each table SHALL load independently of the other and of the registration table. A
table with nothing to show SHALL say so rather than disappear, and its tab SHALL
remain with its zero rather than being withdrawn.

The phase's sheet heading SHALL name the phase's own subject rather than the
fencer table's, as the Import phase's heading already does.

#### Scenario: Nothing outstanding
- **WHEN** the organizer opens the Payments phase on a tournament where nothing has been credited and nothing awaits resolution
- **THEN** both payments tabs show a count of zero, and whichever is opened states that it is empty in a single line

#### Scenario: The second band appears with the money
- **WHEN** the organizer chooses the payments in the first band
- **THEN** a second band appears beside it offering the credited and the uncredited payments, and the first band still offers the registration table

#### Scenario: The fencer table gives way to whichever table is read
- **WHEN** the organizer opens either payments table
- **THEN** that table is what the phase shows, and returning to the registration tab lists every registration with its payment state as before

#### Scenario: One table fails to load
- **WHEN** the request behind the uncredited payments fails while the other succeeds
- **THEN** that table reports its own failure, and the credited table and the registration table still render their data

#### Scenario: The phase names itself
- **WHEN** the organizer opens the Payments phase
- **THEN** the sheet heading names the management of payments rather than the registered fencers

#### Scenario: No codes, no tab
- **WHEN** the organizer opens the Payments phase of a tournament with no discount code
- **THEN** the first band offers the registration table and the payments, as it does without the feature

#### Scenario: The codes tab appears with the first code
- **WHEN** the tournament has a discount code
- **THEN** the first band offers the codes table as well, with no count, whether or not anyone has used one

#### Scenario: The first tab names registrations
- **WHEN** the organizer opens the Payments phase
- **THEN** the first tab of the first band reads "Registrace" in Czech and "Registrations" in English

### Requirement: The codes table says who holds what
The discount codes table SHALL list one row per live registration carrying a code, stating the fencer, the code's name and its code text, what the code deducted in the local currency, and whether the registration reads as paid. A line beside the tab band SHALL state, per code, its uses against its limit, an unlimited code stating its uses alone. A code nobody holds SHALL appear in that line and in no row.

The table SHALL load independently of the phase's other tables, SHALL require console access, and SHALL say so in a single line when nobody holds a code. Registrations that cancelled or expired SHALL NOT be listed, so that the rows always agree with the uses stated.

#### Scenario: Who used it
- **WHEN** three fencers registered with a code limited to 10
- **THEN** the table lists the three with what each was deducted, and the line states 3 / 10

#### Scenario: A cancellation leaves the table
- **WHEN** one of them cancels
- **THEN** the row disappears and the line states 2 / 10

#### Scenario: Nobody yet
- **WHEN** a tournament has codes and none has been used
- **THEN** the table says so in one line and the line beside the band states each at zero

#### Scenario: A revival past the limit
- **WHEN** a revival takes a single-use code to two holders
- **THEN** both are listed and the line states 2 / 1

### Requirement: The registration table states what each order holds
The Payments phase's registration table SHALL carry a **Contents** column
("Obsah" / "Contents") that states in a few words what each registration is billed
for. Only what is billed SHALL be counted: a placement in a queue is not.

The statement SHALL be composed from the order's billed lines, in this order:
- teams: one team is named. Two or more are counted ("2 týmy").
- individual disciplines: each is named by its short name.
- extra items: counted as a sum of their quantities ("3 položky").

The parts SHALL be joined by a middle dot. A part with nothing in it SHALL be left
out. A row that is billed for nothing SHALL read as absent, in the table's idiom
for a cell with nothing to state.

The column SHALL be present on the Payments phase whether or not Squire handles
the tournament's payments, because what an order holds is a fact either way.

#### Scenario: One team
- **WHEN** a registration entered the team "Hema Praha" and nothing else
- **THEN** its Contents cell reads the team's name

#### Scenario: A mixed order
- **WHEN** a registration entered two teams and the individual longsword discipline, and bought three weapon rentals
- **THEN** its Contents cell reads "2 týmy · LS · 3 položky"

#### Scenario: A queued team is not counted
- **WHEN** a registration entered two teams and one of them is waitlisted
- **THEN** its Contents cell names the one seated team, as it would for an order of one team

### Requirement: Every order unfolds into its priced lines
Every row of the Payments registration table that is billed for something SHALL
unfold in place, from its Contents cell, into the lines its total is made of. It
SHALL use the idiom the Teams console uses to unfold a roster. Rows SHALL be
unfoldable whatever the number of their lines, so that the table reads the same
way on every row.

The lines SHALL be:
- one line per individual discipline entered, at its price
- one line per team entered, naming the team and its discipline, at the
  discipline's per-team price
- one line per extra item, with its quantity where it is more than one and the
  sum for that quantity. On a tournament priced the legacy way, the flat rental
  and afterparty fees are stated as such lines.
- one negative line per discount, and one for a discount code, stating what it
  took

The lines SHALL be stated in the tournament's local currency. That is EUR on a
tournament whose local currency is EUR, and the local currency on a tournament that
also accepts EUR. The local price is what the order was itemised at.

The extra items SHALL be stated as the order's own, not divided among its teams.
An item belongs to the registration that bought it.

#### Scenario: Unfolding a mixed order
- **WHEN** the organizer unfolds a registration that entered teams A and B in sabre, the individual longsword, three weapon rentals and the afterparty, and that was granted a club discount
- **THEN** the lines read team A with its price, team B with its price, longsword with its price, the rentals ×3 with their sum, the afterparty with its price, and the discount as a negative amount

#### Scenario: Every row unfolds
- **WHEN** a registration holds a single team and nothing else
- **THEN** its row still unfolds, into that one line

#### Scenario: EUR-local tournament
- **WHEN** the tournament's local currency is EUR
- **THEN** every line is stated in EUR

### Requirement: Queued placements are shown and not counted
A placement that is in a queue, whether a substitute discipline entry or a
waitlisted team, SHALL appear among the unfolded lines of its order with the price
it would carry. It SHALL be greyed and set in italic so that it reads as not
counted, and it SHALL NOT enter the Contents summary, the sum of the lines or the
difference line. Extra items of an order whose every placement is queued are not
billed, and SHALL be shown the same way.

#### Scenario: A waitlisted team among the lines
- **WHEN** the organizer unfolds a registration whose second team is waitlisted
- **THEN** the waitlisted team's line is greyed and italic, and the lines that are counted sum to the order's total

### Requirement: A difference to the issued total is stated, not hidden
The lines SHALL be priced at the prices that stand now. Where they do not sum to
the order's issued total, because a price was changed after the order was issued,
the unfolded order SHALL end with a line stating the difference to the issued
total. The issued total SHALL stay what it is: changing a price after issuing is
the organizer's act, and the organizer settles the difference with the tools that
exist for it (a waiver, a recorded payment, an amendment). Where the lines and the
total agree, no such line SHALL be shown.

#### Scenario: A price changed after issuing
- **WHEN** a registration was issued with three rentals at 150 each and the organizer has since changed the rental price to 200
- **THEN** the rentals line reads 600 at the price that stands now, and a closing line states the difference of 150 against the issued total, which is unchanged

#### Scenario: Nothing changed
- **WHEN** the lines sum to the issued total
- **THEN** no difference line is shown

