# payment-ledger Specification

## Purpose
Define the two journals a registration's money is read from: the credit journal,
which holds one row per amount credited and is the only place a credit is
recorded, and the waiver journal, which holds an organizer's statement that no
money was ever meant to pass. Rows are appended and reversed, never edited and
never deleted. What a registration has been credited, what it owes, whether it
is settled and the day it became paid are each derived from these rows and
stored nowhere, so a reversal is reflected by the next reading with no figure
anywhere to adjust — and a balance can say what it is made of.

## Requirements

### Requirement: Every credit is a journal entry
Every amount credited to a registration SHALL be recorded as one entry in a credit journal, and SHALL exist nowhere else. An entry SHALL state the registration it credits, the amount, the currency the money arrived in, the day it arrived, the source that carried it — an ingested bank transaction or a payment the organizer recorded — and what decided to credit it: an automatic match on the variable symbol, a payment link, a reinstatement, or a refund hold.

The source and the decision are two questions and SHALL both be answerable. The same transaction credited by an automatic match and by an organizer's link is one source with two different decisions behind it, and a reader asking why a registration was credited SHALL NOT have to infer the answer from the state of the source row.

An entry SHALL NOT be edited after it is written. A correction is a reversal and a new entry.

#### Scenario: An automatic match is journalled
- **WHEN** a transaction carrying an issued variable symbol is credited to its registration
- **THEN** one credit entry records the amount, the transaction's currency, the transaction's statement date, that transaction as the source, and the automatic match as the decision

#### Scenario: A recorded payment is journalled the same way
- **WHEN** the organizer records a payment of 1750 in cash received on a stated day
- **THEN** one credit entry records that amount, that currency, that day, the recorded payment as the source, and the organizer's record as the decision

#### Scenario: One transaction covering three fencers
- **WHEN** a payment link distributes one transaction across three registrations
- **THEN** three credit entries are written, each naming its own registration and its own amount, each naming that one transaction as its source and that link as its decision

#### Scenario: Nothing is credited outside the journal
- **WHEN** any amount is credited to a registration by any route
- **THEN** a credit entry exists for it, and the amount appears in no stored figure of its own

### Requirement: Appending a credit is idempotent on its source
A source SHALL NOT credit the same registration twice. Where a live credit entry already exists for a given registration and a given source row, a second attempt to credit that pair SHALL be refused, whatever the state of the source row, however many times a matching pass or a link application runs, and in whatever order.

This guarantee SHALL rest on the credit entries themselves and SHALL NOT rest on the workflow state of the source. A transaction's matching status says where it sits in the organizer's queues; it SHALL NOT be consulted to decide whether the money has already been counted.

One source crediting several registrations is not a repeat: a transaction covering three fencers holds one live credit per fencer, and each is subject to this rule separately.

#### Scenario: Re-running the matcher credits nothing twice
- **WHEN** a matching pass runs a second time over a tournament whose transactions were all credited by the first
- **THEN** no further credit entry is written and no balance moves

#### Scenario: Re-applying a payment link credits nothing twice
- **WHEN** the payment links are applied again after they have already been applied
- **THEN** no further credit entry is written and no balance moves

#### Scenario: A reset workflow state does not release a second credit
- **WHEN** a credited transaction's matching status is returned to a value a matching pass would reconsider
- **THEN** the pass writes no second credit, because a live credit for that transaction and registration already exists

#### Scenario: Re-ingesting the same statement
- **WHEN** the same statement file is imported a second time
- **THEN** the transactions it carries are recognised as already ingested, and no registration is credited again

### Requirement: A credit is reversed, never deleted
A credit entry SHALL be reversible, and reversing it SHALL record when it was reversed, by whom, and why. A reversed entry SHALL remain readable and SHALL stop counting toward what a registration has been credited.

A credit SHALL NOT be deleted, and a reversal SHALL NOT be expressed as a second entry carrying a negative amount. An entry states that money was credited; a reader listing a registration's credits SHALL see payments, not a mixture of payments and their corrections requiring a sign to tell apart.

A reversal SHALL return exactly the amount its entry credited, and SHALL NOT compute an amount from the registration's balance at the time of the reversal.

Reversing SHALL be once. Crediting the same source again after a reversal SHALL be a new entry, subject to the idempotence rule as any other.

#### Scenario: A withdrawn link returns exactly what it credited
- **WHEN** the organizer withdraws a payment link that credited 1750 to a registration whose total has since risen to 2000
- **THEN** 1750 is reversed, not 2000, and the registration is credited what it was before the link

