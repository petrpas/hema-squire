## MODIFIED Requirements

### Requirement: Clearing is refused where money has been credited
Clearing SHALL be refused where any transaction holds a live credit against a
registration, and SHALL state how many do. A refused clear SHALL remove nothing
at all — not the uncredited transactions, not the stored interpretations.

The refusal SHALL stand on what the credit means and not on what unwinding it
would cost. Reversing credits and letting the balances follow is now an ordinary
operation, so the refusal is no longer a limit of the mechanism; it is a
statement that a credited payment was acted on. A fencer was told they are paid,
a seat was confirmed, mail may have gone out, and "that import never happened"
is not something anyone can say about it afterwards. The same rule already
governs deleting a tournament, which is refused once registrations exist because
financial history is not the console's to erase.

The organizer resolves those payments first — withdrawing a link, removing a
recorded payment, or reversing a credited transaction on its own — after which
the clear proceeds normally. Every credited transaction SHALL have such a route
out, so that the refusal is never a dead end.

#### Scenario: Credited money stops the clear
- **WHEN** the organizer clears a tournament in which four transactions hold live credits
- **THEN** the clear is refused, states that four transactions hold credit, and removes nothing

#### Scenario: A refusal is total, not partial
- **WHEN** a tournament holds forty unresolved transactions and one credited one and the organizer clears
- **THEN** all forty-one remain, and no stored interpretation is removed

#### Scenario: Unresolved money clears freely
- **WHEN** no transaction holds a live credit
- **THEN** the clear proceeds

#### Scenario: Clearing after the payments are reversed
- **WHEN** the organizer reverses the credited transactions and clears again
- **THEN** the clear proceeds

#### Scenario: An automatically matched transaction is not a dead end
- **WHEN** the clear is refused on a tournament whose only credited transaction was matched automatically
- **THEN** that transaction can be reversed on its own, after which the clear proceeds

#### Scenario: A reversed credit does not hold the clear
- **WHEN** a transaction's credit has been reversed and the organizer clears
- **THEN** it does not count among the transactions holding credit
