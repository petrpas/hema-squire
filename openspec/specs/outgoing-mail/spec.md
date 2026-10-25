# outgoing-mail Specification

## Purpose
How every message leaves Squire: queued with the action that causes it and delivered with retry, every registration message linking to its tournament, and dates written as the message's language writes them.

## Requirements

### Requirement: A message is queued with the action that causes it
Every message Squire sends SHALL be recorded as an outgoing message in the same database transaction as the action that causes it, and SHALL be delivered only after that transaction commits. A message SHALL exist exactly when its cause took effect: an action that is rolled back SHALL leave no message behind, and an action that commits SHALL leave its message queued whether or not it can be delivered at that moment.

Delivery SHALL be attempted promptly after the commit, so that a message a person is waiting for — a verification link, a confirmation — normally arrives within seconds. A message whose delivery fails SHALL stay queued and SHALL be retried by every later scheduler pass, with the failure and the attempt count recorded on it. A message SHALL be marked sent only once the transport has accepted it, and SHALL NOT be delivered again after that.

An action SHALL NOT fail because its mail could not be delivered. The response to a person reports the action, which took effect. Delivery is a separate matter that the queue owns.

A message that still has not been delivered after the retry budget is spent SHALL stay recorded as failed and SHALL be logged at error level. It SHALL NOT be deleted.

#### Scenario: Transport down during a registration
- **WHEN** a fencer registers while the SMTP server refuses connections
- **THEN** the registration is created and the response reports success, the confirmation is queued with the failure recorded, and it is delivered by the first scheduler pass after the server recovers

#### Scenario: A rolled-back action sends nothing
- **WHEN** an action that composes a message fails after composing it and its transaction is rolled back
- **THEN** no message is queued and nothing is delivered

#### Scenario: A delivered message is not resent
- **WHEN** a message has been accepted by the transport and a later scheduler pass runs
- **THEN** the message is not delivered again

### Requirement: A failed scheduler pass leaves no partial state
When the processing of one tournament in a scheduler pass raises, the system SHALL roll back everything that tournament's processing had not yet committed before it moves to the next tournament. A later tournament's commit SHALL NOT carry an earlier tournament's partial state. Together with queued delivery, this SHALL mean that a registration is stamped as reminded, expired or notified exactly when the message saying so is queued.

#### Scenario: A failure mid-batch
- **WHEN** the reminder pass for one tournament raises on its third registration and the pass then processes a second tournament
- **THEN** none of the first tournament's three registrations is stamped as reminded and none of their reminders is queued, the second tournament is processed normally, and the next pass reminds all three once

### Requirement: Every registration message links to its tournament
Every message about a registration SHALL carry a link to the public page of its tournament, built from the configured public origin of the app. The link SHALL carry no key and SHALL grant nothing by itself; managing the registration from it requires signing in, or for a guest registration the manage link, which a guest's message carries in addition.

#### Scenario: An account holder's confirmation
- **WHEN** an account holder registers
- **THEN** the confirmation carries the link to the tournament's page and no manage link

#### Scenario: A guest's message
- **WHEN** a message about a guest registration is sent
- **THEN** it carries both the link to the tournament's page and the guest's manage link

### Requirement: Dates in messages follow the communication language
Every date a message states SHALL be formatted by one function from the message's language, as a day-month-year date in that language's own convention. Czech is `25. 10. 2026` and English is `25 October 2026`. No message SHALL state a date in ISO form or in a format chosen by the individual send. A deadline stored as an instant SHALL be stated as its day in the tournament's zone.

#### Scenario: One format across messages
- **WHEN** a Czech tournament sends a confirmation stating its payment window and a promotion notice stating its due date
- **THEN** both dates read in the form `25. 10. 2026`

#### Scenario: English date
- **WHEN** an English tournament's reminder states its seating deadline of 1 March 2027
- **THEN** it reads `1 March 2027`
