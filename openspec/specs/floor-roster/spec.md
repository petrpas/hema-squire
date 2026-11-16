# floor-roster Specification

## Purpose
TBD - created by archiving change add-floor-boundary. Update Purpose after archive.
## Requirements
### Requirement: The floor reads entrants from the office replay only
The floor SHALL learn about a tournament's entrants only through the floor roster. The
floor roster is built from the office's replayed fencer list, the same projection the
public roster reads (`public-entrants`), and from the team entries the export band reads
(`export-tables`). There SHALL be no second source. An external table reaches the floor
only after the office's import phase has taken it in and the replay states it as
`imp:` rows.

Building the floor roster SHALL write nothing: no rule, no registration, no row number,
no journal entry.

#### Scenario: An imported table reaches the floor through the office
- **WHEN** an organizer imports a table and its rows are issued registrations seated in Longsword Open
- **THEN** those fencers appear on the floor roster under the ids their rows hold in the replay

#### Scenario: Reading the floor roster changes nothing
- **WHEN** the floor roster is built for a tournament
- **THEN** the tournament's rules, registrations, row numbers and payment records are unchanged

### Requirement: The floor roster lists exactly the public roster's seated entrants
For every discipline the tournament offers, the floor roster SHALL list exactly the
entrants that `public-entrants` lists as seated on that discipline's roster. For an
individual discipline that means the fencers. For a team discipline it means the teams.
It SHALL hold in both modes: when Squire keeps the registrations and when the organizer
does.

Queued entrants SHALL NOT appear on the floor roster. That includes a queued fencer and
a waitlisted team.

Organizer corrections, deletions and merges, and the club and nationality HEMA Ratings
supplies, SHALL appear on the floor roster as they appear on the public roster. Both are
read from the same replay.

Every discipline the tournament offers SHALL be stated on the floor roster with its
slug, name and kind (individual or team), including a discipline nobody has entered.

The order in which entries are listed is not part of this contract. Seeding belongs to
the floor.

#### Scenario: Seated fencers are listed and queued fencers are not
- **WHEN** Longsword Open has twelve seated fencers and three queued
- **THEN** the floor roster lists the twelve as Longsword Open entries and none of the three

#### Scenario: A waitlisted team is not listed
- **WHEN** a team discipline has four seated teams and one waitlisted
- **THEN** the floor roster lists the four teams

#### Scenario: Both modes
- **WHEN** the same entrants are seated on a tournament whose registrations Squire keeps, and on one whose registrations the organizer keeps
- **THEN** in each tournament the floor roster's entrants per discipline equal the public roster's seated entrants

#### Scenario: A correction stands on the floor
- **WHEN** the organizer corrects a fencer's club in the console
- **THEN** the floor roster states the corrected club, as the public roster does

#### Scenario: A team of a removed registration is gone
- **WHEN** the row of the registration that entered a team has been taken out of the table
- **THEN** that team is on neither the public roster nor the floor roster

#### Scenario: An empty discipline is still stated
- **WHEN** nobody has entered Sabre Open
- **THEN** the floor roster states Sabre Open with no entries

### Requirement: Payment marks an entry and filters nothing
Every individual entry and every team entry SHALL state whether it is paid. An entry is
paid when the registration it was entered on is settled. A team is paid for once, on
its entering registration.

An unpaid seated entrant SHALL be listed and marked unpaid. Payment does not decide who
is on the floor. Check-in will decide that later.

The mark states the settled fact the organizer acts on. It is not the public roster's
Paid cell, which leaves the cell empty where nothing is yet owed or where the account
was deleted.

#### Scenario: An unpaid seated fencer is listed
- **WHEN** a seated fencer's registration is not settled
- **THEN** the floor roster lists their entry, marked unpaid

#### Scenario: A deleted account's settled entry is paid
- **WHEN** a seated fencer whose account was deleted had settled their registration
- **THEN** the floor roster marks their entry paid, though the public roster states nothing in that cell

### Requirement: An individual entry carries the replay's rating and rank
An individual entry SHALL state its person, its discipline's slug, whether it is paid,
and the rating and rank the replayed row states for that discipline. Where the row
states none, the entry states none.

