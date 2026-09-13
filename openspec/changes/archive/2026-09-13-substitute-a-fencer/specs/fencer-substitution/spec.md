## ADDED Requirements

### Requirement: A seat may change hands
The organizer SHALL be able to replace the fencer behind a row of the fencer list with another person, in one action, without removing the row and without entering a new one.

The row SHALL survive the substitution whole. The substitute SHALL take, unchanged: the row's **fixed number**, its **registration moment** and therefore its place in the order the list is sorted in, its **place above or below the line** in every discipline's substitute queue and in every team's waiting list, its **variable symbol**, its **stored total** in both currencies, its **disciplines and borrowed items**, its **note**, and everything **credited against it**.

No money SHALL move. The substitution SHALL append no credit, reverse none, write no waiver and issue no refund; what the two fencers settle between themselves is outside Squire. Where the tournament collects payments the seat therefore reads as paid, part-paid or unpaid exactly as it did before, because the derived sum over its journal is the same sum.

No clock SHALL start, restart or stop. A substitution SHALL NOT open a payment window, SHALL NOT reset an expiry, and SHALL NOT lift or impose dormancy: the seat keeps the lifecycle position it had.

What the substitute SHALL NOT inherit is what described the person rather than the seat: the replaced fencer's HEMA Ratings profile, nationality, club, rating and rank, and their account.

#### Scenario: The seat keeps its place and its money
- **WHEN** the organizer replaces a fencer whose registration is the eleventh on the list, carries VS 30114, and has been credited its full total
- **THEN** the row still stands eleventh with the same fixed number, the same VS and the same total, the substitute's name on it, and the seat still reads as paid

#### Scenario: A queued placement is inherited queued
- **WHEN** the organizer replaces a fencer whose longsword entry sits below the line
- **THEN** the substitute's longsword entry sits below the line in the same position, and nobody above it moves

#### Scenario: Nothing is charged and nothing refunded
- **WHEN** a substitution is made on a tournament that collects payments and the seat had been paid in full
- **THEN** the payment journal holds exactly the entries it held before, and no refund is recorded

#### Scenario: The window is not reopened
- **WHEN** the organizer replaces a fencer whose payment window has three days left to run
- **THEN** the window still has three days left to run and no new due date is set

#### Scenario: The profile is not inherited
- **WHEN** the organizer replaces a fencer bound to a HEMA Ratings profile with a substitute for whom no profile was chosen
- **THEN** the row carries no HEMA Ratings id, no rating and no rank, and the replaced fencer's profile stays with the replaced fencer

### Requirement: The substitute is named through the HEMA Ratings index
The substitution dialog SHALL find the substitute by name in the cached HEMA Ratings fighters index, through the same search the profile page and account creation use, so that a substitute who has a profile arrives with their canonical name, nationality and club already right.

A profile SHALL NOT be required. A name the index does not carry SHALL be accepted as typed, and the row SHALL then travel through matching exactly as a hand-entered row does: unmatched, and raised for the organizer's verdict like any other.

A substitute's name SHALL be required and SHALL NOT be blank, whether it came from a profile or was typed.

Where a profile is chosen, its canonical name, nationality and club SHALL be written onto the row, and the binding SHALL be a verdict — the substitute is bound to that profile, not merely proposed for it, because the organizer picked it by hand.

Ratings SHALL follow the profile from the snapshot the tournament already holds. Where no snapshot covers the substitute, their rating and rank SHALL stand empty until the next refresh, and this SHALL NOT be reported as a failure.

#### Scenario: Substitute found in the index
- **WHEN** the organizer searches the substitute's name and confirms a candidate
- **THEN** the row carries that profile's canonical name, nationality, club and HEMA Ratings id, and the match is settled rather than proposed

#### Scenario: Substitute absent from HEMA Ratings
- **WHEN** the organizer types a name the index does not carry and confirms it without a profile
- **THEN** the substitution is accepted, the row carries the typed name and no profile, and Matching on HR raises it for a verdict

#### Scenario: Blank name refused
- **WHEN** the organizer confirms the dialog with no name
- **THEN** the substitution is refused against the name field and the row is unchanged

#### Scenario: Rating arrives with the next refresh
- **WHEN** a substitute bound to a profile the tournament's latest snapshot does not cover is entered, and the export table is read
- **THEN** their rating and rank are empty, the snapshot reports no failure, and the next refresh fills them

