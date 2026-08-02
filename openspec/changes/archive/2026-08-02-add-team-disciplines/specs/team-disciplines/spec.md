## ADDED Requirements

### Requirement: A discipline is individual or team
Every discipline SHALL carry a kind: individual or team. An individual discipline is
entered by one fencer and behaves exactly as disciplines behave today. A team discipline
SHALL additionally carry a minimum and a maximum roster size, both whole numbers with
minimum at least 1 and maximum not below minimum; the customary values are 3 and 4.

For a team discipline, the discipline's capacity SHALL count **teams**, not fencers, and
the discipline's configured fee SHALL be the fee for **one team**, charged once per team
entered, never multiplied by roster size. Every reading of capacity or fee — pricing, the
price preview, availability, the registration form, the confirmation email, the console,
the exports — SHALL interpret the number according to the discipline's kind.

A discipline's kind SHALL NOT change once any registration references it.

#### Scenario: Team discipline configured
- **WHEN** an organizer configures a team discipline with capacity 8, minimum 3, maximum 4, and fee 3000
- **THEN** the discipline admits 8 teams, each charged 3000 once, with rosters of 3 to 4 members

#### Scenario: Roster bounds validated
- **WHEN** an organizer saves a team discipline with a maximum below its minimum, or a minimum below 1
- **THEN** the save is rejected with a validation error naming the field

#### Scenario: Existing disciplines are individual
- **WHEN** a tournament configured before team disciplines existed is read
- **THEN** every one of its disciplines is individual and its capacity and fee mean what they meant before

#### Scenario: Kind frozen once entered
- **WHEN** an organizer attempts to change the kind of a discipline that a registration already references
- **THEN** the change is rejected

### Requirement: Team disciplines carry no HR rating category
A team discipline SHALL be excluded from the tournament's HR category map. The map SHALL
NOT offer, store, or require an entry for a team discipline, and no HR path SHALL derive
a rating category from one.

#### Scenario: Team discipline absent from the map
- **WHEN** a tournament offering an individual and a team discipline exposes its HR category map
- **THEN** only the individual discipline is present

### Requirement: A team is entered by one registered fencer
A team SHALL be entered by exactly one fencer, through that fencer's own registration for
the tournament. The team SHALL carry a name, the team discipline it enters, and a roster.

The team's fee SHALL be charged to the entering fencer's registration: it enters that
registration's total in every configured currency, is owed against that registration's
VS, appears in its confirmation email and payment QR codes, and lives under its
reservation expiry. No separate registration, VS, payment window, or payment instruction
SHALL be created for a team.

A registration MAY carry more than one team, in the same team discipline or in different
ones. A registration MAY consist of teams alone, with no individual discipline entries
and no extra services; such a registration is valid and is priced, confirmed, paid, and
expired like any other.

A team name SHALL be required and SHALL NOT be required to be unique. Two teams in one
discipline MAY carry the same name, whether entered by the same fencer or by different
ones, and the system SHALL NOT reject, warn about, or disambiguate the collision. The
organizer sees both teams with their entering fencers and rosters in the teams view and
resolves it by talking to them.

Entering, renaming, or removing a team is an amendment of the entering fencer's
registration and SHALL be validated and gated exactly as any other amendment is.

#### Scenario: Team fee on the entrant's registration
- **WHEN** a fencer registers for one individual discipline at 900 and enters one team at 3000
- **THEN** their registration totals 3900 against a single VS, with one confirmation email and one payment QR code per configured currency

#### Scenario: Two teams entered by one fencer
- **WHEN** a fencer enters two teams into the same team discipline
- **THEN** both teams exist independently with their own names and rosters, and the discipline's fee is charged twice on that registration

#### Scenario: Duplicate team names accepted
- **WHEN** two fencers each enter a team named "Wolves" into the same team discipline
- **THEN** both entries are accepted unchanged, with no warning and no renaming, and the organizer's teams view lists both with their entering fencers and rosters

#### Scenario: Registration consisting only of a team
- **WHEN** a fencer registers entering one team and selecting no individual discipline and no extra service
- **THEN** the registration is accepted, totals the team fee, and receives a VS and confirmation like any other registration

#### Scenario: Removing a team is an amendment
- **WHEN** a fencer removes a team from a reserved registration
- **THEN** the total is recomputed without that team's fee, the VS and expiry instant are unchanged, and an updated confirmation is sent

#### Scenario: Team entry refused after the amendment window
- **WHEN** a fencer attempts to enter a team after the tournament's amendment window has closed
- **THEN** the attempt is rejected with the closed-window reason

