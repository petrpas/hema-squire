## ADDED Requirements

### Requirement: An organizer may record a payment Squire never saw
WHERE Squire handles a tournament's payments, an organizer with console access SHALL be able to record a payment that arrived outside the bank feed — cash at the desk, a transfer to another account, a card terminal — against one registration. The record SHALL carry the amount, the currency it arrived in, the date the organizer says it arrived, how it arrived, a free note, and the organizer who recorded it.

The amount SHALL be credited to the registration exactly as a bank transaction's amount is credited: to the lane of the currency it names, never converted and never summed across lanes. Every consequence of a credit SHALL follow identically — the settle test against the same tolerance, the deposit threshold and the payment window it closes, the payment event, the overpayment's refund state, and the confirmation or partial-payment mail the fencer receives. A fencer SHALL NOT be able to tell from what Squire sends them which route their money took.

A recorded payment SHALL be a record of its own and SHALL NOT be written into the tournament's bank transactions. That list is what an organizer reads against their bank account and what intake deduplicates against; a row no bank sent would falsify it for every reader.

The organizer SHALL be able to remove a recorded payment, and removal SHALL subtract exactly the amount that payment credited — not a figure derived from today's balance — and SHALL return the registration to the state that amount had settled. Both the recording and the removal SHALL be payment events naming the organizer who acted. A recorded payment SHALL NOT be editable: a correction is a removal and a new record, so that what was credited and what reversed it are both readable afterwards.

Recording SHALL be refused on a tournament whose payments Squire does not handle, with a stated reason. There Squire tracks no amounts at all, and a tournament that needs them tracked wants Squire handling its payments.

#### Scenario: Cash at the desk settles a reservation
- **WHEN** the organizer records a cash payment for the full amount a reservation owes
- **THEN** the registration becomes paid, its credited amount rises by that amount, the fencer receives the same confirmation a bank credit would have sent, and the action is recorded against the organizer

#### Scenario: A recorded payment can be partial
- **WHEN** the organizer records 500 against a registration owing 1750
- **THEN** 500 is credited, the registration stays reserved owing 1250, and the fencer receives the partial-payment notice

#### Scenario: A recorded payment reaches the deposit
- **WHEN** the organizer records an amount that brings a deposit-mode registration's credit to the published deposit
- **THEN** the payment window closes exactly as it does when a bank transaction reaches it

#### Scenario: Removal reverses exactly what was credited
- **WHEN** the organizer removes a recorded payment of 1750 from a registration whose total was later amended upward
- **THEN** 1750 is subtracted, not the amended balance, and the registration is no longer paid

#### Scenario: It is not a bank transaction
- **WHEN** the organizer records a payment and then opens the tournament's transaction list
- **THEN** the list holds only transactions a statement carried, and the recorded payment is not among them

#### Scenario: Refused where Squire collects nothing
- **WHEN** an organizer attempts to record a payment on a tournament whose payments Squire does not handle
- **THEN** the attempt is refused with a stated reason and nothing is credited

### Requirement: A registration has one outstanding balance
A registration SHALL state one outstanding balance and the currency it is in,
never one figure per currency lane.

A tournament pricing in two currencies quotes two prices for one place, not two
halves of a debt: crediting either lane settles the registration, after which
the untouched lane still holds its full price while nothing is owed in it. That
untouched figure is not a balance and SHALL NOT be presented as one. Presented
beside the real balance it reads as a conversion of it, and a fencer who has
paid in full is shown a demand.

The balance SHALL be stated in the lane the money arrived in, and in the local
currency where no money has arrived, that being the price the tournament quotes
first. Nothing SHALL be converted between the lanes to produce it.

**The tolerance decides the registration's state, and SHALL NOT decide this
figure.** A settled registration credited short of its total SHALL state how
short. A euro transfer the payer's bank converted lands twenty or forty crowns
under the local price; the tolerance accepts it as payment and the registration
becomes paid, and what reached the account is still less than what was quoted.
Reading that back as zero tells the organizer their books balance when they do
not, and leaves the difference recorded nowhere. A trivial overpayment SHALL
likewise read as the negative figure it is.

Whether a shortfall is worth chasing is the organizer's to decide, and the
table SHALL put them in a position to decide it.

A registration settled by hand SHALL read as owing nothing whatever its
counters hold, since no money was ever meant to pass.

#### Scenario: Paid in the local currency on a tournament that also takes EUR
- **WHEN** a registration owing 1100 Kč or 45 € is credited 1100 Kč
- **THEN** its balance is zero, and 45 € is not stated as outstanding beside it

#### Scenario: Paid in EUR
- **WHEN** a registration owing 1100 Kč or 45 € is credited 45 €
- **THEN** its balance is zero, and 1100 Kč is not stated as outstanding beside it

#### Scenario: A converted transfer that fell short within tolerance
- **WHEN** a registration owing 750 Kč is credited 708,85 Kč, which the tolerance accepts, and is marked paid
- **THEN** it is paid and its balance reads 41,15 Kč, so that what did not arrive is not lost from view

