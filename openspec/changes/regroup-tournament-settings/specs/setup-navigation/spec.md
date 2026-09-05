## ADDED Requirements

### Requirement: The tournament's settings are configured on one surface
A tournament's mode, its payments setting and the three features it may include SHALL be offered together on **one surface**, never on a sequence of screens and never split between sections that describe one configuration in parts.

The surface SHALL present them in three tiers, in this order, and SHALL make the ordering legible rather than merely sequential:

1. the **mode** — automatic or manual (`tournament-mode`) — as a choice between two, with automatic preselected;
2. the **payments** setting (`payments`);
3. **what the tournament includes** — schedule, team disciplines, extra services (`tournament-features`) — as independent checkboxes.

The first two SHALL be presented as decisions about what Squire does, and the third as a statement of what Setup offers, so that an organizer can see which of their choices carry consequences beyond the console. The third tier SHALL carry no collective name and no summary of how many are enabled.

Each of the three features SHALL carry a help hint stating which tournaments it is for; the mode's two values and the payments setting SHALL each carry a hint stating the consequence rather than restating the label.

#### Scenario: All three tiers on one surface
- **WHEN** the organizer opens the tournament's settings
- **THEN** the mode, the payments setting and the three inclusions are all present, in that order

#### Scenario: No tier name over the inclusions
- **WHEN** the organizer has none of the three features enabled
- **THEN** the surface states which features are off and gives that condition no name

#### Scenario: Consequence in the hint
- **WHEN** the organizer reaches the help marker beside the manual mode
- **THEN** a hint states that fencers cannot register in the application and Squire sends them nothing, rather than restating the word

### Requirement: The settings surface is shown once a tournament is created
Creating a tournament SHALL open the settings surface once the tournament exists, after the dialog that takes its display name, date and slug, and SHALL NOT show a further dialog after it.

The surface SHALL be dismissible. Dismissing it SHALL leave the created tournament exactly as it was created — automatic mode, payments off, no features — and SHALL open the console's Setup phase exactly as confirming it does. A tournament SHALL NOT be left uncreated, half-created, or unreachable by a setting that was never chosen.

A failure to create the tournament SHALL NOT reach the settings surface: the organizer SHALL stay in the creation dialog with their input intact.

#### Scenario: Settings chosen at creation
- **WHEN** an organizer creates a tournament, chooses manual mode and ticks team disciplines
- **THEN** the tournament is manual with the team feature on, the other two features off, and the console opens on Setup

#### Scenario: Surface dismissed
- **WHEN** an organizer creates a tournament and closes the settings surface without choosing
- **THEN** the tournament exists in automatic mode with payments off and no features, and the console opens on Setup

#### Scenario: One surface, not two
- **WHEN** an organizer confirms the settings surface at creation
- **THEN** no further settings dialog opens, and the console opens on Setup

#### Scenario: Creation failure never reaches the settings
- **WHEN** the creation dialog is rejected because the slug is taken
- **THEN** the settings surface does not open and the organizer stays in the creation dialog with their input intact

### Requirement: OTHER carries one settings section
The Setup phase's `OTHER` tab SHALL carry **one** section stating the tournament's whole configuration — its mode, its payments setting, and which of the three features are enabled — in words, with a single control that reopens the settings surface on the tournament's current values. It SHALL NOT carry a second section describing any part of that configuration.

Confirming the surface SHALL apply the settings immediately and SHALL refresh the tab bar and the sections around it, without leaving Setup.

The section SHALL follow the `OTHER` tab's rule that its actions carry their own controls: it SHALL NOT be written by a save control, and `OTHER` SHALL continue to carry none.

#### Scenario: One section states everything
- **WHEN** the organizer opens `OTHER` on a manual tournament with payments on and extra services enabled
- **THEN** one section states that the tournament is manual, that it collects payments, and that it includes extra services, and offers one control to change any of it

#### Scenario: No second section
- **WHEN** the organizer reads `OTHER`
- **THEN** no separate section describes the mode, the payments setting or the features on its own

#### Scenario: Change applies at once
- **WHEN** the organizer enables extra services through the settings surface on `OTHER`
- **THEN** the `EXTRA` tab appears without a save and without leaving Setup
