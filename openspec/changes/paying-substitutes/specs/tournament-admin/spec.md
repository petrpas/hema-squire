## ADDED Requirements

### Requirement: Paying substitutes may take free places
Per tournament, the organizer SHALL be able to set whether **substitutes who pay take free places by themselves**. It SHALL be off by default, and off for every tournament that existed before it.

It SHALL be offered in Setup among the payment and reservation parameters, and only on an automatic tournament whose payments feature is on: on a manual tournament Squire queues nobody, and without payments there is nothing to pay. Where it is not offered its stored value SHALL be retained and offered again unchanged, as every hidden parameter is.

It SHALL be offered with a statement of its consequence in one line each way: off — money sent from the queue waits for the organizer, who seats the fencer or refunds it; on — a fencer waiting in the queue is told what to pay, and their payment takes the places they wait for if all are free when it is credited, or as soon as they free. The statement SHALL say that with it on the queue's order no longer decides who gets a place.

It SHALL be changeable at any time, before and after seating settles and after publication. Turning it off SHALL stop instructions being offered to the queue and SHALL leave every payment already held held for the organizer; turning it on SHALL let held payments seat on the next matching pass where the places are free.

#### Scenario: Off by default
- **WHEN** an organizer creates a tournament
- **THEN** paying substitutes do not take places by themselves

#### Scenario: Not offered on a manual tournament
- **WHEN** the organizer of a manual tournament opens the payment parameters
- **THEN** the setting is not offered

#### Scenario: Turned on after seating settled
- **WHEN** the organizer turns the setting on after seating settled, while a payment from the queue is held and its discipline has a free place
- **THEN** the next matching pass seats that fencer
