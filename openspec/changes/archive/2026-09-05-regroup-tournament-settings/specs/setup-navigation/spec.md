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

### Requirement: The settings surface is the second half of creating a tournament
Creating a tournament SHALL take its display name, date and slug on one panel and its settings on the next, in one window, with no further dialog after them.

**No tournament SHALL exist until the settings panel is confirmed.** The two panels are one act: the request that creates the tournament SHALL carry its settings, so there is no moment at which a tournament exists without them and none at which one exists because of a step the organizer then backed out of.

The settings panel SHALL be dismissible, and dismissing it SHALL return to the naming panel with every field holding what was typed, having created nothing. Dismissing the naming panel SHALL abandon the creation.

Because the tournament is created at the end, a refusal — a slug already taken, or any other — SHALL be reported on the naming panel with the input intact, whichever panel the organizer was on when it was raised.

The settings panel SHALL NOT ask for confirmation of what it is about to write. Confirmation exists to count what a change would hide and whom it would affect, and a tournament that does not yet exist holds nothing and has taken no registrations.

#### Scenario: Settings chosen at creation
- **WHEN** an organizer names a tournament, chooses manual mode, ticks team disciplines and confirms
- **THEN** the tournament is created manual with the team feature on and the other two off, and the console opens on Setup

#### Scenario: Cancelling the settings panel creates nothing
- **WHEN** an organizer names a tournament, reaches the settings panel and cancels
- **THEN** no tournament has been created, and the naming panel is shown again holding the name, date and slug that were typed

#### Scenario: Confirming with nothing chosen
- **WHEN** an organizer confirms the settings panel without changing anything
- **THEN** the tournament is created in automatic mode with every feature off, and the console opens on Setup

#### Scenario: A taken slug is reported where it was typed
- **WHEN** the creation is refused because the slug is taken
- **THEN** the naming panel is shown again with the input intact and the reason stated, and no tournament exists

#### Scenario: Nothing is confirmed twice
- **WHEN** an organizer chooses manual mode on the settings panel at creation
- **THEN** no confirmation is asked for, because nothing is being hidden and nobody has registered

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
