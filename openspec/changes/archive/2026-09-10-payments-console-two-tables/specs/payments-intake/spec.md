## ADDED Requirements

### Requirement: Only money arriving is ingested as a payment
Money **leaving** the account SHALL NOT be ingested as a payment, on every path
by which a statement reaches the console: the exact reader for a bank whose
format the system recognises, the bank's own feed where a token is configured,
and a statement interpreted as a table alike.

The drop SHALL happen at the one point every path passes through, so that the
rule holds by construction rather than by each reader remembering it. A reader
SHALL report a debit as the signed amount it is rather than hiding it, omitting
it, or turning it into a credit; deciding what a debit means is not a reader's
job.

A debit dropped this way SHALL NOT be counted as a duplicate. It is neither new
money nor money already seen, and reporting it as a duplicate would tell the
organizer their statement had been imported before.

An outgoing transfer is a refund the organizer sent, a fee, or money moved
elsewhere. None of them is somebody's entry fee, none can be credited to a
registration, and a negative payment that reached the console could never be
resolved and so would sit in it for the life of the tournament.

#### Scenario: The bank's own feed carries an outgoing transfer
- **WHEN** the tournament's account is polled and the window contains a transfer out of the account
- **THEN** no payment is ingested for it, and the poll's report counts it as neither new nor duplicate

#### Scenario: An exact export carries an outgoing transfer
- **WHEN** the organizer uploads an export from a bank the system reads exactly, containing both incoming payments and one transfer out
- **THEN** only the incoming payments are ingested

#### Scenario: A refund carrying the original symbol
- **WHEN** the organizer refunds an entry fee by copying the original payment, so the outgoing transfer carries that registration's variable symbol
- **THEN** no payment is ingested, and nothing is credited to or deducted from that registration

#### Scenario: An interpreted statement is held to the same rule
- **WHEN** a statement no exact reader recognises is interpreted and its rows include debits
- **THEN** the debits are reported by the reader and dropped before ingestion, exactly as on the exact paths

## MODIFIED Requirements

### Requirement: Statement import accepts any bank's export
The console SHALL accept a bank statement as an uploaded CSV or XLSX file, whatever bank produced it, and SHALL derive the transactions from its rows without the organizer renaming columns or reshaping the file. A statement whose format the system recognises exactly SHALL be read by that exact reader; any other SHALL be read as a table and interpreted. Whichever reader is used, only the credits become payments, as fixed by **Only money arriving is ingested as a payment**.

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
