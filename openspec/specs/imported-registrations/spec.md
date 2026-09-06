# imported-registrations Specification

## Purpose
TBD - created by archiving change issue-imported-registrations. Update Purpose after archive.
## Requirements
### Requirement: Registrations are issued as a step of payment intake
Rows that merely state who is competing SHALL be turned into registrations that
can be paid for automatically, as the first step of every payment intake:
importing a bank statement and polling the bank's API SHALL each issue
registrations for the fencer list before any transaction is matched. No action
that issues registrations SHALL be offered to the organizer, and no surface SHALL
require them to know that issuing exists in order to reconcile a payment.

Issuing SHALL still not run when a file is imported or a row is entered by hand —
a row is not enrolled by arriving — and SHALL NOT run as part of the lifecycle
passes, which move time rather than money.

The pass is idempotent (see "Issuing again changes nothing already issued"), so
every intake after the first issues nothing and a roster that gained rows between
two statements SHALL be brought up to date by the next intake without any further
action.

**Where the tournament's payments are boned out** — Squire collects nothing, so
the Payments phase offers no intake (`etl-console`) — registrations SHALL be
issued instead when the organizer opens the Payments phase, once deduplication
has concluded. Such a tournament allocates no variable symbols at all, so the
pass creates the fencer, the registration, its entries and its frozen price and
nothing scarce is spent.

**Deduplication SHALL be a precondition of matching rather than of issuing.**
Payment intake SHALL refuse to run while any duplicate group is pending the
organizer's verdict, and SHALL state that as the reason (fixed by
`payments-intake`). A merge collapses rows, not registrations, so a registration
issued before the verdict survives the merge and leaves one person holding two.
Enforcing this at intake means issuing can never be reached with a verdict
outstanding, and the organizer meets the refusal while attempting the thing it
protects rather than two phases earlier.

**The console SHALL state, before an intake that will issue, how many rows it
will issue registrations for**, and — where Squire keeps the registrations — that
variable symbols will be allocated and never reclaimed. This SHALL be stated in
place, ahead of the action, rather than as a confirmation the organizer dismisses.

**A variable symbol SHALL be issued only where Squire keeps the tournament's
registrations** (`tournament-mode`). A symbol is a shortcut Squire tells a fencer to
quote so a payment can find its registration without anybody reading the
message — never the registration's identity; on a manual tournament it has told
them nothing, since they registered through the organizer's own form and paid
against whatever that form said. A symbol minted afterwards would appear on no
statement and match no transaction, while consuming a number from a sequence
that is unique across the deployment and never reused. On a manual tournament the
registration SHALL be created with its price, its entries and its dormant clocks,
and with no symbol.

A registration carrying no symbol SHALL be reconciled by the payer's own words
instead, as fixed by `name-assisted-matching`. No surface SHALL read the absence
of a symbol as the absence of a registration.

#### Scenario: A statement import makes the roster billable first
- **WHEN** the organizer imports a bank statement on a tournament holding 54 imported rows and no registrations
- **THEN** registrations are issued for those rows before any transaction is matched, and the statement's payments are matched against them in the same operation

#### Scenario: Polling the bank issues too
- **WHEN** the organizer polls the bank's API on a tournament whose fencer list has rows without registrations
- **THEN** those rows are issued registrations before the polled transactions are matched

#### Scenario: No issuing action is offered anywhere
- **WHEN** the organizer moves through the console's phases
- **THEN** no phase offers an action that issues registrations

#### Scenario: A roster that grew catches up by itself
- **WHEN** a fencer is entered by hand after one statement has been imported, and a second statement is imported
- **THEN** the new row is issued a registration by the second import, without any separate action

#### Scenario: A tournament Squire collects nothing for
- **WHEN** the organizer of a tournament whose payments feature is off opens the Payments phase with deduplication concluded
- **THEN** its imported rows are issued registrations, carrying their prices and their dormant clocks, and none carries a variable symbol

#### Scenario: Pending duplicates stop the money
- **WHEN** the organizer imports a statement while duplicate groups are still pending review
- **THEN** the import is refused, states that the duplicates must be resolved first, and no registration is issued and no payment is matched

#### Scenario: The organizer is told what the import will do
- **WHEN** the organizer opens the intake panel on a tournament with 54 rows without registrations, whose registrations Squire keeps
- **THEN** the panel states, before the upload, that importing will issue 54 registrations and allocate variable symbols that are never reclaimed

#### Scenario: Import of a fencer list alone issues nothing
- **WHEN** a file of fencers is imported and parsed
- **THEN** no registration is created and no variable symbol is allocated

#### Scenario: The lifecycle passes issue nothing
- **WHEN** the organizer runs the payment lifecycle passes by hand
- **THEN** no registration is issued

#### Scenario: A manual tournament's roster carries no symbols
- **WHEN** registrations are issued for fifty imported rows on a tournament whose registrations the organizer keeps
- **THEN** fifty registrations are created with their prices and their dormant clocks, none carries a variable symbol, and none is drawn from the tournament's sequence

