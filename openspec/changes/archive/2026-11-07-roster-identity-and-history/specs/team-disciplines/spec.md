## ADDED Requirements

### Requirement: A roster member keeps its identity across saves

A roster member SHALL have an identity of its own that survives every save of the
roster it belongs to. Saving a roster SHALL NOT discard and recreate its members.

A save SHALL state the roster it wants and SHALL be applied as a difference
against the roster stored: a member stated with its identity SHALL be updated in
place, a member stated without one SHALL be added, and a member the save does not
state SHALL be removed. A member whose fields are unchanged SHALL be left
untouched, and its identity SHALL be the same identity afterwards.

A member's identity SHALL NOT be its position. The order SHALL be rewritten from
the order the save states, and reordering a roster SHALL change no member's
identity — the list is ordered and without roles, as **The roster is an ordered
list without roles** fixes, so position carries no meaning that could identify
anybody.

Two members of one roster MAY be identical in every stored field; their
identities SHALL still be distinct, and a save SHALL apply to the one it names.

#### Scenario: A correction keeps the member
- **WHEN** the entering fencer corrects one member's nationality and saves
- **THEN** that member is the same member afterwards, and the other members are untouched

#### Scenario: Reordering identifies nobody differently
- **WHEN** a roster of four is saved in a different order with no other change
- **THEN** the four are the same four members, in the new order

#### Scenario: Two members alike are still two members
- **WHEN** a roster holds two members with the same name, club, nationality and no identifier, and a save renames one of them
- **THEN** only the named one is renamed

#### Scenario: A member added and a member removed in one save
- **WHEN** a save states three of a roster's four members and one member not stored before
- **THEN** the three keep their identities, the fourth is removed, and the new member is added

### Requirement: A removed roster member is retained

Removing a member SHALL mark it removed rather than erase it. A removed member
SHALL be excluded from everything that states a roster or counts one: the
entrant's editor, the organizer's teams view, the public entrants roster, the
member count against the discipline's minimum and maximum, the below-minimum
mark, and the composition reminder. It SHALL remain retrievable as part of the
roster's history, and restoring it SHALL be possible while the roster has room
for it.

Restoring a removed member SHALL return the same member, not a copy: whatever
the tournament has decided about that person SHALL still be about them.

The tournament's backup document SHALL carry removed members, so that a restore
does not quietly erase a roster's history.

#### Scenario: A removed member counts for nothing
- **WHEN** a team of four removes one member on a discipline requiring three
- **THEN** every list and count states three members, and the team is not below minimum

#### Scenario: A removal is not an erasure
- **WHEN** the roster's history is read after that removal
- **THEN** the removed member is there, named, with the moment it was removed

#### Scenario: Restored rather than retyped
- **WHEN** the organizer restores that member at the venue
- **THEN** the roster states four members again and the restored member is the member that was removed

#### Scenario: A full roster has no room to restore into
- **WHEN** a restore would exceed the discipline's maximum roster size
- **THEN** it is refused, naming the maximum

### Requirement: Every roster change is recorded in one log

Every change to a roster SHALL be recorded: a member added, removed, restored, or
any stored field of a member changed. One log SHALL hold the entering fencer's
changes and the organizer's together, so that a roster's story is whole rather
than half of one.

Each entry SHALL state what changed — the member, and for a field change the
field with its value before and after — who changed it, and when. Where the
organizer changed it, the entry SHALL name the organizer; where the entering
fencer did, it SHALL name them. An entry SHALL state whether the change was made
after the tournament's composition deadline, since a change made afterwards is
read differently from one made before it.

Reordering a roster SHALL NOT be recorded: order carries no meaning, so a
reorder changes nothing anybody could dispute.

The log SHALL be visible to the organizer beside the roster it belongs to. It
SHALL be append-only: no entry SHALL be edited or deleted while the team exists.

#### Scenario: The entrant's own edit is in the log
- **WHEN** the entering fencer replaces a member the evening before the tournament
- **THEN** the log holds the removal and the addition, naming them as the actor and the moment

#### Scenario: The organizer's edit names the organizer
- **WHEN** the organizer swaps a member at the venue
- **THEN** the log holds that change, naming the organizer, and states that it was made after the composition deadline

#### Scenario: A field change states before and after
- **WHEN** a member's club is corrected
- **THEN** the log holds one entry naming the member, the club field, and both values

#### Scenario: A reorder is not a change
- **WHEN** a roster is saved in a different order and nothing else differs
- **THEN** the log gains no entry

## MODIFIED Requirements

### Requirement: Roster editing changes no money
Editing a roster — adding, removing, restoring, renaming, rebinding, or reordering
members — SHALL NOT recompute any total, SHALL NOT issue or reissue a VS, SHALL
NOT change any amount owed or credited, SHALL NOT alter refund state, SHALL NOT
send a confirmation email, and SHALL NOT consume or check capacity. This holds
whoever edits it: a team's fee is per team and never multiplied by its roster, so
there is no edit to a roster that money could follow.

