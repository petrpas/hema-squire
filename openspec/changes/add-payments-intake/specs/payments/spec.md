## MODIFIED Requirements

### Requirement: Bank transaction ingestion
The system SHALL ingest transactions via the Fio bank REST API on a schedule and via manual statement import. A manually imported statement SHALL be accepted whatever bank produced it, as a CSV or XLSX table, rather than only in the Fio export format. Ingestion SHALL be idempotent: each transaction is processed at most once, including where the statement carries no identifier of the bank's own.

#### Scenario: Overlapping statement re-import
- **WHEN** the organizer imports a statement overlapping already-ingested transactions
- **THEN** no transaction is matched or counted twice

#### Scenario: A statement from another bank
- **WHEN** the organizer imports a statement from a bank other than Fio
- **THEN** its credits are ingested as transactions and matched by the same rules as any other
