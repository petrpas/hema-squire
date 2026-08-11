## ADDED Requirements

### Requirement: Rosters are edited on the detail page's Teams tab
Every roster the entering fencer may edit for a tournament SHALL be presented together on
the tournament detail page's `Teams` tab, one editor per team, in the order the teams
stand on the registration. No roster editor SHALL be rendered on the `Registered` tab:
that tab states what the registration holds and what it costs, and the money lines there
SHALL continue to name each team and list its members as read-only text.

Each team's editor SHALL be enclosed in its own bordered block drawn with a solid rule,
and consecutive blocks SHALL be separated by vertical space, so no two team borders touch
or share an edge.

The control that adds a member SHALL be offered as a link, in the same shape as every
other add control in the application, rather than as a filled or bordered button. It
SHALL continue to be withheld when the roster already holds the discipline's maximum.

A member's name field SHALL be underlined by the ordinary hairline rule at rest and SHALL
take the accent rule only while focused. The accent-coloured rule SHALL NOT be used to
draw an unfocused member row, since it reads there as an error state that no member row
is in.

#### Scenario: Rosters reached through the Teams tab
- **WHEN** an entering fencer holding two teams opens the `Teams` tab
- **THEN** both roster editors are shown, each in its own solid-bordered block with space between them

#### Scenario: Registration tab keeps the money only
- **WHEN** the same fencer opens the `Registered` tab
- **THEN** each team appears as a priced line listing its members as text, and no roster editor, add control, or save control is offered there

#### Scenario: Adding a member is a link
- **WHEN** a roster below its discipline's maximum is shown
- **THEN** the add-member control is rendered as a link, matching the add controls elsewhere in the application

#### Scenario: Add control withheld at the maximum
- **WHEN** a roster already holds the discipline's maximum number of members
- **THEN** no add-member control is offered

#### Scenario: Member rows are not drawn as errors
- **WHEN** a roster of three valid members is shown and none of the name fields is focused
- **THEN** no member row carries an accent-coloured or thickened underline

### Requirement: One save commits every roster on the tab
The `Teams` tab SHALL offer exactly one save control, standing at the foot of the tab
below the last team's block, whatever the number of teams. Per-team save controls SHALL
NOT be offered. The control SHALL be sized to its own label rather than stretched to the
width of its container.

The control SHALL be inactive while no roster on the tab has unsaved changes, and active
as soon as any one of them has. Activating it SHALL save every team whose roster changed,
each through that team's own roster endpoint, and SHALL leave untouched teams alone.

WHEN one team's save fails while another's succeeds, the successful saves SHALL stand,
the failed teams SHALL keep their unsaved changes and stay dirty, and a single message
SHALL name the teams that were not saved. A failure SHALL NOT discard any edit and SHALL
NOT prevent the remaining teams from being attempted.

#### Scenario: One control for several teams
- **WHEN** the `Teams` tab shows three roster editors
- **THEN** exactly one save control is rendered, at the foot of the tab, no wider than its own label

#### Scenario: Save inactive until something changes
- **WHEN** the tab is opened and no roster has been touched
- **THEN** the save control is inactive, and it becomes active as soon as a member is added, renamed, reordered, rebound, or removed on any team

#### Scenario: Only changed rosters are written
- **WHEN** the fencer edits one of three teams and saves
- **THEN** only that team's roster is written, and the other two teams' rosters are not resubmitted

#### Scenario: Partial failure named
- **WHEN** two teams are dirty and one of the two saves fails
- **THEN** the successful team is saved and clean, the failed team keeps its edits and stays dirty, and the message names the team that was not saved

### Requirement: A bound member's HEMA Ratings identifier is shown on its row
A roster editor SHALL show, for each member, the HEMA Ratings identifier the member is
bound to, in its own column beside the name. The identifier SHALL be rendered as plain
text in the form `#<id>` and SHALL NOT be a link or any other control.

The column SHALL be left empty for an unbound member. An empty cell SHALL carry no
placeholder, no warning, and no mark: an unbound member remains a complete member
(requirement "A roster member is a named person, never an account").

#### Scenario: Bound member shows its identifier
- **WHEN** a roster holds a member bound to HEMA Ratings profile 1234
- **THEN** that member's row shows `#1234` as plain text alongside the name

#### Scenario: Unbound member shows nothing
- **WHEN** a roster holds a member typed in by name with no profile
- **THEN** that member's identifier cell is empty, with no placeholder and no warning

#### Scenario: Identifier follows a rebinding
- **WHEN** the fencer rebinds a member to a different HEMA Ratings profile
- **THEN** the row shows the new profile's identifier
