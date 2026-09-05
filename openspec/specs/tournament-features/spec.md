# tournament-features Specification

## Purpose
Define the three features a tournament may include — schedule, team disciplines
and extra services — which govern which controls Setup offers and nothing else:
how they are stored, how they are chosen and changed, what turning one off hides
and what it never writes, what each governs, and how tournaments predating them
are derived from what they use.

They share one property without exception: turning any of them off changes
nothing a fencer experiences. A hidden extra item is still sold, a hidden team
discipline still takes teams. The two settings that *do* change what Squire does
are not here — the tournament's mode is fixed by `tournament-mode` and its
payments setting by `payments`.

There is no name for the three taken together and none for having none of them.
That was the defect this capability was split out of: a tier called "easy mode"
was never stored, so every surface derived it and the dialog offering it had to
invent an answer for a choice its data could not hold.
## Requirements
### Requirement: A tournament carries three feature flags
Each tournament SHALL carry three independent boolean features — **schedule**, **team disciplines**, **extra services** — stored with the tournament and governing which of Squire's advanced surfaces its console offers. They are a property of the tournament, not of the account reading it: every member of a tournament's console team SHALL see the same features enabled.

These three SHALL be the whole of this capability, and they SHALL share one property that admits no exception: **each governs which controls Setup offers and nothing else**. Turning any of them off SHALL change nothing a fencer experiences. A tournament's payments setting is not among them — it suspends machinery rather than hiding controls, and is fixed by `payments`. Neither is a tournament's mode, which is fixed by `tournament-mode`.

There SHALL be no name for the three taken together, and no state derived from how many are enabled. A tournament with none of them is a tournament with none of them; naming that condition would name something that is not stored, and every surface would then have to derive the name and answer for a choice no value can hold.

A tournament created after this change SHALL have all three off. They SHALL be changeable at any point in the tournament's life, including after publication, by any account with console access to it, under the same authorization as any other Setup write.

No feature SHALL be derived, inferred, or re-derived at runtime from the tournament's contents. Adding a team discipline SHALL NOT turn the team feature on; removing the last extra item SHALL NOT turn extra services off. The features record what the organizer asked to see.

#### Scenario: Features stored with the tournament
- **WHEN** two organizers on one tournament's console team open its Setup phase
- **THEN** both see the same features enabled and the same sections offered

#### Scenario: New tournament starts with none
- **WHEN** an organizer creates a tournament and dismisses the settings screen
- **THEN** all three features are off

#### Scenario: No name is given to having none
- **WHEN** an organizer turns off the last enabled feature
- **THEN** the tournament is described by what it includes and what it does not, and no tier or mode name is stated on account of the three

#### Scenario: Features are not re-derived
- **WHEN** an organizer with the team feature off adds a team discipline through the API
- **THEN** the team feature stays off and the discipline is stored

#### Scenario: Features changed after publication
- **WHEN** an organizer turns on extra services on a published tournament
- **THEN** the change is accepted and the `EXTRA` tab appears

### Requirement: Disabling a feature hides its settings without changing them
Turning a feature off SHALL hide the settings it governs and SHALL NOT write, clear, reset, or delete any of them. Every stored value the hidden settings hold — a team discipline's roster bounds, an extra item's price and options, a discipline's `when` and `where` — SHALL be retained exactly as it was. Turning the feature back on SHALL show those settings holding the values they held before, with nothing to restore and nothing to re-enter.

A hidden setting SHALL remain in force for every check that reads the tournament's contents rather than its features. In particular, a team discipline hidden by the team feature SHALL still be checked for valid roster bounds by the setup completeness rule, because the discipline still exists and is still offered to fencers.

#### Scenario: Values survive being hidden
- **WHEN** the organizer turns off extra services on a tournament with three priced extra items, then turns extra services back on
- **THEN** the three items are present with their prices, options and schedule fields unchanged

#### Scenario: Disabling writes nothing
- **WHEN** the organizer turns off the schedule feature on a tournament whose disciplines carry a time, a place and a ruleset
- **THEN** all three values are retained unchanged and no other tournament field is written

#### Scenario: Hidden data still checked for completeness
- **WHEN** a tournament with the team feature off has a team discipline with no roster bounds
- **THEN** the `PUBLISH` tab still reports those roster bounds as blocking publication

### Requirement: Turning off a feature the tournament uses is warned and confirmed
WHEN the organizer turns off a feature the tournament already uses, the dialog SHALL state what will be hidden, counting the affected items — team disciplines, extra items, disciplines carrying schedule fields — and SHALL require confirmation before applying the change. Declining SHALL leave every feature as it was.

Turning a feature **on** SHALL NOT be warned or confirmed.

Hiding a feature SHALL NOT change anything a fencer experiences — without exception, since every feature this capability holds governs Setup's controls alone. A hidden extra item SHALL still be offered on the registration form and still be sold; a hidden team discipline SHALL still take teams; a hidden `when` SHALL still be shown wherever the tournament is described. The warning SHALL say so, so that the organizer is hiding settings they are finished with rather than withdrawing products they are selling.

#### Scenario: Warning counts what is hidden
- **WHEN** the organizer turns off team disciplines on a tournament with two team disciplines
- **THEN** the dialog states that two team disciplines will be hidden and asks for confirmation