#### Scenario: A reversed credit stays readable
- **WHEN** a credit is reversed
- **THEN** the entry still states its amount, its source and its day, and states in addition that it was reversed, when and by whom

#### Scenario: A reversal is not a payment
- **WHEN** a registration's credits are listed after one of them was reversed
- **THEN** the list holds the entries that were written, each stating whether it is live, and no entry carries a negative amount

#### Scenario: Re-crediting after a reversal
- **WHEN** a source whose credit was reversed is credited again
- **THEN** a new entry is written and the reversed one is unchanged

### Requirement: A waiver is a journal entry of its own kind
An organizer's statement that a registration is settled with no money passing SHALL be recorded as an entry in a waiver journal: which registration, who granted it, when, and the reason where one is required. Revoking it SHALL record when and by whom, and SHALL leave the granted entry standing.

A waiver SHALL NOT be an entry in the credit journal. It carries no amount, no currency and no arrival day, and crediting one would put money into every sum of what a tournament received that nobody paid.

A registration's waived state SHALL be read from the latest live entry in that journal, and SHALL NOT be stored on the registration. Granting, revoking and granting again SHALL therefore leave three entries and three reasons, and the earliest SHALL remain readable.

#### Scenario: A waiver is granted
- **WHEN** the organizer marks a registration settled by hand with a stated reason
- **THEN** a waiver entry records the registration, the organizer, the moment and the reason, and no credit entry is written

#### Scenario: A waiver is revoked
- **WHEN** the organizer unmarks a registration they had waived
- **THEN** the entry records who revoked it and when, the entry itself remains, and the registration is no longer waived

#### Scenario: An earlier reason survives a later one
- **WHEN** a registration is waived with one reason, unmarked, and waived again with a different reason
- **THEN** both entries stand with their own reasons, and the registration reads as waived under the second

#### Scenario: A waiver moves no money
- **WHEN** a registration owing 1750 is waived
- **THEN** what has been credited to it is unchanged, and no total of what the tournament received moves

### Requirement: What a registration has been credited is a sum of its journal
The amount credited to a registration in a currency lane SHALL be the sum of its live credit entries in that lane, and SHALL NOT be stored. Reversing an entry, withdrawing a link, or removing a recorded payment SHALL each change that sum by ceasing to count an entry, and SHALL NOT adjust a figure.

The sum SHALL be obtainable in a single query alongside the registrations it belongs to, so that counting seats, selecting the registrations a lifecycle pass acts on, and rendering the console's table each stay one query.

The two currency lanes SHALL be summed separately and SHALL NOT be combined, as they are not today. A credit entry's lane SHALL follow from the currency it records against the tournament's own, and SHALL NOT be stored as a property of the entry.

#### Scenario: Two credits in one lane
- **WHEN** a registration holds live credits of 900 and 850 in the local currency
- **THEN** it has been credited 1750 in that lane

#### Scenario: A reversal changes the sum with no figure adjusted
- **WHEN** one of those two credits is reversed
- **THEN** the registration has been credited the other one's amount, arrived at by not counting the reversed entry

#### Scenario: Lanes are not combined
- **WHEN** a registration holds a live credit of 750 in the local currency and one of 30 EUR
- **THEN** it has been credited 750 in the local lane and 30 in the EUR lane, and no third figure exists

#### Scenario: Counting seats stays one query
- **WHEN** the seats taken in a discipline are counted
- **THEN** the count is obtained in a single query, with each registration's credited sum resolved within it

### Requirement: Settled is derived and cannot be assigned
Whether a registration is settled SHALL be derived, at every reading, from a live waiver or from a lane that **holds credit** whose outstanding balance falls within the tournament's tolerance. It SHALL NOT be a stored value, and no code path SHALL be able to declare a registration settled other than by waiving it or by crediting it.

**A registration that has been credited nothing SHALL NOT read as settled, whatever it is owed.** Owing nothing and having paid are different statements and SHALL NOT be collapsed. A registration priced at zero — one sitting entirely in the substitute queue, whose queued placements are not priced, or one on a tournament that charges nothing — owes nothing and has been credited nothing; it SHALL read as reserved. Reading it as paid would put a fencer waiting in a queue onto the roster as having paid.

A registration holding credit whose total later falls to zero or below SHALL continue to read as settled, its balance stating the overpayment. What settles a registration is that money arrived against it, not that a total happens to be covered.