### Requirement: An automatic tournament requires an address for the seat
WHEN the tournament is in automatic mode, the substitution dialog SHALL require an e-mail address, and SHALL state, where the organizer can read it before confirming, that word of the substitution goes to the address given.

The dialog SHALL ask for the substitute's own address by default, and SHALL offer the address the seat already carries as a value to keep **beneath** that field rather than as a choice above it. A substitute with an address of their own is the ordinary case; a club which entered three people under one address and keeps it is the exception, and an exception SHALL NOT be the default. Where the seat carries no address — an imported row that arrived without one — nothing is offered to keep and an address SHALL be typed.

WHEN the tournament is in manual mode, the address SHALL be optional, and the dialog SHALL say nothing about mail, because Squire sends none on such a tournament.

An address SHALL have the shape of an e-mail address or be refused against its own field, the rest of the dialog standing as typed.

#### Scenario: Address required in automatic mode
- **WHEN** the organizer confirms a substitution on an automatic tournament with the address field empty
- **THEN** it is refused against that field, and the dialog states that the substitution is mailed to the address given

#### Scenario: A new address is what the dialog asks for
- **WHEN** the organizer opens the dialog on a seat carrying an address
- **THEN** the address field is empty and ready to type into, and keeping the seat's own is offered unticked below it

#### Scenario: The existing address is kept
- **WHEN** the organizer chooses to keep the seat's current address
- **THEN** the seat keeps it, and word of the substitution goes there

#### Scenario: Nothing to keep on an address-less row
- **WHEN** the organizer opens the dialog on an imported row carrying no address, on an automatic tournament
- **THEN** no address is offered to keep and one must be typed

#### Scenario: Manual mode asks for no address
- **WHEN** the organizer substitutes on a manual tournament without giving an address
- **THEN** the substitution is accepted and nothing is said about mail

### Requirement: The address decides which account holds the seat
An address identifies an account **where it names the same person**. WHERE the address given belongs to a Squire account other than the replaced fencer's, and that account's name is the substitute's own, the seat SHALL be transferred to that account, and the substitute SHALL see it among their registrations.

Names SHALL be compared as the fighters index compares them — disregarding diacritics, case and word order, and not by containment — which is the comparison the issuing pass already makes for the same question.

WHERE the address belongs to an account carrying a **different** name, the seat SHALL NOT be transferred to it. On a roster entered by a parent or a club representative the address names the payer, and binding the seat to their record would enrol one person under another's name. The substitute SHALL become a fencer record without an account and the address SHALL be held as the seat's contact address.

WHERE that account already holds a registration on this tournament, the substitution SHALL be **refused with a stated reason** naming the conflict. One fencer holds one registration per tournament, and a substitution SHALL NOT be the path by which a second appears.

WHERE the address is the one the seat already carried — kept, or typed out again — the substitute SHALL become a fencer record without an account, and the address SHALL be held as the **seat's contact address** rather than as the substitute's login. Keeping an address SHALL NOT hand the seat back to the account that address belongs to; that is the whole point of keeping it.

WHERE the address belongs to no account at all, the substitute SHALL likewise become a fencer record without an account, carrying that address.

A substitution SHALL create no credentials and SHALL NOT invite anybody to create an account.

#### Scenario: Seat transferred to an existing account
- **WHEN** the substitute's address belongs to a Squire account of the same name, holding no registration on this tournament
- **THEN** the seat moves to that account and appears among that fencer's registrations

#### Scenario: An address under another name is a contact, not an identity
- **WHEN** the substitute's address belongs to an account carrying a different name
- **THEN** the substitute is recorded without an account, the seat carries that address as its contact, and the other account is untouched

#### Scenario: Refused where the account is already entered
- **WHEN** the substitute's address belongs to an account that already holds a registration on this tournament
- **THEN** the substitution is refused, the reason names that the substitute is already entered, and both registrations stand unchanged

#### Scenario: A kept address is a contact, not a login
- **WHEN** the organizer keeps the address of a fencer who registered in the application
- **THEN** the substitute is recorded without an account, the seat keeps that address as its contact, and the replaced fencer's account no longer holds the seat

#### Scenario: An unknown address makes no account
- **WHEN** the substitute's address belongs to no account
- **THEN** the seat carries the address, no account is created, and no invitation is sent

