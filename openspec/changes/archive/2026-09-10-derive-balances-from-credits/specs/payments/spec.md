## MODIFIED Requirements

### Requirement: Manual matching
The organizer SHALL be able to link an unmatched transaction to one or more registrations in the Payments phase. The link SHALL persist as a rule (surviving reruns and re-ingestion) and SHALL support one payer covering multiple registrations.

A link covering several registrations SHALL **distribute** the transaction's amount across them, crediting each registration the amount it is due and never more than the transaction holds. It SHALL NOT credit the full transaction amount to every registration it covers, which would record money that never arrived and present every covered registration as overpaid.

Each amount the link credits SHALL be a credit journal entry naming that link as what decided it, so that withdrawing the link reverses exactly the entries it wrote rather than an amount computed against today's balances. The rule SHALL NOT carry those amounts in its own payload: a credit belongs in the journal every other credit is in, where it is subject to the same reversal rule and the same idempotence guarantee.

Withdrawing a link SHALL reverse every live credit it wrote, unconditionally. It SHALL NOT decline to reverse a credit on account of what has become of the registration since — an expired or amended registration holds that money no less, and leaving the credit standing while the link that explains it is withdrawn strands an amount nothing can account for.

#### Scenario: One transfer covers two fencers
- **WHEN** the organizer links a single transaction to two registrations
- **THEN** both registrations read as paid and the link is recorded as a removable rule

#### Scenario: Amount distributed, not multiplied
- **WHEN** the organizer links a transaction of 3500 to two registrations each owing 1750
- **THEN** each registration is credited 1750, both read as paid, and neither is recorded as overpaid

#### Scenario: Removing a distributed link reverts every registration
- **WHEN** the organizer removes a link that had covered three registrations
- **THEN** each of the three has exactly the amount that link credited reversed, and none retains a partial credit

#### Scenario: Withdrawal reaches a registration that has since expired
- **WHEN** the organizer withdraws a link covering a registration that expired after the link was applied
- **THEN** that registration's credit is reversed like every other, and no amount is left standing without the link that explains it

### Requirement: An organizer may mark a registration settled by hand
An organizer with console access SHALL be able to mark a registration settled by hand, and to unmark it, on **every** tournament — whether or not Squire handles its payments. The mark means one thing in both places: this registration is settled and no money passed through Squire.

Where Squire handles no payments, that is the organizer's word that they collected the money themselves, and it is the only way a registration reads as paid there. Where Squire handles the payments, it is a waiver — a free place, a comped entrant, a guest instructor — and it stands beside, not in place of, the money that reaches such a tournament by transaction and by record.

The mark SHALL record the verdict and **SHALL NOT record an amount**. The registration reads as paid; what has been credited to it SHALL be left exactly as it was. A mark that wrote the outstanding amount into the credit journal would put money into every sum of what a tournament received that nobody ever paid.

A hand-settled registration SHALL therefore read as paid while what it is owed remains what it always was. Every surface presenting both SHALL state that the balance is waived rather than owed, because a reader who takes the outstanding figure for an error would be misreading the one thing that is true: the fencer owes the organizer nothing, and Squire received nothing.

The mark SHALL be recorded as an entry in the waiver journal — who granted it, when, and why — and SHALL NOT be stored on the registration, nor inferred from a paid state with empty credits. Whether a registration is waived SHALL be read from the latest live entry, so that a mark set, cleared and set again leaves every reason it was ever given readable rather than only the last.

**The reason SHALL be required where Squire handles the payments** and SHALL be optional where it does not. Where a live ledger is being read, a paid row holding nothing beside rows holding credits is a puzzle a reader will otherwise try to solve as a fault, and one short phrase answers it. Where no ledger exists, every row is that row.

Both marking and unmarking SHALL name the organizer who acted, so that a roster stating that someone has paid can always state who said so and when.

