## MODIFIED Requirements

### Requirement: Finished mail and expired tokens are deleted
A scheduler pass SHALL delete an outgoing message 30 days after it was sent or given up on, an expired pending signup, an expired password reset, and an expired address change. A message still waiting for delivery SHALL NOT be deleted.

#### Scenario: Sent message ages out
- **WHEN** a pass runs 31 days after a message was sent
- **THEN** the message no longer exists

#### Scenario: Waiting message stays
- **WHEN** a message has not finished delivery
- **THEN** it stays and keeps being retried

#### Scenario: An expired address change goes
- **WHEN** a pass runs after an address-change link has expired unfollowed
- **THEN** the pending change, with the address it named, no longer exists