#### Scenario: Declining changes nothing
- **WHEN** the organizer declines the confirmation
- **THEN** every feature is as it was and no setting is written

#### Scenario: Unused feature turned off without a warning
- **WHEN** the organizer turns off extra services on a tournament with no extra items
- **THEN** the change applies with no warning

#### Scenario: Turning a feature on is never warned
- **WHEN** the organizer turns on team disciplines
- **THEN** the change applies with no warning and no confirmation

#### Scenario: Hidden items are still sold
- **WHEN** a tournament with extra services turned off is open for registration
- **THEN** the registration form still offers its extra items and still charges for them

### Requirement: The schedule feature governs the disciplines' when and where
WHEN the schedule feature is off, the discipline table SHALL NOT offer a discipline's `when` and `where` fields. When it is on, they SHALL be offered as fixed by `tournament-admin`.

An extra service's own time and place SHALL be offered whatever the schedule feature says, because they describe an after-party or a seminar rather than the tournament's schedule. The feature's label SHALL say what it governs: that disciplines specify where and when they occur.

#### Scenario: Discipline schedule fields hidden
- **WHEN** the organizer opens `DISCIPLINES` on a tournament with the schedule feature off
- **THEN** no `when` or `where` field is offered on any discipline row

#### Scenario: Extra-item time and place always offered
- **WHEN** the organizer opens `EXTRA` on a tournament with the schedule feature off and extra services on
- **THEN** each item still offers its time and place, and an after-party already carrying them still presents them to fencers

#### Scenario: Stored discipline schedule still presented
- **WHEN** a tournament whose disciplines carry `when` and `where` turns the schedule feature off
- **THEN** the tournament information still presents those lines to fencers, and the fields are merely not editable in Setup

### Requirement: The team feature governs the team surfaces
WHEN the team disciplines feature is off, the console SHALL NOT offer the team kind in the discipline dialog, the roster bounds on a discipline row, the team composition deadline on `TIMELINE`, or the Teams phase. When it is on, all four SHALL be offered as fixed by `team-disciplines`.

A team discipline that exists while the feature is off SHALL continue to take teams, hold rosters, and count capacity in teams. The entering fencer's own Teams tab on the tournament detail page SHALL be unaffected by the feature, which governs the organizer's console alone.

#### Scenario: Team kind not offered
- **WHEN** the organizer opens the discipline dialog on a tournament with the team feature off
- **THEN** no kind control is offered and the discipline being added is individual

#### Scenario: Composition deadline hidden with the feature
- **WHEN** a tournament with a team discipline turns the team feature off
- **THEN** `TIMELINE` offers no composition deadline, and the stored deadline is retained

#### Scenario: Entrants keep their rosters
- **WHEN** a fencer who has entered a team opens the tournament detail page on a tournament whose team feature is off
- **THEN** the Teams tab is offered and the roster can be edited as usual

### Requirement: The extra services feature governs the EXTRA tab
WHEN the extra services feature is off, Setup SHALL NOT offer the `EXTRA` tab. When it is on, `EXTRA` SHALL be offered as fixed by `setup-navigation`.

Extra items stored while the feature is off SHALL be retained, SHALL still be offered on the registration form, and SHALL still be counted by the setup completeness rule, which SHALL continue to report a missing extra-item price. Because that item cannot be priced while the tab is hidden, the report SHALL name the extra services feature as what restores the editor.

#### Scenario: EXTRA absent
- **WHEN** the organizer opens Setup on a tournament with the extra services feature off
- **THEN** the tab bar offers no `EXTRA` tab

#### Scenario: Unpriced hidden item names the way back
- **WHEN** a tournament with the extra services feature off holds an extra item with no EUR price on a EUR-priced tournament
- **THEN** the `PUBLISH` tab reports the missing price and names the extra services feature as what makes it editable

### Requirement: Tournaments predating the features are derived from what they use
A tournament that existed before the features did SHALL have each feature turned on where the tournament shows evidence of using it, and off otherwise. The payments setting SHALL be derived by the same one-shot pass, though what it then governs is fixed by `payments`:

- **schedule** — any discipline has a non-empty `when` or `where`;
- **payments** — a bank account is recorded, or the payment mode is not immediate, or a bank transaction exists for the tournament;
- **team disciplines** — any discipline is of the team kind;
- **extra services** — any extra item exists.

The derivation SHALL be generous: any evidence SHALL turn the feature on, so that no organizer loses sight of something they configured. A tournament showing no evidence of any of them SHALL land with all of them off, which is a description rather than a named state. The derivation SHALL run once and SHALL NOT be a rule the system maintains thereafter.

#### Scenario: Configured tournament keeps everything visible
- **WHEN** a tournament with a bank account, a team discipline and two extra items is read after the features are introduced
- **THEN** payments, team disciplines and extra services are on, and its Setup offers exactly what it offered before

#### Scenario: Untouched draft lands with nothing enabled
- **WHEN** a draft with one individual discipline, no prices, no bank account and no extra items is read after the features are introduced
- **THEN** every feature is off, and the tournament is described by that rather than by a tier name

#### Scenario: Payments derived from a transaction alone
- **WHEN** a tournament with no recorded bank account has ingested bank transactions
- **THEN** the payments feature is on

