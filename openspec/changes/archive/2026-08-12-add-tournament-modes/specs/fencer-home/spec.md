## MODIFIED Requirements

### Requirement: In-app payment instructions
WHEN the tournament's payments feature is on and the account holds an unpaid reservation for it, the detail page SHALL display the payment instructions: total amount, bank account (IBAN), variable symbol, the instruction to quote the VS in the payment message for transfers without a VS field, the reservation expiry date, and an SPAYD QR code. The QR code and the full transfer details SHALL always be shown together.

WHEN the tournament's payments feature is off, no payment instructions SHALL be shown for any registration it holds, whatever that registration owes on paper. There is no account to quote, no variable symbol in use and no expiry to state, and showing a partial set would tell the fencer to do something the tournament is not asking of them.

#### Scenario: Payment panel after registering
- **WHEN** a fencer completes a registration for a payments-enabled tournament
- **THEN** the page shows the QR code alongside IBAN, amount, VS, and the VS-in-message instruction, and states when the reservation expires

#### Scenario: No instructions for a payments-off tournament
- **WHEN** a fencer opens the detail page of a payments-off tournament they are registered for
- **THEN** no payment instructions, account, variable symbol, QR code or expiry date is shown

## ADDED Requirements

### Requirement: A payments-off registration presents no money to settle
WHEN the tournament's payments feature is off, the detail page SHALL present the fencer's registration as confirmed rather than as reserved awaiting payment, and SHALL state no expiry date and no outstanding balance. The selected disciplines, teams and extra services SHALL still be listed with their amounts and total, aligned as `Registration management` fixes, because what the tournament costs is information the fencer needs.

Cancellation SHALL be offered as usual. Its confirmation SHALL ask for confirmation alone, with no mention of refunds, because Squire has taken nothing to refund. Amendment, the roster editor and the queue positions SHALL be unaffected by the payments feature.

#### Scenario: Registration reads as confirmed
- **WHEN** a fencer opens a registration on a payments-off tournament
- **THEN** it is presented as confirmed, with no expiry date, no outstanding balance and no payment prompt

#### Scenario: Amounts still shown
- **WHEN** that registration holds two disciplines and an extra service
- **THEN** each is listed with its amount and the total closes the column, exactly as on a payments-enabled tournament

#### Scenario: Cancellation mentions no money
- **WHEN** a fencer cancels a registration on a payments-off tournament
- **THEN** the confirmation asks only whether to cancel, saying nothing about refunds

#### Scenario: Rosters unaffected
- **WHEN** a fencer who entered a team on a payments-off tournament opens their registration
- **THEN** the team is listed with its roster and the roster editor is offered as usual
