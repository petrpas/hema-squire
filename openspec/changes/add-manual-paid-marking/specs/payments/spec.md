## ADDED Requirements

### Requirement: An organizer may mark a registration settled by hand
WHERE Squire does not handle a tournament's payments, an organizer with console access SHALL be able to mark a registration paid, and to unmark it. This SHALL be the only way a registration reaches the paid state on such a tournament, and the organizer's own knowledge SHALL be its whole basis: they collected the money, and nothing else in the system saw it.

The mark SHALL record the verdict and **SHALL NOT record an amount**. The registration's state becomes paid; the counters holding what Squire has received SHALL be left exactly as they were. Those counters mean money that passed through Squire and were filled by reconciliation reading a bank statement; a figure written into them from a mark would be indistinguishable afterwards from one Squire observed.

A hand-settled registration SHALL therefore read as paid while what it is owed remains what it always was. Every surface presenting both SHALL be able to explain the difference, because a reader who takes the outstanding figure for an error would be misreading the one thing that is true: the fencer owes the organizer nothing, and Squire received nothing.

Marking SHALL be refused on a tournament whose payments Squire handles, with a stated reason. There the paid state follows from credited transactions alone, and a second writer would mean a statement imported later could contradict a person with neither knowing.

Both marking and unmarking SHALL be recorded as payment events naming the organizer who acted, so that a roster stating that someone has paid can always state who said so and when.

The mark SHALL answer a yes-or-no question and SHALL NOT express partial settlement. A tournament that needs amounts tracked wants Squire handling its payments.

#### Scenario: The organizer marks a fencer settled
- **WHEN** the organizer of a tournament that handles its own payments marks a registration paid
- **THEN** the registration's state becomes paid, what Squire has received stays at nothing, and the action is recorded against the organizer

#### Scenario: Unmarking returns it
- **WHEN** the organizer unmarks a registration they had marked
- **THEN** it is no longer paid, and both the marking and the unmarking stand in the record

#### Scenario: Refused where Squire collects
- **WHEN** an organizer attempts to mark a registration paid on a tournament whose payments Squire handles
- **THEN** the attempt is refused with a stated reason and the registration is unchanged

#### Scenario: What Squire received is not invented
- **WHEN** a hand-settled registration is read
- **THEN** the amount Squire has received against it is nothing, and what the registration is owed is unchanged

#### Scenario: Switching to Squire-handled payments states what is carried
- **WHEN** the organizer of a tournament holding hand-settled registrations switches it to having Squire handle the payments
- **THEN** the confirmation states how many registrations are marked paid without any money behind them
