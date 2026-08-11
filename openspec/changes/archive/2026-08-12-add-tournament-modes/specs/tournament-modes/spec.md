## ADDED Requirements

### Requirement: A tournament carries four feature flags
Each tournament SHALL carry four independent boolean features — **schedule**, **payments**, **team disciplines**, **extra services** — stored with the tournament and governing which of Squire's advanced surfaces its console offers. They are a property of the tournament, not of the account reading it: every member of a tournament's console team SHALL see the same features enabled.

A tournament created after this change SHALL have all four off. The features SHALL be changeable at any point in the tournament's life, including after publication, by any account with console access to it, under the same authorization as any other Setup write.

No feature SHALL be derived, inferred, or re-derived at runtime from the tournament's contents. Adding a team discipline SHALL NOT turn the team feature on; removing the last extra item SHALL NOT turn extra services off. The features record what the organizer asked to see.

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

### Requirement: Easy mode is the absence of every feature
**Easy mode** SHALL be the name for a tournament with none of the four features enabled, and **advanced mode** the name for one with at least one. There SHALL be no separately stored mode value, so the name a tournament is given and the sections its console offers SHALL never disagree.

Choosing easy mode SHALL turn all four features off. Choosing advanced mode SHALL offer the four features as independent checkboxes and SHALL require at least one to be chosen; confirming advanced mode with none chosen SHALL leave the tournament in easy mode and SHALL name it as such.

#### Scenario: Easy mode named from the features
- **WHEN** an organizer turns off the last enabled feature
- **THEN** the tournament is described as being in easy mode, with no separate value to change

#### Scenario: Advanced with one feature
- **WHEN** an organizer enables payments alone
- **THEN** the tournament is described as advanced with payments, and the other three features stay off

#### Scenario: Advanced with nothing chosen
- **WHEN** an organizer selects advanced mode but ticks none of the four features
- **THEN** the dialog does not accept the choice as advanced, and the tournament remains in easy mode

### Requirement: The mode is chosen in a dialog of its own at creation
Creating a tournament SHALL open the Tournament Mode dialog once the tournament exists, after the dialog that takes its display name, date and slug. The mode dialog SHALL offer easy mode and advanced mode as a radio choice with easy mode preselected, and under advanced mode the four features as checkboxes, each carrying a help hint stating which tournaments it is for:

- **Tournament schedule** — for larger tournaments with several disciplines on different days and in different places.
- **Payments** — for organizers who want Squire to handle payment processing.
- **Team disciplines** — for tournaments including one or more team disciplines.
- **Extra services** — after-party, seminars, weapon lending, merchandise.

The dialog SHALL be dismissible. Dismissing it SHALL leave the created tournament in easy mode and SHALL open the console's Setup phase exactly as confirming it does; a tournament SHALL NOT be left uncreated, half-created, or unreachable by a mode that was never chosen.

#### Scenario: Mode chosen at creation
- **WHEN** an organizer creates a tournament, selects advanced mode and ticks payments and team disciplines
- **THEN** those two features are enabled, the other two are not, and the console opens on Setup

#### Scenario: Dialog dismissed
- **WHEN** an organizer creates a tournament and closes the mode dialog without choosing
- **THEN** the tournament exists in easy mode and the console opens on Setup

#### Scenario: Creation failure never reaches the mode dialog
- **WHEN** the creation dialog is rejected because the slug is taken
- **THEN** the mode dialog does not open and the organizer stays in the creation dialog with their input intact

#### Scenario: Features explain themselves
- **WHEN** the organizer reaches the help marker beside any of the four features
- **THEN** a hint appears stating which tournaments that feature is for

### Requirement: The mode is stated and changed on OTHER
The Setup phase's `OTHER` tab SHALL carry a section stating the tournament's current mode in words — easy mode, or advanced mode naming the enabled features — with a control that reopens the Tournament Mode dialog on the tournament's current features. Confirming the dialog SHALL apply the features immediately and SHALL refresh the tab bar and the sections around it.

The section SHALL follow the `OTHER` tab's rule that its actions carry their own controls: it SHALL NOT be written by a save control, and `OTHER` SHALL continue to carry none.

#### Scenario: Mode stated on OTHER
- **WHEN** the organizer opens `OTHER` on a tournament with payments and extra services enabled
- **THEN** the section states that the tournament is in advanced mode with payments and extra services, and offers a control to change it

#### Scenario: Easy mode stated on OTHER
- **WHEN** the organizer opens `OTHER` on a tournament with no feature enabled
- **THEN** the section states that the tournament is in easy mode

#### Scenario: Change applies at once
- **WHEN** the organizer enables extra services through the dialog on `OTHER`
- **THEN** the `EXTRA` tab appears without a save and without leaving Setup

### Requirement: Disabling a feature hides its settings without changing them
Turning a feature off SHALL hide the settings it governs and SHALL NOT write, clear, reset, or delete any of them. Every stored value the hidden settings hold — a team discipline's roster bounds, an extra item's price, a bank account, a deposit, a discipline's `when` and `where` — SHALL be retained exactly as it was. Turning the feature back on SHALL show those settings holding the values they held before, with nothing to restore and nothing to re-enter.

A hidden setting SHALL remain in force for every check that reads the tournament's contents rather than its features. In particular, a team discipline hidden by the team feature SHALL still be checked for valid roster bounds by the setup completeness rule, because the discipline still exists and is still offered to fencers.