### Requirement: Team capacity and the team waitlist
A team discipline's capacity SHALL be consumed by teams on confirmed registrations and by
teams on reservations within their validity window. When a team discipline is full,
further teams SHALL be recorded as waitlisted, in entry order.

A waitlisted team SHALL NOT be charged: its fee SHALL be excluded from the entering
fencer's total, exactly as an individual substitute placement is excluded. A team's
waitlisted state SHALL be shown to the entering fencer and to the organizer.

Admitting a waitlisted team into a freed slot is not part of this capability.

#### Scenario: Team entered into a full discipline
- **WHEN** a fencer enters a team into a team discipline that already holds teams to capacity
- **THEN** the team is recorded as waitlisted in entry order, its fee is not charged, and the fencer is told the team is waitlisted

#### Scenario: Waitlisted team excluded from the total
- **WHEN** a registration carries one placed team at 3000 and one waitlisted team at 3000
- **THEN** the registration totals 3000

#### Scenario: Team discipline fills between form load and submission
- **WHEN** a team discipline shown as open has filled by the time the fencer submits
- **THEN** the submission is accepted with that team waitlisted, and the fencer is told which teams were waitlisted

### Requirement: A roster member is a named person, never an account
A team's roster SHALL consist of members, each carrying a name and, when bound to a HEMA
Ratings profile, that profile's identifier together with the club and nationality it
carries. A member SHALL NOT be a fencer account: no member SHALL have an email, a
password, a login, a registration, a payment, or an entry in any account list, and no
member SHALL be created as or converted into a fencer account by this capability.

A member MAY be unbound — a name with no HEMA Ratings identifier. An unbound member is a
valid, complete member. No validation, status, count, warning, or export SHALL treat an
unbound member as missing, incomplete, or erroneous.

Members SHALL be named through the existing nationality-filtered HEMA Ratings similarity
search. Selecting a search result SHALL bind the member to that profile and take its
canonical name, club, and nationality; typing a name without selecting a result SHALL
store that name unbound.

Member identity SHALL be local to its roster. The same person named on two rosters
produces two independent members, and a member is never linked to a registration or a
fencer account, even when a HEMA Ratings identifier would match one.

#### Scenario: Member bound through the HR search
- **WHEN** the entering fencer types a partial name and selects a search result
- **THEN** the member is stored with that profile's identifier, canonical name, club, and nationality

#### Scenario: Member HR does not know
- **WHEN** the entering fencer types a name and the search offers no matching profile
- **THEN** the member is stored with that name and no identifier, and is treated as a complete member everywhere

#### Scenario: Member is not an account
- **WHEN** a roster names a person who has no Squire account
- **THEN** no account, no invitation, no registration, and no payment obligation is created for that person

#### Scenario: Same person on two rosters
- **WHEN** two teams name the same HEMA Ratings profile
- **THEN** both rosters carry their own member row and neither team is affected by the other

### Requirement: The roster is an ordered list without roles
A roster SHALL be an ordered list of members. It SHALL NOT record which member is the
team's captain, which members fence, or which member is the reserve: those are decided at
the tournament and are not modelled.

The roster SHALL be editable to at most the discipline's maximum roster size. It MAY hold
fewer members than the discipline's minimum, including none, at any time.

When the roster editor is first opened for a newly entered team, the entering fencer
SHALL be prefilled as the first member, bound to their own HEMA Ratings profile when they
have one. The prefill is a convenience only: that member SHALL be editable and removable
exactly like any other, and no stored field SHALL mark it as the entrant's.

#### Scenario: Order preserved
- **WHEN** a roster of four members is saved and read back
- **THEN** the members are returned in the order they were entered

#### Scenario: Maximum enforced
- **WHEN** the entering fencer adds a fifth member to a team whose discipline allows four
- **THEN** the addition is rejected with a validation error naming the maximum

#### Scenario: Roster below the minimum accepted
- **WHEN** the entering fencer saves a roster of one member for a discipline requiring three
- **THEN** the roster is saved, and the team is neither rejected nor flagged before the composition deadline

#### Scenario: Entrant prefilled and removable
- **WHEN** a fencer enters a team and opens its roster for the first time
- **THEN** they appear as the first member, and removing or renaming that member is accepted

### Requirement: Roster editing changes no money
Editing a roster — adding, removing, renaming, rebinding, or reordering members — SHALL
NOT recompute any total, SHALL NOT issue or reissue a VS, SHALL NOT change any amount
owed or credited, SHALL NOT alter refund state, SHALL NOT send a confirmation email, and
SHALL NOT consume or check capacity.

