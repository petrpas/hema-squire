## ADDED Requirements

### Requirement: Hand-recorded payments and waivers survive an export
The canonical JSON document SHALL carry every payment an organizer recorded by hand — its registration, amount, currency, the date the money arrived, how it arrived, the note, who recorded it and when — and SHALL carry each registration's settled-by-hand mark with the reason given for it.

Both are load-bearing. A registration's credited amount may now include money no ingested transaction explains, and its paid state may stand on nothing but a person's word; a document that carried the consequence without the cause would restore a payment state that could not be audited, corrected or reversed. A restore SHALL reconstruct the credited counters and the paid state exactly as they stood, and SHALL NOT replay a recorded payment as a fresh credit on top of the counters the document already carries.

Removed records SHALL NOT be exported: what the document reconstructs is the state, and a payment that has been reversed contributes none.

The document version SHALL be raised for this addition. Documents produced before it SHALL remain loadable, restoring with no hand-recorded payments and no marks — which is what those tournaments held.

#### Scenario: Cash payment round-trips
- **WHEN** a tournament holding a registration settled by a recorded cash payment is exported and re-imported into an empty deployment
- **THEN** the registration is restored paid with the same credited amount, and the recorded payment is restored beside it with its date, method, note and recorder

#### Scenario: Waiver round-trips
- **WHEN** a tournament holding a waived registration is exported and re-imported
- **THEN** that registration is restored paid, settled by hand with its reason, and with both credited counters at zero

#### Scenario: A restore does not double the credit
- **WHEN** a document carrying a registration credited 1750 and one recorded payment of 1750 is restored
- **THEN** the registration holds 1750, not 3500

#### Scenario: Older document still loads
- **WHEN** a document produced before this addition is restored
- **THEN** it loads, no registration is marked settled by hand, and no hand-recorded payment exists
