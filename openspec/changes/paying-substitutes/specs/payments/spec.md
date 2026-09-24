## MODIFIED Requirements

### Requirement: Payments arriving on a queued registration
A payment whose VS resolves to a registration sitting entirely in the substitute queue SHALL NOT be credited to it, by an automatic pass or by a bare token, **except where it seats the registration first**, as `seating-queue` fixes under **A paying substitute takes free places** for a tournament that lets paying substitutes take free places. The queue holds no money, and a registration credited there would read as a fencer who paid for a place they do not hold. The transaction SHALL be flagged with a reason of its own, distinct from every expiry reason, naming that the registration is queued. Where the tournament lets paying substitutes take free places, the reason SHALL further distinguish a payment that matched the claim but found a discipline full — which the next passes may seat — from one whose amount is not the claim, which only the organizer resolves.

The fencer SHALL be notified that the payment arrived, that they are waiting in the queue and hold no place, and that the organizer will be in contact. The notice SHALL NOT promise a place and SHALL NOT imply the money is lost.

The organizer SHALL resolve such a transaction in one of two ways:
- by **promoting** the fencer, which re-evaluates the transaction at once, as `seating-queue` fixes, so that it is credited against the placement the fencer now owes for; or
- by **marking it for refund**, the existing action on a flagged transaction, recording the amount against the fencer for manual settlement.

A matching pass SHALL keep re-evaluating such a transaction, as it re-evaluates every flagged one, so that a transaction whose registration has since been promoted by any path is credited by the next pass even where the promotion did not reach it.

A registration holding a seated placement beside a queued one is not sitting entirely in the queue: money arriving on it SHALL be matched against what its seated placements owe, as today.

#### Scenario: Payment on a queued registration held
- **WHEN** a transaction carrying the VS of a registration demoted at settlement arrives
- **THEN** it is flagged with the queued reason, nothing is credited, and the fencer is told the payment arrived and the organizer will be in contact

#### Scenario: Promotion credits the held payment
- **WHEN** the organizer promotes that fencer into a free place
- **THEN** the flagged transaction is credited against the place, and it leaves the flagged list

#### Scenario: Refund instead of a place
- **WHEN** the organizer marks the held transaction for refund
- **THEN** the amount is recorded against the fencer for manual settlement and the registration stays in the queue

#### Scenario: A mixed registration is paid as usual
- **WHEN** a transaction arrives for a registration holding one unpaid seat and one queued placement
- **THEN** it is matched against what the seat owes, exactly as any other payment

#### Scenario: Seated by payment where the tournament allows it
- **WHEN** paying substitutes may take places and a payment matching a waiting registration's claim arrives while its disciplines have free places
- **THEN** the registration is seated and the payment credited, and nothing is flagged

#### Scenario: A wrong amount is held for the organizer
- **WHEN** paying substitutes may take places and a payment on a waiting registration does not match its claim
- **THEN** it is held with a reason naming the amount, and no later pass seats it by itself
