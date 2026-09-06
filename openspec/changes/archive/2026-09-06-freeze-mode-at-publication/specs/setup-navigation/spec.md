## MODIFIED Requirements

### Requirement: The tournament's settings are configured on one surface
A tournament's mode, its payments setting and the three features it may include SHALL be offered together on **one surface**, never on a sequence of screens and never split between sections that describe one configuration in parts.

The surface SHALL present them in three tiers, in this order, and SHALL make the ordering legible rather than merely sequential:

1. the **mode** — automatic or manual (`tournament-mode`) — as a choice between two, with automatic preselected, **on a tournament that is still a draft**. Once the tournament is published the mode SHALL be **stated rather than offered**: it is fixed at publication, and a control that exists only to be refused teaches an organizer that the product argues with them. It SHALL NOT be hidden, since "which mode is this?" is a question the surface should answer;
2. the **payments** setting (`payments`);
3. **what the tournament includes** — schedule, team disciplines, extra services (`tournament-features`) — as independent checkboxes.

The first two SHALL be presented as decisions about what Squire does, and the third as a statement of what Setup offers, so that an organizer can see which of their choices carry consequences beyond the console. The third tier SHALL carry no collective name and no summary of how many are enabled.

Each of the three features SHALL carry a help hint stating which tournaments it is for; the mode's two values and the payments setting SHALL each carry a hint stating the consequence rather than restating the label.

#### Scenario: All three tiers on one surface
- **WHEN** the organizer opens the tournament's settings on a draft
- **THEN** the mode, the payments setting and the three inclusions are all present, in that order, each of them choosable

#### Scenario: The mode is stated once the tournament is published
- **WHEN** the organizer opens the settings of a published tournament
- **THEN** its mode is stated in words with no control to change it, and the payments setting and the three inclusions are offered as before

#### Scenario: No tier name over the inclusions
- **WHEN** the organizer has none of the three features enabled
- **THEN** the surface states which features are off and gives that condition no name

#### Scenario: Consequence in the hint
- **WHEN** the organizer reaches the help marker beside the manual mode
- **THEN** a hint states that fencers cannot register in the application and Squire sends them nothing, rather than restating the word
