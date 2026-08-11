## MODIFIED Requirements

### Requirement: Reservation lifecycle
A reservation's lifecycle SHALL depend on the tournament's payment mode, and SHALL be governed by two independent clocks that produce two different outcomes:

- The **payment window** is the interval between money being requested and money being due, configured per tournament in days. It belongs to one registration. A reservation whose payment window passes unpaid SHALL expire, freeing any capacity it held and leaving the fencer outside the substitute queue.
- The **seating deadline** is a single date for the whole tournament, on which seating settles. A reservation still owing money when the seating deadline passes SHALL be moved to the substitute queue — it SHALL NOT expire, and it SHALL keep its place in registration order.

The seating deadline SHALL NOT be expressed as a payment window on individual registrations, so that the expiry of a payment window can never release a seat that the seating deadline would have queued.

**Both clocks SHALL be dormant while the tournament's payments feature is off.** Such a registration SHALL be seated on the same capacity terms as any other, SHALL carry no due date, SHALL open no payment window, and SHALL never expire for non-payment. Its total SHALL still be computed and presented, as a statement of what the tournament costs rather than a demand, and it SHALL be presented to the fencer as confirmed rather than as awaiting payment. No payment mode SHALL apply to it: the mode describes how money is collected, and no money is being collected.

A registration taken while payments were off SHALL NOT acquire a due date retroactively when the payments feature is turned on. It SHALL remain seated and SHALL NOT expire on account of a window that never opened; what becomes of it is the organizer's decision.

Per mode, on a tournament whose payments feature is on, a seated reservation SHALL be held as follows:

- **immediate** — the full amount is owed at registration and a payment window opens. Unpaid at the end of it, the reservation expires.
- **deposit** — the deposit is owed at registration and a payment window opens for it. Crediting the deposit SHALL close the payment window, leaving the balance owed by the seating deadline. Unpaid at the end of the payment window, the reservation expires; deposit paid but balance unpaid at the seating deadline, it is moved to the substitute queue.
- **reservation** — nothing is owed at registration and no payment window opens. The seat is held until the seating deadline, by which the full amount is owed.

A paid reservation SHALL become a confirmed registration in every mode.

An expired reservation SHALL NOT bar the fencer from the tournament. A fencer whose reservation has expired SHALL be able to register again on the same terms as a fencer who cancelled: the existing registration is reused in place, a fresh window opens where the mode calls for one, and a fresh VS is issued. Capacity SHALL be re-evaluated at that moment like any new registration, so a discipline that filled in the meantime places the returning fencer in the substitute queue rather than seating them. The number of such cycles SHALL NOT be limited.

#### Scenario: Reservation expires unpaid
- **WHEN** the payment window passes with no matched payment
- **THEN** the reservation expires automatically, its discipline capacity is freed, and the fencer is notified

#### Scenario: Payment arrives in time
- **WHEN** a matching payment is ingested before the payment window closes
- **THEN** the reservation becomes a confirmed registration

#### Scenario: Deposit closes the payment window
- **WHEN** a deposit-mode reservation is credited its deposit on day 3 of a 5-day payment window
- **THEN** the payment window closes, the reservation does not expire on day 5, and the balance is owed by the seating deadline

#### Scenario: Free reservation holds without a payment window
- **WHEN** a fencer registers in reservation mode
- **THEN** nothing is owed, no payment window opens, and the seat is held until the seating deadline

#### Scenario: Payments-off registration is seated outright
- **WHEN** a fencer registers for a tournament whose payments feature is off
- **THEN** the registration is seated with no due date and no payment window, its total is shown as information, and it is presented as confirmed

#### Scenario: Payments-off registration never expires
- **WHEN** the scheduler runs against a payments-off tournament long after any configured payment window would have closed
- **THEN** no registration expires, no capacity is freed, and no expiry notice is sent

#### Scenario: Turning payments on does not expire what came before
- **WHEN** a tournament that took registrations with payments off turns payments on and the scheduler runs
- **THEN** those registrations remain seated, none expires, and none is sent an expiry notice

#### Scenario: Re-registration after expiry with seats free
- **WHEN** a fencer whose reservation expired registers again while the selected disciplines have free places
- **THEN** the registration is accepted, reusing the existing row with a fresh window and a fresh VS, and a confirmation email with payment instructions is sent