Marking SHALL succeed on a registration that carries no variable symbol. A tournament whose organizer keeps the roster mints none — Squire never told any payer a number to quote — and those are among the registrations most likely to be settled by hand, so what a registration is stated as SHALL treat the symbol as absent rather than as required.

The mark SHALL answer a yes-or-no question and SHALL NOT express partial settlement. A registration part-settled by money collected outside the feed is recorded as a payment, not marked.

A bank transaction landing afterwards on a hand-settled registration SHALL NOT be credited silently. It SHALL be flagged for the organizer as a transaction whose registration is no longer reserved, stating that the registration was settled by hand, so that a person decides whether it is further money or the same money arriving twice.

#### Scenario: The organizer marks a fencer settled where Squire collects nothing
- **WHEN** the organizer of a tournament that handles its own payments marks a registration paid, giving no reason
- **THEN** the registration reads as paid, what has been credited stays at nothing, and the waiver entry names the organizer

#### Scenario: A waiver on a collecting tournament
- **WHEN** the organizer of a tournament whose payments Squire handles marks a registration settled with the reason *volná účast*
- **THEN** the registration reads as paid and waived, no credit entry is written, no total of received money moves, and the reason is held on the waiver entry

#### Scenario: A reason is required where Squire collects
- **WHEN** an organizer marks a registration settled on a tournament whose payments Squire handles and gives no reason
- **THEN** the mark is refused, stating that a reason is required, and no entry is written

#### Scenario: Unmarking returns it
- **WHEN** the organizer unmarks a registration they had marked
- **THEN** it no longer reads as paid, the entry records who revoked it and when, and both the marking and the unmarking stand in the record

#### Scenario: An earlier reason is not overwritten
- **WHEN** a registration is waived with one reason, unmarked, and waived again with another
- **THEN** both reasons remain readable and the registration reads as waived under the second

#### Scenario: What Squire received is not invented
- **WHEN** a hand-settled registration is read
- **THEN** the amount credited against it is unchanged by the mark, and what the registration is owed is presented as waived rather than as a debt

#### Scenario: A registration with no variable symbol
- **WHEN** the organizer marks a registration that was never given a variable symbol
- **THEN** the mark succeeds and the registration is stated with no symbol, rather than the response failing after the mark was written

#### Scenario: A statement arriving afterwards does not double it
- **WHEN** a bank transaction quoting a hand-settled registration's variable symbol is ingested
- **THEN** it is flagged rather than credited, stating that the registration was settled by hand, and the organizer resolves it

#### Scenario: Switching afterwards is not specially handled
- **WHEN** a tournament holding hand-settled registrations is switched to having Squire handle the payments
- **THEN** the switch applies as any other does, the marks are neither cleared nor counted, and the registrations keep the state a person gave them

### Requirement: A registration has one outstanding balance
A registration SHALL state one outstanding balance and the currency it is in,
never one figure per currency lane.

The balance SHALL be derived, at every reading, from the registration's total in
a lane less the sum of its live credits in that lane. It SHALL NOT be stored,
and neither SHALL the credited figure it is computed from.

A tournament pricing in two currencies quotes two prices for one place, not two
halves of a debt: crediting either lane settles the registration, after which
the untouched lane still holds its full price while nothing is owed in it. That
untouched figure is not a balance and SHALL NOT be presented as one. Presented
beside the real balance it reads as a conversion of it, and a fencer who has
paid in full is shown a demand.

The balance SHALL be stated in the lane the money arrived in, and in the local
currency where no money has arrived, that being the price the tournament quotes
first. Nothing SHALL be converted between the lanes to produce it.

**The tolerance decides whether the registration reads as settled, and SHALL NOT
decide this figure.** A settled registration credited short of its total SHALL
state how short. A euro transfer the payer's bank converted lands twenty or
forty crowns under the local price; the tolerance accepts it as payment and the
registration reads as paid, and what reached the account is still less than what
was quoted. Reading that back as zero tells the organizer their books balance
when they do not, and leaves the difference recorded nowhere. A trivial
overpayment SHALL likewise read as the negative figure it is.