Roster editing SHALL NOT be gated by the tournament's amendment window. It SHALL be
available to the entering fencer from the moment the team is entered until the tournament
date, on a reserved or a paid registration alike, and SHALL be refused on a cancelled or
expired registration.

#### Scenario: Total unmoved by a roster edit
- **WHEN** the entering fencer replaces two members of a team on a paid registration
- **THEN** the registration's totals, amounts credited, outstanding balance, and refund state are all unchanged, and no email is sent

#### Scenario: Roster editable after amendments close
- **WHEN** the entering fencer edits a roster after the tournament's amendment window has closed
- **THEN** the edit is accepted

#### Scenario: Roster editing refused on a dead registration
- **WHEN** the entering fencer attempts to edit a roster on a registration that has expired or been cancelled
- **THEN** the edit is rejected

### Requirement: Team composition deadline checks rather than enforces
A tournament SHALL carry an optional team composition deadline: the date by which rosters
are expected to reach their disciplines' minimum sizes. It SHALL be configurable only as
a date, SHALL be meaningful only when the tournament offers at least one team discipline,
and SHALL be presented to the entering fencer alongside their teams.

The deadline SHALL NOT enforce anything. Passing it SHALL NOT lock a roster, SHALL NOT
cancel or waitlist a team, SHALL NOT free capacity, SHALL NOT change a total or a refund
state, and SHALL NOT block any action. Rosters remain editable after it under the same
rules as before it.

Its sole effect SHALL be to mark, from the day after it passes, every team whose roster is
below its discipline's minimum, for the organizer to act on through the controls that
already exist.

#### Scenario: Deadline passes with a short roster
- **WHEN** the composition deadline passes and a team holds two members against a minimum of three
- **THEN** the team is marked as below minimum for the organizer, remains entered, keeps its capacity slot, and its registration's total and payment state are unchanged

#### Scenario: Roster completed after the deadline
- **WHEN** the entering fencer adds the missing member after the deadline has passed
- **THEN** the edit is accepted and the team is no longer marked as below minimum

#### Scenario: Member swapped the night before
- **WHEN** the entering fencer replaces a member the day before the tournament
- **THEN** the edit is accepted

#### Scenario: No deadline configured
- **WHEN** a tournament offering a team discipline has no composition deadline set
- **THEN** no team is ever marked as below minimum and nothing is reminded

### Requirement: Composition reminder to the entering fencer
When a tournament has a composition deadline, the system SHALL remind the entering fencer,
once, ahead of that deadline, of every team of theirs whose roster is still below its
discipline's minimum. The reminder SHALL name the teams, state how many members each
still needs, state the deadline, and link to the roster editor.

The reminder SHALL be sent at most once per team and SHALL record when it was sent, so
that a repeated run does not resend it. No reminder SHALL be sent for a team already at
or above its minimum, for a cancelled or expired registration, or for a waitlisted team.

#### Scenario: Reminder for a short roster
- **WHEN** the reminder runs ahead of the deadline for a team holding one member against a minimum of three
- **THEN** the entering fencer receives one localized reminder naming the team, the shortfall, and the deadline

#### Scenario: Reminder not repeated
- **WHEN** the reminder job runs again while the roster is still short
- **THEN** no second reminder is sent for that team

#### Scenario: Complete roster not reminded
- **WHEN** the reminder runs for a team already at its minimum
- **THEN** no reminder is sent

### Requirement: Organizer's read-only teams view
The console SHALL present, per team discipline, the teams entered into it: the team name,
the entering fencer, the roster in order with each member's name and — where bound — HEMA
Ratings identifier, club, and nationality, the member count against the discipline's
minimum and maximum, and the team's waitlist position where it is waitlisted. Teams
marked below minimum after the composition deadline SHALL be distinguished.

The view SHALL be read-only. It SHALL offer no action on a team or a roster: no
admission from the waitlist, no roster editing on the entrant's behalf, and no team
cancellation. The organizer acts through the controls that already exist elsewhere in
the console.

#### Scenario: Teams listed per discipline
- **WHEN** an organizer opens the teams view for a team discipline holding six teams
- **THEN** each team is listed with its name, entering fencer, ordered roster, and member count against the minimum and maximum

#### Scenario: Short teams distinguished after the deadline
- **WHEN** the composition deadline has passed and two of the listed teams are below minimum
- **THEN** those two are distinguished from the rest

#### Scenario: Unbound members shown plainly
- **WHEN** a listed roster contains members with no HEMA Ratings identifier
- **THEN** those members are shown by name with no identifier, club, or nationality, and are not marked as a problem

#### Scenario: No actions offered
- **WHEN** an organizer views a waitlisted team or a team below minimum
- **THEN** the view offers no control to admit, edit, or cancel it