Roster editing SHALL NOT be gated by the tournament's amendment window, and SHALL
NOT be gated by the composition deadline. It SHALL be available to the entering
fencer from the moment the team is entered until the tournament date, on a
reserved or a paid registration alike, and SHALL be refused on a cancelled or
expired registration. It SHALL be available to the organizer on the same terms,
as **Organizer's teams view** fixes.

The organizer's edit SHALL send nothing to the entering fencer. A roster edit
moves no money, and a letter for each corrected row would cost more than the
error it reports; the change SHALL be visible to the entering fencer on the
tournament's detail page, where their own roster already is.

#### Scenario: Total unmoved by a roster edit
- **WHEN** the entering fencer replaces two members of a team on a paid registration
- **THEN** the registration's totals, amounts credited, outstanding balance, and refund state are all unchanged, and no email is sent

#### Scenario: Roster editable after amendments close
- **WHEN** the entering fencer edits a roster after the tournament's amendment window has closed
- **THEN** the edit is accepted

#### Scenario: Roster editing refused on a dead registration
- **WHEN** the entering fencer attempts to edit a roster on a registration that has expired or been cancelled
- **THEN** the edit is rejected

#### Scenario: The organizer's edit after the deadline moves nothing and says nothing
- **WHEN** the organizer swaps a member on a paid registration after the composition deadline
- **THEN** the edit is accepted, the registration's money is unchanged, and no mail is sent

### Requirement: Organizer's teams view
The console SHALL present, per team discipline, the teams entered into it: the team name, the entering fencer, the roster in order with each member's name and — where bound — HEMA Ratings identifier, club, and nationality, the member count against the discipline's minimum and maximum, and the team's waitlist position where it is waitlisted. Teams marked below minimum after the composition deadline SHALL be distinguished.

The view SHALL be offered only while the tournament's team disciplines feature is on, as fixed by `tournament-features`. An organizer who has turned the feature off SHALL see no Teams phase; the teams, rosters and waitlist positions it would have shown SHALL be retained untouched and SHALL be shown again when the feature is turned back on. The entering fencer's own roster editor on the tournament detail page SHALL be unaffected by the feature, which governs the organizer's console alone.

**The view SHALL let the organizer edit a roster**: add a member, remove one, restore a removed one, and correct a member's name, HEMA Ratings identifier, club or nationality. A team arrives at the tournament and the fencer who entered it cannot always reach their own editor; the organizer acting for them is the remedy, and it is a safe one — a roster edit moves no money, as **Roster editing changes no money** fixes. Every such edit SHALL be recorded as **Every roster change is recorded in one log** fixes, and the log SHALL be shown beside the roster.

The view SHALL offer no other action on a team. Team cancellation SHALL NOT be offered here. Admission from the waitlist and return to it are the Queue phase's (`seating-queue`), and the view SHALL say so where it shows a waitlisted team. The organizer acts through the controls that exist elsewhere in the console.

#### Scenario: Teams listed per discipline
- **WHEN** an organizer opens the teams view for a team discipline holding six teams
- **THEN** each team is listed with its name, entering fencer, ordered roster, and member count against the minimum and maximum

#### Scenario: A bound member states its identifier here too
- **WHEN** a listed roster holds a member bound to a HEMA Ratings profile
- **THEN** the view states that identifier, as the public entrants roster already does

#### Scenario: Short teams distinguished after the deadline
- **WHEN** the composition deadline has passed and two of the listed teams are below minimum
- **THEN** those two are distinguished from the rest

#### Scenario: Unbound members shown plainly
- **WHEN** a listed roster contains members with no HEMA Ratings identifier
- **THEN** those members are shown by name with no identifier, club, or nationality, and are not marked as a problem

#### Scenario: The organizer swaps a member at the venue
- **WHEN** the organizer removes a member of a listed team and adds another in their place
- **THEN** the roster states the new member, the log holds both changes naming the organizer, and the entering fencer's registration is unchanged

#### Scenario: No actions offered
- **WHEN** an organizer views a waitlisted team or a team below minimum
- **THEN** the view offers no control to admit or cancel it, and a waitlisted team's row states that admission is on the Queue phase

#### Scenario: No teams view while the feature is off
- **WHEN** an organizer opens the console of a tournament whose team disciplines feature is off
- **THEN** no Teams phase is offered

#### Scenario: Teams reappear with the feature
- **WHEN** that organizer turns the team disciplines feature back on
- **THEN** the Teams phase is offered again, listing the same teams and rosters as before

#### Scenario: Entrants keep their roster editor
- **WHEN** a fencer who entered a team opens the tournament detail page while the team feature is off
- **THEN** the team is listed and its roster editor is offered as usual

## RENAMED Requirements

- FROM: `### Requirement: Organizer's read-only teams view`
- TO: `### Requirement: Organizer's teams view`
