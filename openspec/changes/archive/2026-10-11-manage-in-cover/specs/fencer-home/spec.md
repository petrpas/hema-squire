## MODIFIED Requirements

### Requirement: Managing a tournament from its card
A card in any tab, and the tournament's detail, SHALL carry a **Spravovat** control when, and only when, the account reading it may manage that tournament — as its Tournament Owner or as a member of its console team. The control SHALL open that tournament's console. It SHALL be the only difference between what an organizer sees on the list or the detail and what anyone else sees.

The control SHALL be a quiet secondary button: a small pill outlined in `--hairline-strong` with `--ink-soft` text, never filled, so it stays apart from the screen's one primary action. It SHALL stand in the bottom right corner of the cover band, on the card and on the detail alike. On a phone, where the card has no cover band, it SHALL stand at the card's trailing edge below the foot.

The control SHALL be a link carrying the console's URL, so middle-click and modifier-click open it in a new browser tab, and SHALL be reachable without opening the card: activating it SHALL open the console and SHALL NOT also open the fencer-facing detail the card links to.

It SHALL appear on a past tournament's card as it does on an upcoming one — a held tournament's console is still where its records are read — and SHALL be absent for an anonymous visitor, who may manage nothing.

#### Scenario: Owner sees the control
- **WHEN** a Tournament Owner opens the tournament list and their tournament is listed
- **THEN** that card carries a Spravovat control and no other card does

#### Scenario: Console team member sees the control
- **WHEN** a console team member who is not the owner opens the same list
- **THEN** the card carries the same control

#### Scenario: Plain fencer sees no control
- **WHEN** a fencer who neither owns nor staffs any tournament opens the list
- **THEN** no card carries a Spravovat control

#### Scenario: The control opens the console, not the detail
- **WHEN** an organizer activates Spravovat on a card
- **THEN** that tournament's console opens and the fencer-facing detail does not

#### Scenario: The control is a link
- **WHEN** an organizer middle-clicks Spravovat
- **THEN** the console opens in a new browser tab at that tournament's console URL

#### Scenario: A held tournament can still be managed
- **WHEN** an organizer finds a tournament they ran last month in the Past tab
- **THEN** its card carries the Spravovat control

#### Scenario: Anonymous visitor sees no control
- **WHEN** a visitor with no account opens the list
- **THEN** no card carries a Spravovat control

#### Scenario: The control on the detail
- **WHEN** a Tournament Owner opens their tournament's detail
- **THEN** the cover's bottom right corner carries a Spravovat button leading to the console, and a plain fencer opening the same detail sees none

#### Scenario: A quiet button, not a link
- **WHEN** an organizer's card or detail shows the control
- **THEN** it is drawn as a small outlined pill, not as underlined text and not filled

#### Scenario: In the cover's corner
- **WHEN** an organizer's card is shown on a desktop width
- **THEN** its Spravovat button stands in the bottom right corner of the cover band, clear of the plate and the status block, and activating it opens the console, not the detail