#### Scenario: Roster becomes billable
- **WHEN** registrations are issued for a fencer list of imported rows that have none
- **THEN** each row gains a registration, the outstanding amount for each row appears in the fencer list, and a variable symbol is carried only where Squire keeps the registrations

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

On a tournament that prices by items, what the row borrows and the afterparty it
takes SHALL be issued as selections of those items, so that they are priced as
the tournament prices them. A borrowed item the tournament lends nothing by that
name SHALL be billed nothing and SHALL be named on the row, so that a total
short by an unpriced item can be seen rather than only computed. Where several
items offer an afterparty, a row's bare yes SHALL NOT be resolved to one of
them: it does not say which, and billing an evening nobody picked is worse than
billing none.

#### Scenario: Early bird priced at the fencer's own moment
- **WHEN** a row registered before the early-bird deadline is issued a registration after that deadline has passed
- **THEN** its total is the early-bird price

#### Scenario: A later fee change does not move an issued total
- **WHEN** a discipline's fee is raised after registrations have been issued
- **THEN** every already-issued registration owes exactly what it owed before

#### Scenario: Extras are priced with the disciplines
- **WHEN** a row entering one discipline also borrows a weapon and takes the afterparty
- **THEN** its total is the discipline fee plus the rental fee plus the afterparty fee, each at the row's own moment

#### Scenario: Rentals are priced where the tournament prices by items
- **WHEN** a row borrowing two of a tournament's rental items is issued a registration
- **THEN** the registration holds a selection of each item and its total includes both their prices

#### Scenario: A borrowed item nothing lends is named on the row
- **WHEN** a row borrows an item the tournament offers under no name
- **THEN** nothing is billed for it, and the row states that item as one nothing prices

#### Scenario: An afterparty nobody can name is not guessed
- **WHEN** a row says it takes the afterparty on a tournament offering two of them
- **THEN** neither is billed

#### Scenario: A row with no discipline is not issued
- **WHEN** the list holds a row that entered no discipline
- **THEN** no registration is issued for it, and the intake operation's conclusion names it as skipped with the reason

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
The pass SHALL be safe to run repeatedly, which is what allows it to run on every intake. A row that already has a
registration SHALL be left exactly as it is: its variable symbol, its total, its
credited amount and its state SHALL NOT change, and no second registration SHALL
be created for it.

A list gaining rows after an issuing pass — by a later import or a manual entry —
SHALL be brought up to date by the next intake, which SHALL issue registrations
for the new rows only.

**The pass SHALL report what it did through the conclusion of the operation that
ran it**: how many registrations it issued, how many rows it left alone because
they already had one, and every row it skipped, named, with its reason. The
skipped rows are not an aside — each is a fencer whose payment cannot reconcile
until the row is fixed, and the organizer SHALL be able to see which without
reading the fencer list twice.

Where the pass runs on entering a boned-out Payments phase, and there is no
operation to carry it, the report SHALL be stated on that phase.

#### Scenario: Rerun on an unchanged list does nothing
- **WHEN** two statements are imported in succession on an unchanged fencer list
- **THEN** the second run issues nothing, and every variable symbol and total from the first run is unchanged

#### Scenario: A later import is caught up
- **WHEN** a second fencer file is imported and deduplicated after registrations were issued, and a statement is then imported
- **THEN** only the rows from the second file are issued registrations

#### Scenario: A credited registration is not disturbed
- **WHEN** a further statement is imported after some issued registrations have been paid
- **THEN** their credited amounts and paid states are unchanged

### Requirement: What a row must have to be issued
A fencer-list row SHALL be issued a registration where it states a name and at
least one discipline. It SHALL NOT be refused for anything else about its
contents.

A row SHALL NOT be required to carry an e-mail address, and SHALL NOT be refused
because another row carries the same one. Neither is a defect in the row: a
roster is routinely entered by one person for several — a parent, a club
representative — and the address is that person's. The fencer record such a row
needs is created on the tournament's behalf, holds no credentials and is never
written to (`fencer-accounts`), so it needs no address of its own.

The reasons a row can be skipped SHALL therefore describe the row rather than
the system's bookkeeping: no name, because there is no fencer to make; and no
discipline, because the registration would total zero, read as settled, and
quietly absorb a payment.

Every reason a row was skipped SHALL be reported, named, wherever the skipped
rows are stated — the enrolment's own report and the surfaces that ask what the
next enrolment would leave alone.

#### Scenario: Two rows on one address are both issued
- **WHEN** registrations are issued for a list in which a parent's address appears on two fencers' rows
- **THEN** both rows are issued registrations, and neither is reported as skipped

#### Scenario: A row carrying no address is issued
- **WHEN** a row states a name and a discipline but no e-mail address
- **THEN** it is issued a registration

#### Scenario: A row with no discipline is still refused
- **WHEN** the list holds a row that entered no discipline
- **THEN** no registration is issued for it, and it is reported as skipped with that reason

#### Scenario: A row with no name is still refused
- **WHEN** the list holds a row that states no name
- **THEN** no registration is issued for it, and it is reported as skipped with that reason