### Requirement: Both parties are told, once each
WHEN the tournament is in automatic mode, the substitution SHALL send two messages: one to the substitute, stating the tournament, what the seat carries — its disciplines and borrowed items — and whether anything is still owed on it; and one to the replaced fencer, naming who has taken their place.

WHERE something is still owed, the substitute's message SHALL state the outstanding amount, the account and the variable symbol, with the QR codes every other payment message carries. WHERE nothing is owed, it SHALL say so, and SHALL NOT print an amount of zero as though it were a bill.

The replaced fencer's message SHALL state that the seat is no longer theirs and that Squire refunds nothing; it SHALL NOT print the substitute's address.

WHERE the two addresses are the same — the kept address — one message SHALL be sent, the substitute's, and not two.

WHEN the tournament is in manual mode, **no message SHALL be sent**, whatever addresses are held, in keeping with Squire running nothing against such a tournament.

#### Scenario: Two messages, two addresses
- **WHEN** a substitution gives a new address on an automatic tournament
- **THEN** the substitute is written to about what they have inherited and the replaced fencer is written to about who took their place

#### Scenario: One address, one message
- **WHEN** the organizer keeps the seat's current address
- **THEN** one message goes to it, addressed to the substitute, and no second copy is sent

#### Scenario: An unpaid seat is inherited with its bill
- **WHEN** a substitution is made on a seat still owing 600 CZK
- **THEN** the substitute's message states 600 CZK, the account, the variable symbol and the QR code

#### Scenario: A paid seat is inherited without a bill
- **WHEN** a substitution is made on a seat that has been paid in full
- **THEN** the substitute's message says nothing is owed and states no amount to pay

#### Scenario: Manual tournaments send nothing
- **WHEN** a substitution is made on a manual tournament for which both addresses are known
- **THEN** no message is sent to either

### Requirement: A substitution is recorded, readable and reversible
A substitution SHALL persist as a rule in the fencer list's manual-edits log, alongside every other manual action. Its entry SHALL name **both fencers** — who was replaced and who took the place — so that the log answers who is on the roster and why without another source being consulted.

Withdrawing the rule SHALL return the seat to the fencer it was taken from, restoring their name, profile, nationality, club and account binding, and the seat's address as it stood. The seat's number, order, symbol, total and credits SHALL be untouched by the withdrawal, as they were by the substitution.

Withdrawal SHALL send no mail. A message already sent SHALL NOT be unsent, and the console SHALL say so where the withdrawal is offered rather than leaving the organizer to assume the news was recalled.

A seat MAY be substituted more than once. Each substitution SHALL be its own rule, and withdrawing one SHALL return the seat to whoever held it when that rule was made.

#### Scenario: The log names both
- **WHEN** the organizer opens the fencer list's manual-edits log after a substitution
- **THEN** an entry states the row, the fencer replaced and the fencer who took the place

#### Scenario: Withdrawal restores the fencer
- **WHEN** the organizer withdraws a substitution
- **THEN** the replaced fencer holds the seat again with their profile, club and account, and the seat's number, symbol, total and credits are unchanged

#### Scenario: Withdrawal does not recall the mail
- **WHEN** the organizer moves to withdraw a substitution on an automatic tournament
- **THEN** the console states that the messages already sent stand, and withdrawing sends none

#### Scenario: Twice substituted
- **WHEN** a seat is substituted, then substituted again, and the second substitution is withdrawn
- **THEN** the first substitute holds the seat

### Requirement: What a substitution may not be done to
A substitution SHALL be refused on a row that is **deleted** and on a row a **merge has absorbed**. A deleted row offers to be restored, not to be handed on; an absorbed row is not a seat of its own.

A substitution SHALL be refused on a **draft** tournament, as every other manual action on the fencer list is. The console states a draft's wait rather than offering the table's actions, and a substitution SHALL NOT be the one action that reaches through that gate.

A substitution SHALL be refused where the substitute would be the fencer already on the row.

#### Scenario: Not on a deleted row
- **WHEN** the organizer opens the actions of a row deleted on the fencer list
- **THEN** restoration is offered and substitution is not

#### Scenario: Not on an absorbed row
- **WHEN** deduplication has merged a row into another and the organizer reads the Import view
- **THEN** the absorbed row offers no substitution

#### Scenario: Refused on a draft
- **WHEN** a substitution is posted against a row of an unpublished tournament
- **THEN** it is refused for want of publication, exactly as every other rule on that tournament is
