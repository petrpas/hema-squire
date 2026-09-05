# payments-intake Specification

## Purpose
Define how money reaches the console: a bank statement from any bank, the bank's
own feed where a token is configured, and the lifecycle passes on demand — every
intake action reachable from the Payments phase rather than from a scheduler the
organizer cannot see.

A statement no exact reader recognises is shaped by a model into the same rows a
Fio export produces, and every reading is stored per row, so re-importing the
same file asks nothing again. Fio keeps its deterministic parser: a format Squire
can read exactly is never guessed at.
## Requirements
### Requirement: Statement import accepts any bank's export
The console SHALL accept a bank statement as an uploaded CSV or XLSX file, whatever bank produced it, and SHALL derive the transactions from its rows without the organizer renaming columns or reshaping the file. A statement whose format the system recognises exactly SHALL be read by that exact reader; any other SHALL be read as a table and interpreted.

#### Scenario: A statement from a bank the system has never seen
- **WHEN** the organizer uploads a CSV export from a bank other than Fio, with its own column names and its own way of writing amounts
- **THEN** its credits are ingested as transactions, with the payer, amount, currency, date and variable symbol each taken from whichever column carries them

#### Scenario: A Fio export is read exactly, not interpreted
- **WHEN** the organizer uploads a Fio export
- **THEN** it is parsed by the exact Fio reader, and no language model is consulted

#### Scenario: A spreadsheet rather than a CSV
- **WHEN** the organizer uploads the statement as an XLSX file
- **THEN** it is read the same way as the CSV form

#### Scenario: Nothing to interpret with
- **WHEN** a non-Fio statement is uploaded on a deployment configured with no language model
- **THEN** the console states that it cannot interpret an unrecognised statement, and ingests nothing

### Requirement: Import is idempotent whatever the bank
Re-importing a statement SHALL NOT credit any transaction twice, including where the bank's export carries no identifier of its own. Where a row supplies no stable identifier, the system SHALL derive one from the row's own content, so that the same row read twice is recognised as the same transaction.

#### Scenario: The same file uploaded twice
- **WHEN** the organizer uploads the same non-Fio statement a second time
- **THEN** every row is counted as a duplicate and nothing is credited again

#### Scenario: A corrected statement re-uploaded
- **WHEN** the organizer re-uploads a statement with new rows appended to the ones already imported
- **THEN** only the new rows are ingested, and only they are interpreted afresh

### Requirement: Statement parsing is recorded work
Interpreting a statement SHALL be recorded as an operation of the tournament, started rather than awaited, so that it reports its progress, survives the organizer leaving the page, and is recovered if the process running it does not survive.

#### Scenario: A long statement and a closed tab
- **WHEN** the organizer uploads a long statement and closes the tab while it is being interpreted
- **THEN** the work continues to its end and the console reports its conclusion when reopened

#### Scenario: Another operation already running
- **WHEN** the organizer tries to import a statement while a table parse is running
- **THEN** the console states which work is under way instead of failing the import

### Requirement: Every intake action is reachable from the console
The Payments phase SHALL offer the organizer the statement import, a way to poll the bank's API where one is configured, and a way to run the payment lifecycle passes now. Each action SHALL state plainly when it is unavailable rather than offering a control that fails when used.

Each action SHALL also state, before it runs, what it will do that the organizer cannot undo. Where an intake would issue registrations for the fencer list, the console SHALL state how many rows it will issue registrations for, and — where Squire keeps the tournament's registrations — that variable symbols will be allocated and never reclaimed. This SHALL be stated in place, ahead of the action, rather than as a confirmation the organizer dismisses: the organizer reads it while deciding to act, not after having decided.

Where an intake would issue nothing, no such statement SHALL be made. A panel that announces a consequence on every visit teaches the organizer to stop reading it.

#### Scenario: No bank API token configured
- **WHEN** the tournament has no Fio token
- **THEN** the poll action is not offered, and the card says the tournament has no token configured

#### Scenario: Lifecycle run on the organizer's say-so
- **WHEN** the organizer runs the lifecycle passes after importing a statement
- **THEN** expiries, reminders and holding-payment events are applied immediately rather than at the scheduler's next sweep

#### Scenario: A statement that credits a waiting registration
- **WHEN** the organizer imports a statement carrying a payment for a reserved registration
- **THEN** that registration is settled and leaves the outstanding balance behind it, without any further action

