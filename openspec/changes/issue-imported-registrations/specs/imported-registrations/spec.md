## ADDED Requirements

### Requirement: Issuing registrations for the fencer list
The organizer SHALL be able to issue registrations for the fencer list in one
action, turning rows that merely state who is competing into registrations that
can be paid for. The action SHALL be offered on the Fencers phase and nowhere
else, and SHALL NOT run automatically when a file is imported or a row is
entered by hand.

The action SHALL be offered only once deduplication has concluded. A row that a
pending merge may collapse SHALL NOT be issued a registration first: a variable
symbol is unique across the deployment and is never reused, so issuing one to a
row that is about to be merged away spends an identifier on a record that will
not exist.

The action SHALL state, before it runs, how many rows it will issue
registrations for, and SHALL state that no mail will be sent.

#### Scenario: Roster becomes billable
- **WHEN** the organizer issues registrations for a fencer list of imported rows that have none
- **THEN** each row gains a registration carrying a variable symbol, and the outstanding amount for each row appears in the fencer list

#### Scenario: Not offered before deduplication has concluded
- **WHEN** duplicate groups are still pending the organizer's review
- **THEN** the issuing action is not offered

#### Scenario: Import alone issues nothing
- **WHEN** a file is imported and parsed
- **THEN** no registration is created and no variable symbol is allocated

#### Scenario: The organizer is told the size of the action
- **WHEN** the organizer opens the issuing action against a list of 54 rows without registrations
- **THEN** the confirmation states that 54 registrations will be issued and that no mail will be sent

### Requirement: What an issued registration is worth
An issued registration's total SHALL be computed from the row's own answers —
the disciplines it entered, the items it borrows, and the afterparty where it
takes one — priced as the tournament prices them.

The total SHALL be computed **at the row's own registration moment**, not at the
moment of issuing. Early-bird pricing SHALL therefore apply exactly as it applied
when the fencer registered, and a roster issued after an early-bird deadline has
passed SHALL NOT thereby become more expensive than it was.

The total SHALL be stored on the registration when it is issued, and SHALL NOT be
recomputed on read. A later change to a discipline's fee, to an extra's fee or to
the early-bird deadline SHALL NOT move what an already-issued registration owes.

A row that states no discipline SHALL NOT be issued a registration, and SHALL be
reported as such rather than issued with a total of zero.

#### Scenario: Early bird priced at the fencer's own moment
- **WHEN** a row registered before the early-bird deadline is issued a registration after that deadline has passed
- **THEN** its total is the early-bird price

#### Scenario: A later fee change does not move an issued total
- **WHEN** a discipline's fee is raised after registrations have been issued
- **THEN** every already-issued registration owes exactly what it owed before

#### Scenario: Extras are priced with the disciplines
- **WHEN** a row entering one discipline also borrows a weapon and takes the afterparty
- **THEN** its total is the discipline fee plus the rental fee plus the afterparty fee, each at the row's own moment

#### Scenario: A row with no discipline is not issued
- **WHEN** the list holds a row that entered no discipline
- **THEN** no registration is issued for it, and the action reports it as skipped with the reason

### Requirement: Capacity does not apply to an issued registration
Every discipline an issued registration enters SHALL be entered as a seated
placement, whatever that discipline's capacity says and however many
registrations already hold it. An issued registration SHALL NOT be placed in the
substitute queue by the act of issuing.

A fencer list is a record of who is competing, not a queue of applicants. The
rows were admitted by whoever ran the registration — often a season before the
tournament was entered into Squire at all — and re-deciding that against a
capacity figure would queue people who have already fenced. It would also make
them free: a substitute placement is not billed, so an over-subscribed roster
would issue registrations owing nothing, which is the opposite of what issuing is
for.

Issuing MAY therefore leave a discipline holding more seated placements than its
capacity. That capacity SHALL continue to govern everyone else: a fencer
registering afterwards into a discipline the roster has filled SHALL be placed in
the substitute queue exactly as they would be behind any other full discipline.

#### Scenario: The roster is seated whole
- **WHEN** registrations are issued for forty-eight rows entering a discipline whose capacity is forty-two
- **THEN** all forty-eight placements are seated, and every one of them is billed

