## ADDED Requirements

### Requirement: An organizer may cancel a registration
An organizer with console access SHALL be able to cancel a live registration of a
published tournament, on the fencer list, in either mode. The cancellation SHALL do to the
registration exactly what the fencer's own cancellation does, through the same path: the
registration becomes cancelled, every seat and queue place it held is freed, no clock of
its runs on, and where money had been credited the refund state is recorded as it is when
the fencer cancels. The organizer settles any refund outside Squire.

It SHALL be confirmed before it is made and SHALL NOT be reversible. A seat freed by it
may already be taken by the time anyone thinks better of it. A person cancelled in error
registers again, or is entered again by the organizer.

Nobody SHALL be promoted by it. A freed seat waits for the organizer's promotion from the
queue, as it does after the fencer's own cancellation.

The fencer SHALL be told by mail that the organizer has cancelled their registration,
naming the tournament and what the registration held, with the organizer's note where one
was given, and, where money had been credited, that a refund is the organizer's to
settle. The mail follows the rule every message about a seat follows: a registration
entered by hand is sent nothing, and so is one with no address. The cancellation SHALL
take effect whether or not a mail is sent.

#### Scenario: The seat is freed
- **WHEN** the organizer cancels a reserved registration seated in a full discipline of capacity 32
- **THEN** the registration reads cancelled, the discipline holds 31, and nobody from the queue is seated by it

#### Scenario: The clocks stop
- **WHEN** the organizer cancels a reservation whose payment window has two days to run
- **THEN** no reminder and no expiry notice is sent for it afterwards

#### Scenario: Money credited is marked for refund
- **WHEN** the organizer cancels a paid registration while refunds are possible
- **THEN** its refund state reads pending, exactly as if the fencer had cancelled it, and no money is moved by Squire

#### Scenario: The fencer is told
- **WHEN** the organizer cancels a registration made in the application, adding the note "duplicate entry"
- **THEN** the fencer receives one mail naming the tournament, what was cancelled and the note

#### Scenario: A hand-entered seat is not mailed
- **WHEN** the organizer cancels a registration they entered by hand
- **THEN** it is cancelled and no mail is sent

#### Scenario: Not undone
- **WHEN** the organizer has cancelled a registration
- **THEN** no console action offers to restore it
