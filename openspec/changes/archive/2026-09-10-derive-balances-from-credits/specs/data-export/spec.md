## MODIFIED Requirements

### Requirement: Hand-recorded payments and waivers survive an export
The canonical JSON document SHALL carry every payment an organizer recorded by hand — its registration, amount, currency, the date the money arrived, how it arrived, the note, who recorded it and when — and SHALL carry both payment journals: every credit with its amount, currency, arrival day, origin, the source row that carried it and its reversal where it has one, and every waiver with its reason, who granted it and who revoked it.

Both are load-bearing. What a registration has been credited is the sum of its live credits, and whether it is settled may stand on nothing but a person's word; a document that carried the consequence without the cause would restore a payment state that could not be audited, corrected or reversed. A restore SHALL reconstruct the journals as they stood and SHALL NOT replay a recorded payment as a fresh credit on top of the credit journal that already carries it.

A credit SHALL name the row that carried it, and SHALL be restored only where that row travelled in the same document. A credit whose source did not travel SHALL NOT be restored: a credit that cannot say where it came from is the one thing the journal exists to prevent.

Removed records SHALL NOT be exported: what the document reconstructs is the state, and a payment that has been reversed contributes none.

The document version SHALL be raised for this addition. A document produced before it SHALL remain loadable where it carries no payment state — restoring with no credit, no waiver and no hand-recorded payment, which is what those tournaments held. A document produced before it that **does** carry a credited amount or a settled-by-hand mark SHALL be refused, naming that as the reason. Such a document records a total whose composition was never kept — which payment, from where, arriving when — and there is no honest way to reconstruct the credits it was the sum of; restoring it with the payments silently dropped would be worse than refusing it.

#### Scenario: Cash payment round-trips
- **WHEN** a tournament holding a registration settled by a recorded cash payment is exported and re-imported into an empty deployment
- **THEN** the registration is restored paid with the same credit against it, and the recorded payment is restored beside it with its date, method, note and recorder

#### Scenario: Waiver round-trips
- **WHEN** a tournament holding a waived registration is exported and re-imported
- **THEN** that registration is restored paid, waived with its reason, and holding no credits

#### Scenario: A restore does not double the credit
- **WHEN** a document carrying one recorded payment of 1750 and the credit it wrote is restored
- **THEN** the registration holds 1750, not 3500

#### Scenario: Older document with no payments still loads
- **WHEN** a document produced before this addition, in which nothing was credited and nothing waived, is restored
- **THEN** it loads, no registration is waived, and no hand-recorded payment exists

#### Scenario: Older document carrying a credited amount is refused
- **WHEN** a document produced before this addition carries a registration with a credited amount, or with a settled-by-hand mark
- **THEN** the restore is refused with that as the stated reason, and no tournament is created
