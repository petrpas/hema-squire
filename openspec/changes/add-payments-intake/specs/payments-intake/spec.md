## ADDED Requirements

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

#### Scenario: No bank API token configured
- **WHEN** the tournament has no Fio token
- **THEN** the poll action is not offered, and the card says the tournament has no token configured

#### Scenario: Lifecycle run on the organizer's say-so
- **WHEN** the organizer runs the lifecycle passes after importing a statement
- **THEN** expiries, reminders and holding-payment events are applied immediately rather than at the scheduler's next sweep

#### Scenario: A statement that credits a waiting registration
- **WHEN** the organizer imports a statement carrying a payment for a reserved registration
- **THEN** that registration is settled and leaves the outstanding balance behind it, without any further action