The stored lifecycle SHALL hold what a person or a clock decided — that a registration is reserved, has expired, or was cancelled — and SHALL NOT hold whether it is paid. Where the lifecycle and the derivation meet, the lifecycle SHALL win: a registration credited after it expired reads as expired, and a cancelled one reads as cancelled, however much money stands against it.

The state a reader is shown SHALL continue to be one of reserved, paid, expired and cancelled, composed from the lifecycle and the derivation at the point it is read.

#### Scenario: Crediting settles without anything being assigned
- **WHEN** a registration owing 1750 is credited 1750
- **THEN** it reads as paid, and no stored value was changed to make it so

#### Scenario: An amendment upward unsettles nothing that was decided
- **WHEN** a settled registration's total is raised beyond tolerance by an amendment
- **THEN** whether it reads as paid follows from the new total against its credits, with no state to correct

#### Scenario: A waiver settles with no money
- **WHEN** a registration owing 1750 is waived
- **THEN** it reads as paid and its credits stay at nothing

#### Scenario: The lifecycle wins over the money
- **WHEN** an expired registration is credited the whole amount it owed
- **THEN** it reads as expired, not as paid, and appears among the reservations that expired holding money

#### Scenario: A reversal unsettles by derivation
- **WHEN** the credit that settled a registration is reversed
- **THEN** the registration reads as reserved again, arrived at by re-reading the money rather than by restoring a previous state

#### Scenario: A fully-queued registration is not paid
- **WHEN** a registration sits entirely in the substitute queue, so that nothing it holds is priced and it owes nothing
- **THEN** it reads as reserved, and appears on no roster as having paid

#### Scenario: A tournament that charges nothing
- **WHEN** a registration on a tournament whose total comes to zero is read
- **THEN** it reads as reserved, having been credited nothing and waived by nobody

#### Scenario: An amendment down to nothing keeps the payment
- **WHEN** a paid registration is amended until its total is zero while its credit stands
- **THEN** it still reads as paid and its balance states the overpayment

### Requirement: The paid date is the day of the credit that completed the balance
A registration that reads as paid SHALL state the day it became paid, derived by accumulating its live credits in the order they were appended until the outstanding balance in the lane the money came in first falls within tolerance. That credit's arrival day SHALL be the paid date. Where a waiver settles the registration, the paid date SHALL be the day the waiver was granted.

The paid date SHALL NOT be stored. Where credits are appended out of the order the money actually arrived in, the derived day may precede a credit already counted, and that SHALL be accepted rather than corrected: the day is the arrival day of the credit that completed the balance, not the latest day seen.

Widening the amount tolerance settles registrations on money already received, and such a settlement SHALL take the day of the credit that the widened tolerance accepted, not the day the organizer widened it.

#### Scenario: Settled by the second of two credits
- **WHEN** a registration owing 1750 is credited 1000 arriving on the 1st and 750 arriving on the 3rd
- **THEN** its paid date is the 3rd

#### Scenario: A later credit does not move the date
- **WHEN** that registration is afterwards credited a further amount arriving on the 10th
- **THEN** its paid date is still the 3rd

#### Scenario: A waiver dates itself
- **WHEN** a registration is settled by a waiver alone
- **THEN** its paid date is the day the waiver was granted

#### Scenario: Widening the tolerance takes the money's day
- **WHEN** the organizer widens the tolerance and a registration credited short on the 1st thereby becomes paid on the 8th
- **THEN** its paid date is the 1st

### Requirement: One credit entry may be reversed on its own
An organizer with console access SHALL be able to reverse a single credited bank transaction, releasing the credit it made and returning the transaction to the unmatched queue. The registration's settled state SHALL follow from the money afterwards, with nothing else restored.

This SHALL be available whatever decided the credit. A payment link and a payment recorded by hand can each already be taken back; a transaction an automatic match credited SHALL be no less reversible, that being the case in which money otherwise has no way out.

The action SHALL state what it will do before it is confirmed, because the reversal may unsettle a registration a fencer has already been told is paid.

#### Scenario: An automatically matched transaction is reversed
- **WHEN** the organizer reverses a transaction that an automatic match had credited
- **THEN** its credit stops counting, the transaction returns to the unmatched queue, and the registration reads as reserved

#### Scenario: The consequence is stated first
- **WHEN** the organizer opens the reversal on a transaction whose credit settled a registration
- **THEN** it states that the registration will no longer read as paid, before anything is written

#### Scenario: A transaction covering several fencers
- **WHEN** the organizer reverses a transaction whose credits covered three registrations
- **THEN** all three of its credits stop counting, and each registration's state follows from what remains