#### Scenario: Nobody is queued by being issued
- **WHEN** a registration is issued for a row entering a discipline that is already full
- **THEN** its placement is seated rather than queued

#### Scenario: Capacity still governs a later registration
- **WHEN** a fencer registers in the application for a discipline the issued roster has filled
- **THEN** they are placed in the substitute queue, as they would be behind any full discipline

### Requirement: An issued registration's clocks never start
An issued registration SHALL have both lifecycle clocks dormant, permanently and
by virtue of its origin. It SHALL carry no due date, SHALL open no payment
window, SHALL NOT expire for non-payment, and SHALL never be sent a payment
reminder or an expiry notice.

Its dormancy SHALL NOT depend on the tournament's configuration and SHALL NOT be
lifted by any later change to it. Turning the payments feature on or off,
changing the payment mode, setting or moving the seating deadline, and running
the lifecycle passes by hand SHALL all leave an issued registration seated and
silent.

Its total SHALL still be computed, stored and presented — as a statement of what
the tournament costs rather than a demand — and it SHALL still be matchable,
linkable and creditable, because what is dormant is the passage of time, not the
money.

#### Scenario: The scheduler passes an issued registration by
- **WHEN** the lifecycle passes run against a tournament holding issued registrations long after any configured payment window would have closed
- **THEN** none of them expires, no capacity is freed, and no expiry notice or reminder is sent

#### Scenario: Running the lifecycle by hand sends nothing
- **WHEN** the organizer runs the lifecycle passes from the console against a roster of unpaid issued registrations
- **THEN** no mail is sent to any of them

#### Scenario: Configuration changes do not wake the clocks
- **WHEN** the payments feature is turned on, or the payment mode or seating deadline is changed, after registrations have been issued
- **THEN** the issued registrations remain seated, acquire no due date, and are sent nothing

#### Scenario: Dormant clocks do not stop money
- **WHEN** a payment quoting an issued registration's variable symbol is ingested
- **THEN** it is matched and credited exactly as it would be for an in-app registration

### Requirement: A fencer record without an account
Issuing a registration for a row that has no fencer record SHALL create one, on
the tournament's behalf. The record SHALL hold no credentials, SHALL NOT be sent
an invitation or any other mail, and SHALL NOT become an account the person can
log into by its creation alone.

Where the row has been matched to a HEMA Ratings profile and the organizer has
reached a verdict on that match, the created record SHALL carry that binding. An
unresolved or proposed match SHALL NOT be bound: the fencer list's evidence
register is not a decision, and a record created here SHALL NOT claim a profile
that no one has confirmed.

#### Scenario: Fencer created silently
- **WHEN** a registration is issued for a row that has no fencer record
- **THEN** a fencer record is created, no credentials exist for it, and no mail is sent

#### Scenario: Confirmed HR match carries over
- **WHEN** a registration is issued for a row whose HEMA Ratings match the organizer has confirmed
- **THEN** the created fencer record carries that HR id

#### Scenario: Unconfirmed match is not claimed
- **WHEN** a registration is issued for a row whose HEMA Ratings match is only proposed
- **THEN** the created fencer record carries no HR id

### Requirement: Issuing again changes nothing already issued
The action SHALL be safe to run repeatedly. A row that already has a
registration SHALL be left exactly as it is: its variable symbol, its total, its
credited amount and its state SHALL NOT change, and no second registration SHALL
be created for it.

A list gaining rows after an issuing pass — by a later import or a manual entry —
SHALL be brought up to date by running the action again, which SHALL issue
registrations for the new rows only.

The action SHALL report what it did: how many registrations it issued, how many
rows it left alone because they already had one, and how many it skipped with
the reason.

#### Scenario: Rerun on an unchanged list does nothing
- **WHEN** the organizer runs the issuing action twice in succession
- **THEN** the second run issues nothing, and every variable symbol and total from the first run is unchanged

#### Scenario: A later import is caught up
- **WHEN** a second file is imported and deduplicated after registrations were issued, and the action is run again
- **THEN** only the rows from the second file are issued registrations

#### Scenario: A credited registration is not disturbed
- **WHEN** the action is run again after some issued registrations have been paid
- **THEN** their credited amounts and paid states are unchanged