#### Scenario: Values survive being hidden
- **WHEN** the organizer turns off extra services on a tournament with three priced extra items, then turns extra services back on
- **THEN** the three items are present with their prices, options and schedule fields unchanged

#### Scenario: Disabling writes nothing
- **WHEN** the organizer turns off payments on a tournament with a recorded bank account, a deposit and a five-day payment window
- **THEN** all three values are retained unchanged and no other tournament field is written

#### Scenario: Hidden data still checked for completeness
- **WHEN** a tournament with the team feature off has a team discipline with no roster bounds
- **THEN** the `PUBLISH` tab still reports those roster bounds as blocking publication

### Requirement: Turning off a feature the tournament uses is warned and confirmed
WHEN the organizer turns off a feature the tournament already uses, the dialog SHALL state what will be hidden, counting the affected items — team disciplines, extra items, disciplines carrying schedule fields — and naming the payment settings recorded, and SHALL require confirmation before applying the change. Declining SHALL leave every feature as it was.

Turning a feature **on** SHALL NOT be warned or confirmed.

Except for payments, hiding a feature SHALL NOT change anything a fencer experiences. A hidden extra item SHALL still be offered on the registration form and still be sold; a hidden team discipline SHALL still take teams; a hidden `when` SHALL still be shown wherever the tournament is described. The warning SHALL say so, so that the organizer is hiding settings they are finished with rather than withdrawing products they are selling. What payments does when it is turned off is fixed by its own requirement.

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

### Requirement: The payments feature suspends the payment machinery
The payments feature governs whether Squire handles payment processing for a tournament, not merely whether its settings are shown. WHEN it is off, the tournament SHALL:

- require no bank account to be published, whatever it charges, as fixed by `tournament-admin`;
- offer none of the payment and reservation parameters in Setup — the payment mode, the deposit, the payment window, the reminder day, the seating deadline, the bank account, the unpaid-list treatment and the variable-symbol statement;
- request no money at registration: no payment window opens, no due date is set, and no variable symbol is put to work;
- send no payment instructions, QR code, reminder, expiry notice or surcharge mail;
- expire no reservation for non-payment;
- offer no Payments phase in the console, and reconcile no bank transactions.

Prices SHALL be unaffected. Disciplines and extra items SHALL keep their prices in the tournament's currency, discounts SHALL still apply, and the total SHALL still be computed and presented to the fencer — as a statement of what the tournament costs, settled outside Squire, rather than as a demand with a deadline.

Turning payments off SHALL retain every stored payment value: the bank account, the payment mode, the deposit, the window, credited payments, ingested transactions, payment events and issued variable symbols. Turning payments back on SHALL resume with all of them present. Registrations taken while payments were off carry no due date, so SHALL NOT expire retroactively when payments are turned on; they SHALL remain reserved until the organizer acts on them.

#### Scenario: Priced tournament publishes without an account
- **WHEN** an organizer publishes a tournament with priced disciplines, payments off and no bank account recorded
- **THEN** publication succeeds and no missing bank account is reported

#### Scenario: Registration takes no money
- **WHEN** a fencer registers for a payments-off tournament with a total of 1200 Kč
- **THEN** the registration is seated, no payment window opens, no due date is set, and the confirmation email states the total with no account block and no QR code

#### Scenario: Nothing expires
- **WHEN** the scheduler runs against a payments-off tournament holding registrations older than any payment window
- **THEN** no reservation expires, no reminder is sent, and no expiry notice is sent

#### Scenario: No payments phase
- **WHEN** the organizer opens the console for a payments-off tournament
- **THEN** no Payments phase is offered and no transaction can be reconciled against the tournament

#### Scenario: Prices survive
- **WHEN** an organizer turns payments off on a tournament pricing in CZK with two discounts
- **THEN** the discipline and extra-item prices, the currency and both discounts are unchanged, and the registration form still shows the computed total

#### Scenario: Payments turned back on
- **WHEN** an organizer turns payments back on
- **THEN** the bank account, payment mode, deposit and payment window hold the values they held before, and the Payments phase is offered again

#### Scenario: Registrations taken while payments were off do not expire
- **WHEN** a tournament that took registrations with payments off turns payments on
- **THEN** those registrations remain reserved, none expires on account of a window that never opened, and the organizer decides what to do with them

### Requirement: Tournaments predating the mode are derived from what they use
A tournament that existed before the features did SHALL have each feature turned on where the tournament shows evidence of using it, and off otherwise:

- **schedule** — any discipline has a non-empty `when` or `where`;
- **payments** — a bank account is recorded, or the payment mode is not immediate, or a bank transaction exists for the tournament;
- **team disciplines** — any discipline is of the team kind;
- **extra services** — any extra item exists.

The derivation SHALL be generous: any evidence SHALL turn the feature on, so that no organizer loses sight of something they configured. A tournament showing no evidence of any of the four SHALL land in easy mode. The derivation SHALL run once and SHALL NOT be a rule the system maintains thereafter.

#### Scenario: Configured tournament keeps everything visible
- **WHEN** a tournament with a bank account, a team discipline and two extra items is read after the features are introduced
- **THEN** payments, team disciplines and extra services are on, and its Setup offers exactly what it offered before

#### Scenario: Untouched draft lands in easy mode
- **WHEN** a draft with one individual discipline, no prices, no bank account and no extra items is read after the features are introduced
- **THEN** all four features are off and it is described as being in easy mode

#### Scenario: Payments derived from a transaction alone
- **WHEN** a tournament with no recorded bank account has ingested bank transactions
- **THEN** the payments feature is on
