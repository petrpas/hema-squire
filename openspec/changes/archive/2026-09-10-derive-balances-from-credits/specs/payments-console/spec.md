## MODIFIED Requirements

### Requirement: Payment resolution views
The Payments phase SHALL present the organizer's payment work as six views in the phase's main area, stacked above the fencer table: flagged transactions, unmatched transactions, reservations that expired while holding credited money, active payment links, the transactions holding a live credit, and the payments recorded by hand. The phase's rail SHALL hold only the operation's parameters and the manual-edits log, as every other phase's rail does. Each view SHALL load independently of the others and of the table. A view with nothing to show SHALL say so rather than disappear, and SHALL take no more room than its own heading while it has nothing to show.

#### Scenario: Nothing outstanding
- **WHEN** the organizer opens the Payments phase on a tournament where nothing has been credited, nothing awaits resolution and nothing was recorded by hand
- **THEN** each of the six views states that it is empty in a single heading line, and the fencer table begins directly below them

#### Scenario: Work sits above the ledger
- **WHEN** the tournament has transactions awaiting resolution
- **THEN** those views appear above the fencer table, and the table below still lists every registration with its payment state

#### Scenario: One view fails to load
- **WHEN** the expired-holding request fails while the others succeed
- **THEN** that view reports its own failure, and the remaining five and the fencer table still render their data

## ADDED Requirements

### Requirement: Credited transactions are listed and reversible
The console SHALL list every transaction holding a live credit, showing the date, the payer, the amount with its currency, and every registration that transaction credited — not only the one the matcher resolved it to, since one transaction may credit several.

The view exists because such a transaction is in none of the resolution queues. The matcher resolved it, so it is neither unmatched nor flagged, and a credit an automatic VS match decided leaves no payment link to list it under. Without this view the only credited transaction the console could see was one an organizer had linked by hand, which is the one case that already had a way back.

The organizer SHALL be able to reverse a transaction's credit from this list. Reversing SHALL release every live credit that transaction made and return it to the unmatched queue. The action SHALL state its consequence before it is confirmed, naming the registrations that stop reading as paid, or stating plainly that none does. That statement SHALL be asked of the current state rather than read from the listing, because whether a registration reads as paid is a derivation and the listing may be older than the answer; the confirmation SHALL NOT be offered until it has been obtained.

Which transactions hold credit SHALL be answered from the credit journal and not from the transaction's matched registration or its queue status: what a transaction credited is what its live entries say.

#### Scenario: An automatically matched transaction is listed
- **WHEN** a transaction is credited to a registration by an automatic VS match
- **THEN** it appears in the credited view with its date, payer, amount and the fencer it credited, though it sits in no queue and no payment link names it

#### Scenario: A transaction covering three registrations names all three
- **WHEN** the credited view lists a transaction that credited three registrations
- **THEN** all three fencers are named on its row

#### Scenario: The consequence is stated before it is confirmed
- **WHEN** the organizer opens the reversal action on a transaction whose credit is the whole of what settled a registration
- **THEN** that registration is named as one that will stop reading as paid, and nothing is reversed until the organizer confirms

#### Scenario: Nothing stops reading as paid
- **WHEN** the organizer opens the reversal action on a transaction whose registrations remain settled without it
- **THEN** the action states that no registration stops reading as paid

#### Scenario: A reversal empties the row from the view
- **WHEN** the organizer confirms the reversal
- **THEN** the credits are reversed, the transaction returns to the unmatched queue, and it no longer appears in the credited view

#### Scenario: An uncredited transaction is not listed
- **WHEN** a transaction carries no VS that resolves and has been credited to nobody
- **THEN** it does not appear in the credited view
