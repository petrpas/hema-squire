## ADDED Requirements

### Requirement: Reconciliation applies only where payments are enabled
Every behaviour this capability fixes — transaction ingestion, automatic and manual matching, partial payments, multi-registration payments, the amount tolerance, reminders, expiry notices and the handling of payments arriving after expiry — SHALL apply only to a tournament whose payments feature is on, as fixed by `tournament-modes`. A tournament with the feature off has no money in flight for Squire to reconcile.

Ingestion SHALL NOT attribute a transaction to a payments-off tournament, and a request to reconcile, match, link or ingest against one SHALL be refused with a clear reason rather than accepted and silently doing nothing — an organizer uploading a statement against the wrong tournament must learn that, not watch it disappear.

Everything already reconciled SHALL be retained when the feature is turned off: credited payments, ingested transactions, payment events, issued variable symbols and the recorded tolerance. Turning the feature back on SHALL resume reconciliation with all of them present and with no replay, reissue or renumbering of anything already settled.

#### Scenario: No ingestion against a payments-off tournament
- **WHEN** an organizer uploads a bank statement against a tournament whose payments feature is off
- **THEN** the request is refused with a reason naming the payments feature, and no transaction is stored against that tournament

#### Scenario: Manual linking refused
- **WHEN** a request tries to link a transaction to a registration of a payments-off tournament
- **THEN** it is refused rather than accepted with no effect

#### Scenario: Reconciled money survives the feature being turned off
- **WHEN** an organizer turns payments off on a tournament holding credited payments and ingested transactions
- **THEN** every payment, transaction and payment event is retained unchanged, and no registration's paid state is altered

#### Scenario: Reconciliation resumes on the same data
- **WHEN** that organizer turns payments back on
- **THEN** the Payments phase shows the same transactions, the same credited payments and the same tolerance as before, with nothing replayed and no variable symbol reissued
