## MODIFIED Requirements

### Requirement: A message is queued with the action that causes it
Every message Squire sends SHALL be recorded as an outgoing message in the same database transaction as the action that causes it, and SHALL be delivered only after that transaction commits. A message SHALL exist exactly when its cause took effect: an action that is rolled back SHALL leave no message behind, and an action that commits SHALL leave its message queued whether or not it can be delivered at that moment.

Delivery SHALL be attempted promptly after the commit, so that a message a person is waiting for — a verification link, a confirmation — normally arrives within seconds. A message whose delivery fails SHALL stay queued and SHALL be retried by every later scheduler pass, with the failure and the attempt count recorded on it. A message SHALL be marked sent only once the transport has accepted it, and SHALL NOT be delivered again after that.

An action SHALL NOT fail because its mail could not be delivered. The response to a person reports the action, which took effect. Delivery is a separate matter that the queue owns.

A message that still has not been delivered after the retry budget is spent SHALL stay recorded as failed and SHALL be logged at error level. It SHALL NOT be deleted, except where `account-deletion` removes the messages addressed to an erased person.

#### Scenario: Transport down during a registration
- **WHEN** a fencer registers while the SMTP server refuses connections
- **THEN** the registration is created and the response reports success, the confirmation is queued with the failure recorded, and it is delivered by the first scheduler pass after the server recovers

#### Scenario: A rolled-back action sends nothing
- **WHEN** an action that composes a message fails after composing it and its transaction is rolled back
- **THEN** no message is queued and nothing is delivered

#### Scenario: A delivered message is not resent
- **WHEN** a message has been accepted by the transport and a later scheduler pass runs
- **THEN** the message is not delivered again

#### Scenario: An erased person's messages go
- **WHEN** an account deletion executes while a message to its address waits or has failed
- **THEN** the message is removed and is not delivered
