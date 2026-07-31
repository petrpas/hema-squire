## MODIFIED Requirements

### Requirement: Payment identity via variable symbol
Each reservation SHALL receive a variable symbol that is unique across the whole deployment, not merely within its tournament. Transaction matching SHALL be performed exclusively by VS — or by the VS quoted in the payment message for transfers that cannot carry a VS field — never by payer name or amount alone.

A newly issued VS SHALL take the structured form `YYNNnnn`: two digits of the tournament's VS year, two digits of the tournament's series within that year, and three digits of registration sequence within that tournament. The value SHALL be seven digits with a leading nonzero digit, so that it survives banks that strip leading zeros and fits both the ten-digit domestic limit and the SPAYD variable-symbol field. Sequence allocation SHALL be per tournament and SHALL be correct when two registrations are created concurrently. Allocation SHALL fail with a clear error when a tournament exhausts its sequence rather than wrapping, truncating, or issuing a value that overruns into the series digits.

**The prefix is documentation, not routing.** Matching SHALL resolve a registration by looking up the complete VS value in a deployment-wide index, and SHALL take the tournament from the registration it resolved. It SHALL NOT parse the year or series digits to decide which tournament a transaction belongs to, because a payer who mistypes one digit would otherwise have their payment reconciled against a different event.

A VS issued before the structured format SHALL continue to match unchanged, and no already-issued VS SHALL ever be rewritten to the new format.

When a transaction's VS resolves to a registration belonging to a **different** tournament than the one being processed — the normal case when two tournaments share one bank account and each ingests the whole statement — the transaction SHALL be recorded as belonging to that other tournament and SHALL be excluded from this tournament's unmatched and flagged queues. It SHALL NOT mark any registration paid, SHALL NOT send any email, and SHALL NOT alter any registration state. The organizer SHALL be told how many transactions were set aside this way, so that a quiet queue is distinguishable from a queue that silently swallowed someone's payment.

#### Scenario: Third party pays for a fencer
- **WHEN** a transaction from a different sender carries a registration's VS
- **THEN** it matches that registration regardless of the sender's name

#### Scenario: Structured VS issued
- **WHEN** a fencer registers for the fifth tournament created for 2026 and is the third registration to it
- **THEN** the issued VS is 2605003

#### Scenario: Sequence is per tournament
- **WHEN** the first registration is created for each of two different tournaments in the same year
- **THEN** both carry sequence 001 and they differ only in their series digits

#### Scenario: Concurrent registrations get distinct symbols
- **WHEN** two fencers register for the same tournament at the same moment
- **THEN** each receives a different VS and neither registration fails

#### Scenario: Sequence exhaustion refused
- **WHEN** a tournament that has issued 999 variable symbols attempts to issue another
- **THEN** the registration is refused with a clear error and no eight-digit or overrunning value is issued

#### Scenario: Sibling tournament's payment is set aside, not queued
- **WHEN** a tournament ingests a statement containing a transaction whose VS belongs to another tournament's registration
- **THEN** the transaction is recorded as belonging to that other tournament, is absent from this tournament's unmatched queue, and no registration is marked paid and no email is sent

#### Scenario: Sibling payment matched by its own tournament
- **WHEN** the tournament that owns that registration ingests its own copy of the same transaction
- **THEN** the transaction matches normally and the registration is marked paid

#### Scenario: Set-aside count reported
- **WHEN** an ingestion sets transactions aside as belonging to other tournaments
- **THEN** the result reports how many were set aside, distinctly from matched, flagged, and unmatched counts

#### Scenario: Mistyped prefix does not route to a sibling
- **WHEN** a transaction carries a VS whose series digits name a different tournament but whose complete value matches no registration
- **THEN** the transaction enters the unmatched queue and no tournament is selected from its prefix

#### Scenario: Legacy variable symbol still matches
- **WHEN** a transaction carries a VS issued before the structured format
- **THEN** it resolves to its registration and matches exactly as it did before