#### Scenario: A surcharge outlives the settle
- **WHEN** a paid registration is amended upward so that 300 is owed
- **THEN** it stays paid and its balance reads 300

#### Scenario: Part-paid in one lane only
- **WHEN** a registration owing 1100 Kč or 45 € is credited 600 Kč
- **THEN** its balance reads 500 Kč, in the lane the money came in

#### Scenario: A waiver owes nothing
- **WHEN** a registration is settled by hand
- **THEN** its balance is not the total it would otherwise owe

### Requirement: A credit can say where it came from
Every amount credited to a registration SHALL be attributable, after the fact, to either a bank transaction Squire ingested or a payment an organizer recorded. The distinction SHALL be a property of the payment and not of the registration, because one registration may hold both.

The credited counters themselves SHALL hold the sum of both, so that what a registration is owed, whether its deposit is met, and whether it expired holding money are each answered once and from one figure. A reader needing only what arrived in the bank account SHALL be able to obtain it by asking which payments were which, and SHALL NOT be silently handed the larger figure in its place.

#### Scenario: Both kinds on one registration
- **WHEN** a registration is credited 1000 by a bank transaction and 750 by a recorded payment
- **THEN** it is credited 1750 in total, owes nothing further, and each of the two amounts can be traced to the payment that carried it

#### Scenario: What arrived in the account is still answerable
- **WHEN** a reader asks what a tournament received through its bank account
- **THEN** the answer counts the ingested transactions alone and excludes what was recorded by hand

## MODIFIED Requirements

### Requirement: An organizer may mark a registration settled by hand
An organizer with console access SHALL be able to mark a registration settled by hand, and to unmark it, on **every** tournament — whether or not Squire handles its payments. The mark means one thing in both places: this registration is settled and no money passed through Squire.

Where Squire handles no payments, that is the organizer's word that they collected the money themselves, and it is the only way a registration reaches the paid state there. Where Squire handles the payments, it is a waiver — a free place, a comped entrant, a guest instructor — and it stands beside, not in place of, the money that reaches such a tournament by transaction and by record.

The mark SHALL record the verdict and **SHALL NOT record an amount**. The registration's state becomes paid; the counters holding what has been credited SHALL be left exactly as they were. A mark that wrote the outstanding amount into those counters would put money into every sum of what a tournament received that nobody ever paid.

A hand-settled registration SHALL therefore read as paid while what it is owed remains what it always was. Every surface presenting both SHALL state that the balance is waived rather than owed, because a reader who takes the outstanding figure for an error would be misreading the one thing that is true: the fencer owes the organizer nothing, and Squire received nothing.

The mark SHALL be stored on the registration — when it was made and why — and SHALL NOT be inferred from a paid state with empty counters. That inference stops being sound the moment a marked registration may also hold a recorded payment.

**The reason SHALL be required where Squire handles the payments** and SHALL be optional where it does not. Where a live ledger is being read, a paid row holding nothing beside rows holding credits is a puzzle a reader will otherwise try to solve as a fault, and one short phrase answers it. Where no ledger exists, every row is that row.

Both marking and unmarking SHALL be recorded as payment events naming the organizer who acted, so that a roster stating that someone has paid can always state who said so and when.

Marking SHALL succeed on a registration that carries no variable symbol. A tournament whose organizer keeps the roster mints none — Squire never told any payer a number to quote — and those are among the registrations most likely to be settled by hand, so what a registration is stated as SHALL treat the symbol as absent rather than as required.

The mark SHALL answer a yes-or-no question and SHALL NOT express partial settlement. A registration part-settled by money collected outside the feed is recorded as a payment, not marked.

A bank transaction landing afterwards on a hand-settled registration SHALL NOT be credited silently. It SHALL be flagged for the organizer as a transaction whose registration is no longer reserved, stating that the registration was settled by hand, so that a person decides whether it is further money or the same money arriving twice.

#### Scenario: The organizer marks a fencer settled where Squire collects nothing
- **WHEN** the organizer of a tournament that handles its own payments marks a registration paid, giving no reason
- **THEN** the registration's state becomes paid, what has been credited stays at nothing, and the action is recorded against the organizer

#### Scenario: A waiver on a collecting tournament
- **WHEN** the organizer of a tournament whose payments Squire handles marks a registration settled with the reason *volná účast*
- **THEN** the registration reads as paid and waived, both credited counters stay at zero, no total of received money moves, and the reason is stored with the mark

#### Scenario: A reason is required where Squire collects
- **WHEN** an organizer marks a registration settled on a tournament whose payments Squire handles and gives no reason
- **THEN** the mark is refused, stating that a reason is required, and the registration is unchanged

#### Scenario: Unmarking returns it
- **WHEN** the organizer unmarks a registration they had marked
- **THEN** it is no longer paid, the stored mark and its reason are cleared, and both the marking and the unmarking stand in the record

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