Whether a shortfall is worth chasing is the organizer's to decide, and the
table SHALL put them in a position to decide it.

A registration settled by hand SHALL read as owing nothing whatever its
credits hold, since no money was ever meant to pass.

#### Scenario: Paid in the local currency on a tournament that also takes EUR
- **WHEN** a registration owing 1100 Kč or 45 € is credited 1100 Kč
- **THEN** its balance is zero, and 45 € is not stated as outstanding beside it

#### Scenario: Paid in EUR
- **WHEN** a registration owing 1100 Kč or 45 € is credited 45 €
- **THEN** its balance is zero, and 1100 Kč is not stated as outstanding beside it

#### Scenario: A converted transfer that fell short within tolerance
- **WHEN** a registration owing 750 Kč is credited 708,85 Kč, which the tolerance accepts, and reads as paid
- **THEN** it is paid and its balance reads 41,15 Kč, so that what did not arrive is not lost from view

#### Scenario: A surcharge is read against the credits that stand
- **WHEN** a paid registration is amended upward so that 300 is owed
- **THEN** its balance reads 300, arrived at from the new total against the same credits

#### Scenario: Part-paid in one lane only
- **WHEN** a registration owing 1100 Kč or 45 € is credited 600 Kč
- **THEN** its balance reads 500 Kč, in the lane the money came in

#### Scenario: A waiver owes nothing
- **WHEN** a registration is settled by hand
- **THEN** its balance is not the total it would otherwise owe

#### Scenario: A reversal is reflected without a figure being adjusted
- **WHEN** a credit of 600 Kč against a registration owing 1100 Kč is reversed
- **THEN** its balance reads 1100 Kč again, because the reversed entry stops being counted

### Requirement: A credit can say where it came from
Every amount credited to a registration SHALL be attributable, after the fact, to either a bank transaction Squire ingested or a payment an organizer recorded. The credit entry itself SHALL carry that attribution, so the question is answered by reading the credit rather than by asking each source table in turn which one holds it.

What a registration has been credited SHALL be the sum of both kinds together, so that what it is owed, whether its deposit is met, and whether it expired holding money are each answered once and from one figure. A reader needing only what arrived in the bank account SHALL be able to obtain it by narrowing that sum to the credits carried by transactions, and SHALL NOT be silently handed the larger figure in its place.

#### Scenario: Both kinds on one registration
- **WHEN** a registration is credited 1000 by a bank transaction and 750 by a recorded payment
- **THEN** it is credited 1750 in total, owes nothing further, and each of the two entries names the payment that carried it

#### Scenario: What arrived in the account is still answerable
- **WHEN** a reader asks what a tournament received through its bank account
- **THEN** the answer sums the credits carried by ingested transactions alone and excludes what was recorded by hand

#### Scenario: The decision behind a credit is answerable too
- **WHEN** a reader asks why a registration was credited by a given transaction
- **THEN** the entry states whether an automatic match, a payment link, a reinstatement or a refund hold decided it

## REMOVED Requirements

### Requirement: A registration's paid date is the day the money arrived
**Reason**: Restated in the new `payment-ledger` capability as **The paid date is the day of the credit that completed the balance**, which keeps every substantive rule this requirement carried — the day is the arrival day and not the day Squire learned of it; a registration settled by several credits takes the day of the one that completed it; a tolerance widening takes the accepted transaction's day — and withdraws only the prohibition on reconstructing it. That prohibition rested on credits being "amounts and not a history", which this change makes untrue: credits are now a journal, and the date falls out of replaying it rather than needing to be written down at the one place a credit's consequences are decided.

**Migration**: `Registration.paid_at` is dropped. Every reader of it reads the derived paid date instead, which answers identically for every registration the old field answered correctly for. No behaviour a client can observe changes.
