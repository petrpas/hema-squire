## ADDED Requirements

### Requirement: A conditional registration moves as one
A registration carrying a participation condition (`registration`, **Participation condition**) SHALL be promoted and returned as one wherever the condition is concerned.

**Promotion.** Promoting any placement of a registration whose condition is not met SHALL seat every discipline of the condition together with the placement promoted. It SHALL be offered and carried out only while every discipline of the condition, and the promoted discipline, has a free place, and SHALL be refused otherwise with a reason naming the discipline that has none. It SHALL bill what the newly seated placements add, as every promotion does. Promoting a placement outside the condition of a registration whose condition is already met SHALL be an ordinary promotion of that placement alone.

**Return.** Returning to the queue any placement belonging to a met condition SHALL return the whole registration: every seated placement, inside the condition and outside it, since the fencer does not come without the condition. Returning a placement outside the condition SHALL return that placement alone. The organizer's return SHALL keep each placement's queue moment, as every organizer's return does.

**Queue view.** A queued row of a conditional registration SHALL state the other disciplines the registration waits for. Its promote arrow SHALL be offered only when all of them have a free place, so that the rows the organizer can seat now are legible as those carrying an arrow. Its position SHALL remain its place in queue order; a conditional registration ahead of the line in one discipline does not stop a later fencer from being promoted there.

Demotion for non-payment already moves a whole registration and SHALL continue to.

#### Scenario: Promoting a conditional registration
- **WHEN** the organizer promotes a registration waiting on Longsword and Sabre and both have free places
- **THEN** both are seated at once and the registration is billed for both

#### Scenario: Arrow withheld while one discipline is full
- **WHEN** Longsword frees a place but Sabre is still full
- **THEN** the registration's Longsword row states that it also waits for Sabre and carries no promote arrow

#### Scenario: A later fencer may be promoted past it
- **WHEN** the conditional registration stands first in the Longsword queue and cannot be seated
- **THEN** the second fencer in that queue carries the promote arrow and may be seated

#### Scenario: Returning one placement of a condition returns all
- **WHEN** the organizer returns the Sabre placement of a registration seated in Longsword and Sabre under a condition
- **THEN** both placements are queued and the registration owes nothing

#### Scenario: A placement outside the condition moves alone
- **WHEN** the organizer returns the Rapier placement of a registration whose condition is Longsword and Sabre
- **THEN** only Rapier is queued