#### Scenario: Re-registration after expiry into a full discipline
- **WHEN** a fencer whose reservation expired registers again for a discipline that has since filled
- **THEN** that discipline is entered as a substitute placement rather than seated, and no waiting substitute is displaced

#### Scenario: Repeated expiry not penalized
- **WHEN** a fencer's reservation expires unpaid for the second time and they register again
- **THEN** the registration is accepted on the same terms as the first time

### Requirement: Confirmation email with QR payment
On registration for a tournament whose payments feature is on, the system SHALL send a localized confirmation email containing the registration summary — items with quantities and option values — the total amount with its currency, the bank account, the VS, and an SPAYD-format QR code encoding amount, currency, account, VS, and message. When the tournament prices in EUR as a second currency, the email SHALL additionally carry the EUR total and a second QR code denominated in EUR against the same account.

**On a tournament whose payments feature is off, the confirmation email SHALL carry the summary and the total and nothing about paying it**: no bank account, no variable symbol, no QR code, no expiry date and no payment instruction. It SHALL confirm the registration rather than request money, and where the organizer has written registration instructions those SHALL be the tournament's own statement of how it is settled. No reminder, expiry notice, surcharge or payment-received mail SHALL be sent for such a tournament, because nothing generates one.

Each discipline entered SHALL be summarized by its name alone. The email SHALL NOT carry discipline slugs, which are not fencer-facing text (`discipline-identity`); where a tournament offers several disciplines classified alike, the name is what tells the fencer which one they entered.

Each QR code SHALL encode the stored total of its own currency, with the SPAYD currency field taken from that currency. No amount in either QR code SHALL be produced by conversion.

The account SHALL be stated in the same form as the in-app instructions: a Czech account as its domestic form together with its IBAN, any other account as its IBAN alone. The two surfaces SHALL NOT differ in how they present one account, because a fencer comparing the email against the page must not have to work out whether they are looking at the same thing. The QR code SHALL continue to encode the IBAN whatever form the email states, since the payment descriptor admits no other.

#### Scenario: QR payment
- **WHEN** the fencer scans the QR code from the confirmation email in a banking app
- **THEN** the prefilled payment carries the exact amount, currency, account, and VS needed for automatic matching

#### Scenario: Czech account stated in both forms
- **WHEN** a confirmation email goes out for a tournament whose account is Czech
- **THEN** it states the domestic form and the IBAN, while the QR code encodes the IBAN

#### Scenario: Email and page agree
- **WHEN** a fencer compares their confirmation email against the in-app payment instructions
- **THEN** the account is presented identically in both

#### Scenario: Disciplines summarized by name
- **WHEN** a fencer registers for two disciplines
- **THEN** the email lists each by its name alone, with no slug alongside it

#### Scenario: Tiers legible in the summary
- **WHEN** a fencer registers for one of two longsword disciplines that differ only by name
- **THEN** the email names the one they entered, and it is distinguishable from the one they did not

#### Scenario: EUR QR carries the stored EUR total
- **WHEN** a CZK + EUR tournament confirms a reservation totalling 1500 Kč and 60 €
- **THEN** the email carries a CZK QR for 1500 and a EUR QR for 60, each with its own currency in the SPAYD currency field

#### Scenario: No EUR block in single-currency mode
- **WHEN** a tournament prices in one currency
- **THEN** the email carries exactly one amount and one QR code

#### Scenario: Payments-off confirmation carries no payment block
- **WHEN** a fencer registers for a payments-off tournament totalling 1200 Kč
- **THEN** the email states the summary and the total, and carries no account, no VS, no QR code and no expiry date

#### Scenario: No payment mail for a payments-off tournament
- **WHEN** the scheduler runs against a payments-off tournament holding registrations of every age
- **THEN** no reminder, expiry notice, surcharge or payment-received mail is sent

#### Scenario: Emailed amounts stable against configuration changes
- **WHEN** the organizer changes prices or the recorded ratio after a confirmation email was sent
- **THEN** the reminder and the in-app instructions for that reservation state the same amounts and carry the same QR codes as the original confirmation
