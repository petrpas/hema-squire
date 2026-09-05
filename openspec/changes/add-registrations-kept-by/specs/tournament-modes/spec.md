## MODIFIED Requirements

### Requirement: A tournament carries four feature flags
Each tournament SHALL carry four independent boolean features — **schedule**, **payments**, **team disciplines**, **extra services** — stored with the tournament and governing which of Squire's advanced surfaces its console offers. They are a property of the tournament, not of the account reading it: every member of a tournament's console team SHALL see the same features enabled.

A tournament created after this change SHALL have all four off. The features SHALL be changeable at any point in the tournament's life, including after publication, by any account with console access to it, under the same authorization as any other Setup write.

No feature SHALL be derived, inferred, or re-derived at runtime from the tournament's contents. Adding a team discipline SHALL NOT turn the team feature on; removing the last extra item SHALL NOT turn extra services off. The features record what the organizer asked to see.

The four features SHALL be the whole of this axis, and the axis SHALL be understood as governing **which advanced surfaces the console offers**. Who keeps the tournament's registrations is a different axis, stored separately and fixed by `registration-ownership`; it SHALL NOT be added here as a fifth feature, SHALL NOT be counted when easy and advanced mode are named, and neither axis SHALL be derived from the other. The two are independent because they answer different questions: these four decide what the organizer sees, while that one decides whether Squire owns the roster at all — which is why turning a feature off hides settings without changing what fencers experience, and being organizer-kept withdraws the registration form outright.

#### Scenario: Features stored with the tournament
- **WHEN** two organizers on one tournament's console team open its Setup phase
- **THEN** both see the same features enabled and the same sections offered

#### Scenario: New tournament starts with none
- **WHEN** an organizer creates a tournament and dismisses the mode dialog
- **THEN** all four features are off

#### Scenario: Features are not re-derived
- **WHEN** an organizer with the team feature off adds a team discipline through the API
- **THEN** the team feature stays off and the discipline is stored

#### Scenario: Mode changed after publication
- **WHEN** an organizer turns on extra services on a published tournament
- **THEN** the change is accepted and the `EXTRA` tab appears

#### Scenario: The two axes do not move each other
- **WHEN** an organizer sets a tournament to organizer-kept and then enables payments
- **THEN** the tournament is organizer-kept with the payments feature on, and neither setting changed the other
