## MODIFIED Requirements

### Requirement: Settled is derived and cannot be assigned
Whether a registration is settled SHALL be derived, at every reading, from a live waiver or from a lane that **holds credit** whose outstanding balance falls within the tournament's tolerance. It SHALL NOT be a stored value, and no code path SHALL be able to declare a registration settled other than by waiving it or by crediting it.

**A registration that has been credited nothing SHALL NOT read as settled, whatever it is owed.** Owing nothing and having paid are different statements and SHALL NOT be collapsed. A registration priced at zero — one sitting entirely in the substitute queue, whose queued placements are not priced, or one on a tournament that charges nothing — owes nothing and has been credited nothing; it SHALL read as reserved. Reading it as paid would put a fencer waiting in a queue onto the roster as having paid.

A registration holding credit whose total later falls to zero or below SHALL continue to read as settled, its balance stating the overpayment. What settles a registration is that money arrived against it, not that a total happens to be covered.

**A registration sitting entirely in the substitute queue SHALL NOT read as settled, whatever it has been credited**, unless it has been waived. Every one of its placements is a place it is waiting for, and the queue holds no money (`seating-queue`): credit it holds there — a deposit forfeited at settlement, a partial payment on a registration demoted by a lapsed window — is recorded against it, counts when it is promoted, and SHALL NOT make it read as paid. A registration sitting entirely in the queue is one with at least one placement, every individual placement of which is a substitute placement and every team of which is waitlisted.

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

#### Scenario: A forfeited deposit does not read as paid
- **WHEN** a deposit-mode registration credited its 500 deposit is demoted at settlement and its total recomputed to nothing
- **THEN** it reads as reserved, its credit of 500 stands against it, and it appears on no roster as having paid

#### Scenario: Promotion lets the held credit count
- **WHEN** that registration is promoted into a place priced 1750
- **THEN** it owes 1250, and reads as paid once 1250 more is credited

#### Scenario: A tournament that charges nothing
- **WHEN** a registration on a tournament whose total comes to zero is read
- **THEN** it reads as reserved, having been credited nothing and waived by nobody

#### Scenario: An amendment down to nothing keeps the payment
- **WHEN** a paid registration is amended until its total is zero while its credit stands
- **THEN** it still reads as paid and its balance states the overpayment
