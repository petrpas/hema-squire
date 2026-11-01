## MODIFIED Requirements

### Requirement: Foreign transfers without a VS field
Payment instructions for foreign payers SHALL request the VS in the payment message, and ingestion SHALL capture every text-bearing field the bank provides — the message, the payer's own reference or user identification, any comment or specification field, and the specific symbol — so that matching can search all of them. Matching SHALL NOT restrict its search to the message field alone.

A VS SHALL be recognized in two ways. A token explicitly labelled as a variable symbol SHALL be matched on the number, wherever in those fields it appears. A **bare numeric token** carrying no label SHALL be matched automatically only when it both resolves to an issued VS and the transaction covers that registration's outstanding balance within tolerance; a bare token that resolves to an issued VS but whose amount does not agree SHALL be offered to the organizer as a pre-filled candidate rather than matched or credited. Fields that hold structured identifiers rather than payer text — the payer's name and account number — SHALL NOT be searched for bare tokens.

Where the tournament accepts EUR, the foreign payer SHALL be given a EUR amount and a EUR QR code in the EPC format against the tournament's configured IBAN and account holder, as fixed by **A payment code's format follows its currency**. The VS travels in that code's remittance text, labelled, so matching finds it in the message like any other labelled VS. Foreign payments that still fail to match SHALL be resolved manually; the system MAY suggest candidates by name and amount, but only a human confirms the match.

#### Scenario: SEPA payment with VS in the message
- **WHEN** a SEPA transaction carries the VS in its message text
- **THEN** it matches automatically like a domestic VS payment

#### Scenario: Labelled VS outside the message field
- **WHEN** a transaction carries a labelled VS in its user-identification field and its message is empty
- **THEN** the VS is found and the transaction matches

#### Scenario: Bare number with the right amount matches
- **WHEN** a transaction's text carries the bare number 2605003 with no label, that VS is issued, and the amount covers that registration's outstanding within tolerance
- **THEN** the registration is marked paid without organizer action

#### Scenario: Bare number with an unrelated amount becomes a candidate
- **WHEN** a transaction's text carries a bare number matching an issued VS but its amount does not cover that registration's outstanding within tolerance
- **THEN** the transaction is not matched and not credited, and the organizer is offered it as a pre-filled candidate

#### Scenario: Payer name not scanned for bare tokens
- **WHEN** a transaction's payer name or account number contains a digit sequence that happens to match an issued VS
- **THEN** it is not treated as a variable symbol

#### Scenario: Foreign payer receives a EUR amount
- **WHEN** a fencer registers for a CZK tournament that has EUR payments enabled
- **THEN** the payment instructions state a EUR amount and offer a EUR QR code in the EPC format against the same IBAN

## ADDED Requirements

### Requirement: A payment code's format follows its currency
Every payment QR code SHALL be encoded in the format the banks of its currency's payers read. A code denominated in **EUR** SHALL be an **EPC QR code** (the European Payments Council's SEPA credit transfer code, version `002`, UTF-8): service tag `BCD`, identification `SCT`, no BIC, the account holder as beneficiary name, the tournament's IBAN, the amount as `EUR` followed by the amount with a dot and at most two decimals, no purpose and no structured reference, and as remittance text the payment message — the VS labelled as `VS` followed by the tournament's display name — cut to the 140 characters the format allows. A code denominated in any other currency SHALL be a SPAYD string, as before. This SHALL hold for every code Squire produces — confirmation, amendment, reminder, promotion and the in-app payment instructions — and for a EUR-only tournament's single code as much as for the second code of a local + EUR one.

No EUR code SHALL be produced without an account holder: the EPC format requires a beneficiary name, and a code without one is refused by the payer's bank. Where no holder is recorded, the payment instructions SHALL still state the EUR amount, the IBAN and the VS in text, and SHALL carry no EUR code rather than one that fails.

#### Scenario: A EUR code is an EPC code
- **WHEN** a CZK + EUR tournament held by "TJ Šerm Praha" with VS 2601004 confirms a reservation totalling 1500 Kč and 60 €
- **THEN** the CZK code is a SPAYD string with `CC:CZK`, and the EUR code is an EPC code beginning `BCD`, version `002`, naming "TJ Šerm Praha", the IBAN and `EUR60`, with remittance text beginning `VS2601004`

#### Scenario: EUR-only tournament
- **WHEN** a tournament whose only currency is EUR sends payment instructions
- **THEN** its one code is an EPC code

#### Scenario: Remittance text fits the format
- **WHEN** a tournament's display name would make the payment message longer than 140 characters
- **THEN** the remittance text is cut to 140 characters and still begins with the labelled VS

#### Scenario: A paid EPC transfer matches by its VS
- **WHEN** a SEPA transfer made from the EUR code arrives with its remittance text in the message field
- **THEN** the labelled VS is found and the transaction matches as any labelled VS does

#### Scenario: No holder, no EUR code
- **WHEN** a published tournament taking EUR has no account holder recorded
- **THEN** its payment instructions state the EUR amount, the IBAN and the VS, and carry no EUR code
