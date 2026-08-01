## MODIFIED Requirements

### Requirement: Amount tolerance
A VS-matched transaction SHALL be credited to the registration its VS identifies, **in the currency the transaction is denominated in**, and that currency's state SHALL then be decided from the **total credited to it in that same currency** rather than from that transaction alone. Several transfers carrying one VS in the same currency — an installment, a correction after an underpayment, a transfer a bank has split, or a payment covering an amendment surcharge — SHALL therefore settle a registration between them.

The amount due in a currency SHALL be that currency's total less the amount already credited to the registration in that same currency, so that a registration amended upward after payment is owed the difference and one amended downward carries an overpayment rather than appearing settled. **No conversion SHALL occur at any point in the payment path,** and no exchange ratio SHALL be consulted. A transaction in a currency the tournament does not price in SHALL be flagged with a distinct not-accepted reason rather than compared as if the amounts were commensurable, and SHALL NOT be credited.

Once credited, the registration SHALL be marked paid when the amount still due in that currency falls within the tournament's configured tolerance (default ±5 %) of zero, absorbing bank fees and payer rounding — it is no longer required to absorb any difference between an organizer's recorded ratio and a payer's bank's rate, because neither reaches the comparison. A registration still owing more than the tolerance allows in that currency SHALL remain reserved with its credited amount recorded, and its transaction SHALL be recorded as a partial payment rather than flagged — there is nothing for the organizer to resolve about money that is simply not all there yet. A registration credited beyond the tolerance in the other direction SHALL be treated as overpaid in that currency and routed to refund tracking.

Amounts credited to a registration SHALL be recorded per currency, and SHALL NOT be summed across currencies — doing so would require an exchange ratio the payment path does not use. A registration SHALL be settled when the amount credited in **either** currency covers that currency's total within tolerance; a registration part-paid in each of two currencies SHALL be flagged for the organizer rather than aggregated. Reverting a manual payment link SHALL remove exactly the amount that link credited, from the currency it credited.

#### Scenario: Local-currency payment slightly short
- **WHEN** a payment in the tournament's local currency arrives 3 % below the amount due in that currency with the correct VS
- **THEN** the registration is marked paid

#### Scenario: EUR payment matched against the stored EUR total
- **WHEN** a CZK tournament with EUR payments enabled receives a 60 EUR transaction carrying the VS of a reservation whose EUR total is 60
- **THEN** it is compared against the stored EUR total with no conversion, falls within tolerance, and the registration is marked paid

#### Scenario: Two half-payments in the same currency settle one registration
- **WHEN** two CZK transactions of 900 and 850 carrying the same VS are ingested against a reservation whose local total is 1750
- **THEN** both are credited to the local counter, the amount still due in that currency reaches zero, and the registration is marked paid

#### Scenario: Half-payments arriving in separate statements
- **WHEN** the first half-payment is ingested in one statement and the second in a later one, in the same currency
- **THEN** the registration is marked paid on ingestion of the second, without organizer action

#### Scenario: Unpriced currency flagged with its own reason
- **WHEN** a VS-matched transaction arrives in a currency the tournament does not price in
- **THEN** the transaction is flagged with a not-accepted reason, is not compared numerically against any total, and nothing is credited to the registration

#### Scenario: Amount far off is a partial payment, not a flag
- **WHEN** a payment with a correct VS arrives 40 % below the amount due in its own currency
- **THEN** it is credited to that currency's counter, the reservation stays reserved with the balance recorded, and the transaction is recorded as a partial payment rather than flagged

#### Scenario: Overpayment flagged
- **WHEN** a payment with a correct VS credits a registration more than the tolerance beyond its total in that currency
- **THEN** the excess is recorded and the registration is routed to refund tracking

#### Scenario: Credited amount recorded in its own currency
- **WHEN** a transaction is matched to a registration
- **THEN** the amount credited in that transaction's currency increases by the transaction's amount, the other currency's credited amount is unchanged, and the audit entry records the amount and its currency

#### Scenario: Credits not summed across currencies
- **WHEN** a registration owing 1500 Kč or 60 € receives 750 Kč and then 30 €
- **THEN** neither currency's credit covers its own total, the payments are not combined, and the registration is flagged for the organizer

