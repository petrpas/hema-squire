## ADDED Requirements

### Requirement: Publication's completeness guarantee survives every later change
A tournament that was complete when it was published SHALL NOT be made incomplete by any change permitted afterwards. Completeness is the one guarantee the registration path relies on, and it attaches at publication; a setting that could withdraw it after the fact would make the guarantee conditional on nobody having exercised that setting.

The mode is the setting that could. A manual tournament must record the address of its external registration to be published, so switching a published tournament to manual would leave it complete when published and incomplete now, with every later Setup save refused until the address was supplied. `tournament-mode` closes this by fixing the mode at publication.

Where a setting that remains changeable *can* add a mandatory item — the payments setting adds a bank account on a tournament that charges — the item SHALL be reported and the tournament SHALL remain published, as fixed above: completeness attaching later never un-publishes.

#### Scenario: No published tournament is made incomplete by a mode
- **WHEN** an organizer attempts to change a published tournament's mode
- **THEN** the attempt is refused, and no published tournament is ever missing its external registration address on account of a mode changed after publication

#### Scenario: A changeable setting may still report an item
- **WHEN** the organizer of a published, priced tournament turns the payments setting on with no bank account recorded
- **THEN** the account is reported as missing and the tournament stays published
