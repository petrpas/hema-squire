# payments-console Specification

## Purpose
Define the Payments phase's resolution queues — what each holds, what an
organizer does to empty it, and what the fencer table states about money beside
them: the transactions nothing matched, the ones a check flagged, the
reservations that expired holding a payment, and the links an organizer made by
hand.

Each queue is a decision waiting for a person, stated on the evidence the
decision needs, so that resolving one costs a reading and an action rather than
a hunt through the transaction list.
## Requirements
### Requirement: Payment resolution views
The Payments phase SHALL present the organizer's payment work as five views in the phase's main area, stacked above the fencer table: flagged transactions, unmatched transactions, reservations that expired while holding credited money, active payment links, and the payments recorded by hand. The phase's rail SHALL hold only the operation's parameters and the manual-edits log, as every other phase's rail does. Each view SHALL load independently of the others and of the table. A view with nothing to show SHALL say so rather than disappear, and SHALL take no more room than its own heading while it has nothing to show.

#### Scenario: Nothing outstanding
- **WHEN** the organizer opens the Payments phase on a tournament where every transaction matched cleanly and nothing was recorded by hand
- **THEN** each of the five views states that it is empty in a single heading line, and the fencer table begins directly below them

#### Scenario: Work sits above the ledger
- **WHEN** the tournament has transactions awaiting resolution
- **THEN** those views appear above the fencer table, and the table below still lists every registration with its payment state

#### Scenario: One view fails to load
- **WHEN** the expired-holding request fails while the others succeed
- **THEN** that view reports its own failure, and the remaining four and the fencer table still render their data

### Requirement: Unmatched transaction queue
The console SHALL list every transaction whose status is `unmatched` — the ones carrying no VS that resolves to a registration — showing the payer, the amount with its currency, the date, and the transaction's message text, so the organizer can judge who sent the money. Flagged transactions SHALL NOT appear in this list; they belong to the flagged queue.

#### Scenario: Foreign transfer with no VS
- **WHEN** a SEPA transfer arrives with the fencer's name but no parsable VS
- **THEN** it appears in the unmatched queue with its payer name, amount, date and message

#### Scenario: Queues do not overlap
- **WHEN** the tournament has both unmatched and flagged transactions
- **THEN** each transaction appears in exactly one of the two cards

### Requirement: Manual link dialog
The organizer SHALL be able to open a link dialog from any unmatched transaction. The dialog SHALL offer the transaction's detected candidate VS values as one-click choices, SHALL accept a VS entered by hand, and SHALL allow several registrations to be selected together so that one transfer covering several fencers is linked in a single action. Confirming SHALL call the manual-link endpoint, and on success the transaction SHALL leave the unmatched queue.

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

### Requirement: Money stranded on expired reservations
The system SHALL expose the reservations that expired while holding credited money, distinguished from ordinary expiries, and the console SHALL list them with the fencer, the VS, the credited amount and when the reservation expired. This list SHALL be readable without touching the transaction queues, because the money in question is already credited and so appears in neither.

A reservation holding money an organizer recorded by hand SHALL appear here on the same terms as one holding a bank credit. The money is as real and the reservation is as expired; that a person entered it rather than a statement changes only who has to be found to give it back.

#### Scenario: Payment credited, reservation expired
- **WHEN** a reservation expires while holding a credited payment
- **THEN** it appears in the expired-holding list with the credited amount and the expiry time

#### Scenario: Ordinary expiry excluded
- **WHEN** a reservation expires having received no payment
- **THEN** it does not appear in the expired-holding list

#### Scenario: Hand-recorded money is not exempt
- **WHEN** a reservation expires holding only a payment the organizer recorded by hand
- **THEN** it appears in the expired-holding list with that amount

#### Scenario: A waiver is not money
- **WHEN** a hand-settled registration is read against this list
- **THEN** it is not listed, because nothing was credited to it

### Requirement: Payment links are visible and removable
The console SHALL list the tournament's active payment-link rules, showing the transaction and the registrations each links, and SHALL mark those the matcher created automatically as distinct from those an organizer made by hand. The organizer SHALL be able to remove a link from this list, and removal SHALL unapply it.

#### Scenario: Manual link reviewed
- **WHEN** the organizer links a transaction by hand and reopens the Payments phase
- **THEN** the link appears in the payment-links card, attributed as manual

#### Scenario: Auto-created link distinguished
- **WHEN** the matcher creates a payment link automatically
- **THEN** it appears in the same card marked as auto-created

#### Scenario: Link removed
- **WHEN** the organizer removes a link from the card
- **THEN** the rule is deleted, the link is unapplied, and the card no longer lists it

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

### Requirement: Payments recorded by hand are listed and removable
The console SHALL list the tournament's payments recorded by hand as a view of its own beside the resolution queues, showing for each the fencer, the amount with its currency, the date it arrived, how it arrived, the note, and who recorded it. A view holding nothing SHALL say so in a single heading line, as the other views do.

The organizer SHALL be able to remove a payment from this list, and removal SHALL reverse exactly the amount it credited. The list SHALL state what removal will do before it is confirmed, because the reversal may unsettle a registration the roster already shows as paid.

#### Scenario: A recorded payment is reviewed
- **WHEN** the organizer records a payment and reopens the Payments phase
- **THEN** it appears in the recorded-payments view with its amount, date, method, note and the organizer who recorded it

#### Scenario: Nothing recorded
- **WHEN** the tournament has no payments recorded by hand
- **THEN** the view states that it is empty in a single heading line

#### Scenario: Removal unsettles a registration
- **WHEN** the organizer removes the recorded payment that had settled a registration
- **THEN** the reversal is stated before it is confirmed, the amount is subtracted, and the registration returns to reserved

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

### Requirement: The flagged queue names a hand-settled cause
WHERE a transaction is flagged because its registration is no longer reserved, the queue SHALL state whether that registration was settled by hand and, where it was, show the mark or the recorded payment that settled it. An organizer resolving the row is deciding whether the transaction is further money or the same money arriving twice, and that decision needs the earlier act in front of it.

#### Scenario: The earlier act is shown
- **WHEN** a transaction is flagged against a registration a recorded cash payment had settled
- **THEN** the flagged row states that the registration was settled by a payment recorded by hand, with its amount and date

#### Scenario: An ordinary conflict is unchanged
- **WHEN** a transaction is flagged against a registration paid by an earlier bank transaction
- **THEN** the row states that as it does today, with no hand-settled claim made