#### Scenario: Rating per discipline
- **WHEN** a fencer is seated in Longsword Open and Sabre Open and the replay rates them 1650 in longsword and nothing in sabre
- **THEN** their Longsword Open entry carries 1650 and their Sabre Open entry carries no rating

### Requirement: A team entry names its team and its members
A team entry SHALL state a key, the discipline's slug, the team's name, the person keys
of its current members in roster order, and whether it is paid. The team key is the
team's own identity, `team:<team id>`, and never its name. One registration may enter
two teams with the same name.

Every member of a listed team SHALL appear among the roster's persons.

#### Scenario: Two teams of one name stay two teams
- **WHEN** one registration entered two teams both named "Ostrava" into one team discipline
- **THEN** the floor roster lists two team entries with distinct keys

### Requirement: A person is one human, decided by row and by confirmed HEMA Ratings identity
The floor roster SHALL list each person once. A person states a key, a name, a club, a
nationality and a HEMA Ratings identifier. Only persons holding at least one listed
entry are listed.

A fencer seated in several individual disciplines SHALL be one person with one entry
per discipline. The replay already states them as a single row.

A registration-backed row (`reg:`, `imp:` or `man:`) and team member rows (`mem:`), or
several member rows, SHALL be one person when every one of them carries the same HEMA
Ratings identifier with a confirmed match verdict. The person then:
- takes its key, name, club and nationality from its anchor row. The anchor is the
  registration-backed row, or the member row with the lowest member id when there is
  none.
- carries that identifier.

Where the floor roster cannot decide, the rows SHALL stay separate persons. That covers
a missing identifier, an identifier that is only proposed, and two registration-backed
rows sharing one confirmed identifier, which is a duplicate the office's dedup has to
resolve. No row is merged by name. Joining such rows is a later floor decision, not this
roster's.

#### Scenario: A fencer in two disciplines is one person
- **WHEN** a fencer is seated in Longsword Open and Sabre Open
- **THEN** the floor roster lists one person with two entries

#### Scenario: An individual who also fights on a team is one person
- **WHEN** a fencer seated in Longsword Open with confirmed HEMA Ratings id 123 is also a member of a seated team, and that member row carries 123 confirmed
- **THEN** the floor roster lists one person, keyed by the fencer's row id, who holds the individual entry and appears among the team's members

#### Scenario: A proposed identifier does not merge
- **WHEN** the member row's 123 is a proposal not yet confirmed
- **THEN** the fencer and the member are two persons

#### Scenario: Two registrations with one identifier are not merged
- **WHEN** two registration-backed rows both carry 123 confirmed
- **THEN** they are two persons, and no member row with 123 is merged into either

### Requirement: A person key is the replay's row id
A person's key SHALL be the replay row id of its anchor: `reg:<registration id>`,
`imp:<fingerprint>`, `man:<id>` or `mem:<member id>`. An `imp:` fingerprint is frozen
from the moment its row is issued a registration, and only rows standing for a live
registration are seated. So an `imp:` key on the floor roster does not change when the
organizer uploads a corrected table. The corrected row arrives as a new row; the old
one is not renamed. A key leaves the roster when its entry does, for example when a
cancellation removes the entry or the tournament's imported content is cleared.

#### Scenario: Re-uploading a table keeps the keys
- **WHEN** an organizer re-uploads the table the seated fencers were imported from
- **THEN** every seated imported fencer keeps their key on the floor roster

### Requirement: The organizer reads the floor roster from the console
`GET /api/tournaments/{slug}/floor/roster` SHALL return the floor roster: the
disciplines, the persons, the individual entries and the team entries. It SHALL be
behind the same gate as `GET /api/tournaments/{slug}/export/tables`. That means:
- an unknown slug answers 404 `tournament_not_found`;
- a caller who is not the tournament's owner or on its team answers 403;
- a draft tournament answers 409.

#### Scenario: An organizer reads the roster
- **WHEN** a member of the tournament's team requests the floor roster of a published tournament
- **THEN** the response lists its disciplines, persons and entries

#### Scenario: A stranger is refused
- **WHEN** a signed-in fencer with no console access requests the floor roster
- **THEN** the request is refused with 403

