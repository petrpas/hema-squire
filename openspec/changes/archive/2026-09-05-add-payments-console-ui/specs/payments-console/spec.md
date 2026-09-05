## ADDED Requirements

### Requirement: Payment resolution views
The Payments phase SHALL present the organizer's payment work as four views in the phase's main area, stacked above the fencer table: flagged transactions, unmatched transactions, reservations that expired while holding credited money, and active payment links. The phase's rail SHALL hold only the operation's parameters and the manual-edits log, as every other phase's rail does. Each view SHALL load independently of the others and of the table. A view with nothing to show SHALL say so rather than disappear, and SHALL take no more room than its own heading while it has nothing to show.

#### Scenario: Nothing outstanding
- **WHEN** the organizer opens the Payments phase on a tournament where every transaction matched cleanly
- **THEN** each of the four views states that it is empty in a single heading line, and the fencer table begins directly below them

#### Scenario: Work sits above the ledger
- **WHEN** the tournament has transactions awaiting resolution
- **THEN** those views appear above the fencer table, and the table below still lists every registration with its payment state

#### Scenario: One view fails to load
- **WHEN** the expired-holding request fails while the others succeed
- **THEN** that view reports its own failure, and the remaining three and the fencer table still render their data

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

#### Scenario: Payment credited, reservation expired
- **WHEN** a reservation expires while holding a credited payment
- **THEN** it appears in the expired-holding list with the credited amount and the expiry time

#### Scenario: Ordinary expiry excluded
- **WHEN** a reservation expires having received no payment
- **THEN** it does not appear in the expired-holding list

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