#### Scenario: Either currency settles the registration
- **WHEN** a registration owing 1500 Kč or 60 € is credited 60 € across one or more transactions
- **THEN** it is marked paid, and no local-currency balance is treated as outstanding

#### Scenario: Reverted link removes its credit
- **WHEN** the organizer removes a manual payment link that had credited a registration
- **THEN** the amount credited in that link's currency returns to what it was before the link was applied

### Requirement: Automatic matching outcome
WHEN a transaction settles a reservation within tolerance, the system SHALL mark the registration paid, confirm its capacity, send a payment confirmation email, update the public participant list, and record the match in the audit trail. Transactions with an unknown or missing VS SHALL enter an unmatched queue.

Each matching pass SHALL evaluate newly ingested transactions **and** re-evaluate transactions that remain flagged, so that a transaction flagged before the rest of its payment arrived is resolved when that payment lands. A transaction the organizer has explicitly resolved — manually linked, marked for refund, or recorded as belonging to another tournament — SHALL NOT be re-evaluated, and no automatic pass SHALL override an organizer's decision. The system SHALL record when each transaction was last evaluated, so that a transaction leaving the queue between passes is explicable.

#### Scenario: Clean match
- **WHEN** a scheduled Fio poll ingests a transaction with a known VS and a valid amount
- **THEN** the reservation becomes paid and the fencer appears on the public list without organizer action

#### Scenario: Flagged transaction resolved by a later pass
- **WHEN** a transaction flagged as overpaid is re-evaluated after an amendment raised the registration's total
- **THEN** it is reconsidered and settles the registration without organizer action

#### Scenario: Organizer decision not overridden
- **WHEN** a matching pass runs over a transaction the organizer marked for refund
- **THEN** the transaction is left exactly as the organizer left it

### Requirement: Manual matching
The organizer SHALL be able to link an unmatched transaction to one or more registrations in the Payments phase. The link SHALL persist as a rule (surviving reruns and re-ingestion) and SHALL support one payer covering multiple registrations.

A link covering several registrations SHALL **distribute** the transaction's amount across them, crediting each registration the amount it is due and never more than the transaction holds. It SHALL NOT credit the full transaction amount to every registration it covers, which would record money that never arrived and present every covered registration as overpaid. The amount credited to each registration SHALL be recorded on the rule when it is applied, so that removing the rule reverses exactly what it did rather than what it would do against today's balances.

#### Scenario: One transfer covers two fencers
- **WHEN** the organizer links a single transaction to two registrations
- **THEN** both registrations are marked paid and the link is recorded as a removable rule

#### Scenario: Amount distributed, not multiplied
- **WHEN** the organizer links a transaction of 3500 to two registrations each owing 1750
- **THEN** each registration is credited 1750, both are marked paid, and neither is recorded as overpaid

#### Scenario: Removing a distributed link reverts every registration
- **WHEN** the organizer removes a link that had covered three registrations
- **THEN** each of the three has exactly the amount that link credited removed, and none retains a partial credit

### Requirement: Foreign transfers without a VS field
Payment instructions for foreign payers SHALL request the VS in the payment message, and ingestion SHALL capture every text-bearing field the bank provides — the message, the payer's own reference or user identification, any comment or specification field, and the specific symbol — so that matching can search all of them. Matching SHALL NOT restrict its search to the message field alone.

A VS SHALL be recognized in two ways. A token explicitly labelled as a variable symbol SHALL be matched on the number, wherever in those fields it appears. A **bare numeric token** carrying no label SHALL be matched automatically only when it both resolves to an issued VS and the transaction covers that registration's outstanding balance within tolerance; a bare token that resolves to an issued VS but whose amount does not agree SHALL be offered to the organizer as a pre-filled candidate rather than matched or credited. Fields that hold structured identifiers rather than payer text — the payer's name and account number — SHALL NOT be searched for bare tokens.

Where the tournament accepts EUR, the foreign payer SHALL be given a EUR amount and a EUR-denominated SPAYD QR against the tournament's configured IBAN. Foreign payments that still fail to match SHALL be resolved manually; the system MAY suggest candidates by name and amount, but only a human confirms the match.

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
- **THEN** the payment instructions state a EUR amount and offer a EUR-denominated QR code against the same IBAN