#### Scenario: The organizer reads what the import will cost before uploading
- **WHEN** the organizer opens the intake panel on a tournament whose registrations Squire keeps, holding 54 rows without registrations
- **THEN** the panel states, before any upload, that importing will issue 54 registrations and allocate 54 variable symbols that are never reclaimed

#### Scenario: A manual tournament is told the count without the symbols
- **WHEN** the organizer of a tournament that keeps its own registrations opens the intake panel with rows awaiting issue
- **THEN** the panel states how many registrations the import will issue, and says nothing about variable symbols, since none is allocated

#### Scenario: Nothing to announce on a settled roster
- **WHEN** the organizer opens the intake panel on a tournament whose every row already has a registration
- **THEN** the panel states nothing about issuing

### Requirement: Intake issues registrations before it matches
Payment intake SHALL issue registrations for the fencer list as its first step,
before any transaction is matched. Importing a bank statement and polling the
bank's API SHALL each do so; running the lifecycle passes SHALL NOT, since they
move time rather than money and have nothing to reconcile.

This is where the roster becomes billable, and it is the only place. Matching
resolves a payment through `Registration.vs` and manual linking through a symbol
the organizer types, so both are meaningless against rows that state who is
competing and carry no registration. Issuing immediately before matching is
issuing at the moment the absence would otherwise bite, and it SHALL require no
action, no setting and no prior knowledge from the organizer
(`imported-registrations`).

The pass is idempotent, so an intake finding every row already issued SHALL do
nothing and SHALL NOT be slowed or reported as having acted. A fencer list that
gained rows between two intakes — by a later import or a manual entry — SHALL be
brought up to date by the next one.

Where the tournament's registrations are Squire's, issuing allocates variable
symbols from the tournament's sequence; where they are not, it allocates none.
Neither case changes what intake does with the transactions afterwards.

#### Scenario: A statement against a roster that has no registrations
- **WHEN** the organizer imports a statement on a tournament holding 54 imported rows and no registrations
- **THEN** 54 registrations are issued first, and the statement's transactions are then matched against them within the same operation

#### Scenario: Polling issues on the same terms
- **WHEN** the organizer polls the bank's API on a tournament whose fencer list holds rows without registrations
- **THEN** those rows are issued registrations before the polled transactions are matched

#### Scenario: A second intake issues nothing
- **WHEN** a second statement is imported against an unchanged fencer list
- **THEN** no registration is issued, every variable symbol and total from the first intake is unchanged, and only the statement's own rows are ingested

#### Scenario: A row entered between two statements
- **WHEN** a fencer is entered by hand after one statement has been imported, and a second statement is then imported
- **THEN** the new row is issued a registration by that second import

#### Scenario: The lifecycle passes issue nothing
- **WHEN** the organizer runs the payment lifecycle passes
- **THEN** no registration is issued and no variable symbol is allocated

### Requirement: Intake is refused while duplicates are pending
Payment intake SHALL refuse to run while any duplicate group is still pending the
organizer's verdict, and SHALL state the pending count as the reason rather than
failing obscurely. Nothing SHALL be ingested, issued or matched by a refused
intake.

Deduplication is a precondition of reconciling money, not of issuing. A merge
collapses rows, not registrations, so a registration issued before the verdict
survives the merge and leaves one person holding two — with nothing to collapse
them and a payment that can settle either. Refusing at intake makes that
unreachable by the order of the phases, and puts the refusal where the organizer
is already attempting the thing it protects.

The refusal SHALL name Deduplication as what resolves it, so the organizer is
sent somewhere rather than merely stopped.

#### Scenario: A statement uploaded with duplicates outstanding
- **WHEN** the organizer imports a statement while three duplicate groups are still pending review
- **THEN** the import is refused, the console states that three duplicates are awaiting a verdict and points at the Deduplication phase, and no transaction is ingested and no registration is issued

#### Scenario: Polling is refused on the same ground
- **WHEN** the organizer polls the bank's API while duplicate groups are pending
- **THEN** the poll is refused with the same reason, and nothing is ingested

#### Scenario: Intake proceeds once the verdicts are in
- **WHEN** the organizer resolves the last pending duplicate group and imports the statement again
- **THEN** the import runs, registrations are issued for the fencer list, and the transactions are matched

#### Scenario: A roster that never had duplicates
- **WHEN** the organizer imports a statement on a tournament whose deduplication produced no candidate groups at all
- **THEN** the import is not refused

