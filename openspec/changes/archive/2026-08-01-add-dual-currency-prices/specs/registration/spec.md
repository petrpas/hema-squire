## MODIFIED Requirements

### Requirement: Amounts presented in the tournament's currency
Every amount presented to a fencer — row prices, the running total, the registration total, and payment instructions — SHALL be rendered from a stored price or a stored total together with the currency it is denominated in. When the tournament prices in EUR as a second currency, each presented figure SHALL additionally show the EUR figure, taken from the EUR price or the EUR total. No presented amount SHALL be produced by converting another amount at an exchange ratio. No EUR figure SHALL be presented when the tournament does not price in EUR, and no second figure SHALL be presented when the local currency is already EUR. No user-facing string SHALL contain a hardcoded currency unit.

A registration SHALL store a total per configured currency, computed when the registration is created. A subsequent change to any configured price or to the recorded exchange ratio SHALL NOT alter a stored total.

#### Scenario: Both figures shown from stored prices
- **WHEN** a CZK + EUR tournament presents a registration totalling 1500 Kč and 60 €
- **THEN** both figures are presented from the stored totals and neither is computed from the other

#### Scenario: No EUR figure in single-currency mode
- **WHEN** a tournament prices in CZK only
- **THEN** every amount is presented in CZK only

#### Scenario: EUR-priced tournament shows one figure
- **WHEN** a tournament's local currency is EUR
- **THEN** amounts are presented in EUR once, with no second currency figure

#### Scenario: Ratio change moves nothing
- **WHEN** the organizer changes the recorded exchange ratio after a reservation exists
- **THEN** that reservation's presented totals in both currencies are unchanged

#### Scenario: Price change does not move an existing registration
- **WHEN** the organizer raises a discipline price after a reservation exists
- **THEN** that reservation's stored totals are unchanged in both currencies

### Requirement: Confirmation email with QR payment
On registration the system SHALL send a localized confirmation email containing the registration summary — items with quantities and option values — the total amount with its currency, the bank account, the VS, and an SPAYD-format QR code encoding amount, currency, account, VS, and message. When the tournament prices in EUR as a second currency, the email SHALL additionally carry the EUR total and a second QR code denominated in EUR against the same account.

Each QR code SHALL encode the stored total of its own currency, with the SPAYD currency field taken from that currency. No amount in either QR code SHALL be produced by conversion.

#### Scenario: QR payment
- **WHEN** the fencer scans the QR code from the confirmation email in a banking app
- **THEN** the prefilled payment carries the exact amount, currency, account, and VS needed for automatic matching

#### Scenario: EUR QR carries the stored EUR total
- **WHEN** a CZK + EUR tournament confirms a reservation totalling 1500 Kč and 60 €
- **THEN** the email carries a CZK QR for 1500 and a EUR QR for 60, each with its own currency in the SPAYD currency field

#### Scenario: No EUR block in single-currency mode
- **WHEN** a tournament prices in one currency
- **THEN** the email carries exactly one amount and one QR code

#### Scenario: Emailed amounts stable against configuration changes
- **WHEN** the organizer changes prices or the recorded ratio after a confirmation email was sent
- **THEN** the reminder and the in-app instructions for that reservation state the same amounts and carry the same QR codes as the original confirmation

### Requirement: In-app payment instructions retrieval
The system SHALL provide, to the owning account only, the payment data for its unpaid reservation: total amount with its currency, bank account (IBAN), variable symbol, payment message, reservation expiry, and the SPAYD QR code — plus the EUR total and a EUR-denominated QR code when the tournament prices in EUR as a second currency. Every amount SHALL be a stored total and every QR code SHALL encode the stored total of its own currency. The content SHALL be identical to the confirmation email's. The EUR fields SHALL be absent, not empty, when they do not apply.

#### Scenario: Owner retrieves payment data
- **WHEN** the fencer who holds an unpaid reservation requests its payment instructions
- **THEN** the amount with its currency, IBAN, VS, message, expiry, and QR code are returned

#### Scenario: EUR pair present only when applicable
- **WHEN** payment instructions are requested on a CZK + EUR tournament and again on a CZK-only one
- **THEN** the first response carries the EUR total and EUR QR and the second omits both fields entirely

#### Scenario: Instructions match the original email after a configuration change
- **WHEN** prices or the recorded ratio change and the fencer then retrieves their payment instructions
- **THEN** the amounts and QR codes returned are the ones from their confirmation email

#### Scenario: Other accounts denied
- **WHEN** a different account requests those payment instructions
- **THEN** the request is rejected

### Requirement: Price preview
The system SHALL compute the total price for a hypothetical selection (disciplines and extra services with quantities and option values) for a tournament without creating a registration, using the same pricing engine — itemized pricing with discounts, or the legacy fee fields for legacy tournaments — that applies at registration time, evaluated as of the current date. The preview SHALL return a total per configured currency, each summed from that currency's prices by the same computation the registration will use.

#### Scenario: Preview matches registration
- **WHEN** a price preview is requested for a selection and the same selection is then submitted as a registration at the same date
- **THEN** the previewed totals equal the registration's computed totals in every configured currency

#### Scenario: Preview carries both totals
- **WHEN** a price preview is requested on a CZK + EUR tournament
- **THEN** the response carries the CZK total and the EUR total, each summed from its own prices

#### Scenario: Preview in single-currency mode
- **WHEN** a price preview is requested on a tournament pricing in one currency
- **THEN** the response carries exactly one total
