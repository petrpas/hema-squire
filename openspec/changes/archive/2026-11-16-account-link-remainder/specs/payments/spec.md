## MODIFIED Requirements

### Requirement: Manual matching
The organizer SHALL be able to link an unmatched transaction to one or more registrations in the Payments phase. The link SHALL persist as a rule (surviving reruns and re-ingestion) and SHALL support one payer covering multiple registrations.

A link covering several registrations SHALL **distribute** the transaction's amount across them, crediting each registration the amount it is due and never more than the transaction holds. It SHALL NOT credit the full transaction amount to every registration it covers, which would record money that never arrived and present every covered registration as overpaid.

**A link SHALL account for the whole transaction.** It SHALL credit each registration it covers what that registration owes in the transaction's currency, in the order the registrations are named, and the last registration able to take money SHALL be credited everything that remains. Where that leaves it credited beyond tolerance it SHALL read as overpaid and be routed to refund tracking, exactly as a transaction quoting its variable symbol would. What a link credits SHALL always add up to the transaction's amount, so that no part of a payment is matched without standing in the journal. This SHALL hold of a link covering one registration as of one covering several.

A registration is able to take money where it is reserved and does not already read as settled. **A link that would credit nothing SHALL NOT resolve the transaction** — where no registration it covers is able to take money, or the transaction is in a currency the tournament does not take. Creating such a link SHALL be refused with a stated reason and the transaction SHALL remain among the uncredited. A link already recorded that finds nothing payable when it is applied again SHALL leave its transaction uncredited rather than matched.

Each amount the link credits SHALL be a credit journal entry naming that link as what decided it, so that withdrawing the link reverses exactly the entries it wrote rather than an amount computed against today's balances. The rule SHALL NOT carry those amounts in its own payload: a credit belongs in the journal every other credit is in, where it is subject to the same reversal rule and the same idempotence guarantee.

Withdrawing a link SHALL reverse every live credit it wrote, unconditionally. It SHALL NOT decline to reverse a credit on account of what has become of the registration since — an expired or amended registration holds that money no less, and leaving the credit standing while the link that explains it is withdrawn strands an amount nothing can account for.

#### Scenario: One transfer covers two fencers
- **WHEN** the organizer links a single transaction to two registrations
- **THEN** both registrations read as paid and the link is recorded as a removable rule

#### Scenario: Amount distributed, not multiplied
- **WHEN** the organizer links a transaction of 3500 to two registrations each owing 1750
- **THEN** each registration is credited 1750, both read as paid, and neither is recorded as overpaid

#### Scenario: The remainder goes to the last registration
- **WHEN** the organizer links a transaction of 2600 to two registrations each owing 1000
- **THEN** the first is credited 1000, the second 1600, both read as paid, the second is routed to refund tracking, and the link's credits add up to 2600

#### Scenario: A one-registration link keeps the overpayment
- **WHEN** the organizer links a transaction of 1200 to one registration owing 1000
- **THEN** it is credited 1200 and routed to refund tracking

#### Scenario: A link to nothing payable is refused
- **WHEN** the organizer links a transaction to a registration that already reads as paid
- **THEN** the link is refused stating that nothing it names can take the payment, nothing is credited, and the transaction stays among the uncredited

#### Scenario: Removing a distributed link reverts every registration
- **WHEN** the organizer removes a link that had covered three registrations
- **THEN** each of the three has exactly the amount that link credited reversed, and none retains a partial credit

#### Scenario: Withdrawal reaches a registration that has since expired
- **WHEN** the organizer withdraws a link covering a registration that expired after the link was applied
- **THEN** that registration's credit is reversed like every other, and no amount is left standing without the link that explains it