## ADDED Requirements

### Requirement: Partial payments
A payment that credits a registration less than it owes SHALL leave the reservation reserved, with the credited amount recorded and the remaining balance derivable from it. The fencer SHALL be told what is still outstanding, with its currency, rather than being left to work the difference out from a total and a payment they may not have recorded.

A partial payment SHALL NOT change the reservation's validity window. A reservation holding a partial payment SHALL expire on its original schedule like any other.

Because that expiry leaves the organizer holding money for a reservation that no longer exists, a reservation expiring with a credited amount SHALL be recorded under a distinct audit event, SHALL be presented to the organizer separately from ordinary expiries, and its expiry notice to the fencer SHALL state that the payment is held by the organizer who will be in contact. The notice SHALL NOT imply the money is lost, and SHALL NOT promise a seat.

#### Scenario: Partial payment leaves the reservation reserved
- **WHEN** a transaction credits 900 against a reservation owing 1750
- **THEN** the reservation stays reserved, 900 is recorded against it, and 850 is outstanding

#### Scenario: Fencer told the outstanding balance
- **WHEN** a partial payment is credited to a reservation
- **THEN** the fencer is notified of the amount still outstanding with its currency

#### Scenario: Partial payment does not extend the window
- **WHEN** a partial payment is credited on day 9 of a 10-day validity window
- **THEN** the reservation still expires at the end of day 10

#### Scenario: Expiry holding money is recorded distinctly
- **WHEN** a reservation carrying a partial payment expires
- **THEN** a distinct audit event records that it expired holding a credited amount, and the organizer sees it separately from ordinary expiries

#### Scenario: Expiry notice explains the held payment
- **WHEN** a reservation carrying a partial payment expires
- **THEN** the fencer's expiry notice states that the payment is held by the organizer who will be in contact, without implying the money is lost or promising a seat

#### Scenario: Remaining balance arriving in grace settles it
- **WHEN** the rest of the amount arrives within the tournament's expiry grace period and the discipline still has a free place
- **THEN** the reservation is reinstated, the credited amounts together settle the total, and the registration is marked paid

### Requirement: Multi-registration payments
When a transaction's text carries several distinct issued variable symbols, the system SHALL treat it as a payment covering all of those registrations rather than as an unmatched transaction. Amounts due SHALL be summed **in the transaction's own currency** — each registration's outstanding balance in that currency, never a conversion of its balance in the other. Where that sum matches the transaction within tolerance, the system SHALL mark them all paid and SHALL record the coverage as a payment link rule of the same kind the organizer creates manually — removable, replayable, and reverting every registration it touched when removed. The rule SHALL record that it was created automatically, so the organizer can see why several registrations were settled at once.

Where the sum does not match within tolerance, the transaction SHALL be presented in the manual matching interface with the detected variable symbols already filled in, rather than as a bare unmatched row. The system SHALL NOT search for a subset of the detected symbols whose amounts happen to sum correctly, which would be a guess about the payer's intent.

#### Scenario: Club transfer settles six registrations
- **WHEN** one transaction carries six issued variable symbols and its amount matches the sum of those six registrations' amounts due within tolerance
- **THEN** all six are marked paid and a removable payment link rule records the coverage

#### Scenario: Auto-created link reverts like a manual one
- **WHEN** the organizer removes an automatically created multi-registration link
- **THEN** every registration it covered has its credit removed and returns to its previous state

#### Scenario: Auto-created link is distinguishable
- **WHEN** the organizer inspects a multi-registration link created by the system
- **THEN** it is identifiable as automatically created rather than manually built

#### Scenario: Mismatched sum becomes a pre-filled candidate
- **WHEN** a transaction carries three issued variable symbols but its amount does not match their combined amounts due within tolerance
- **THEN** the transaction stays unmatched and the manual matching interface opens with those three symbols pre-filled

#### Scenario: No subset guessing
- **WHEN** a transaction carries six variable symbols and its amount matches the sum of only five of them
- **THEN** the system does not settle those five automatically and presents all six as a candidate
