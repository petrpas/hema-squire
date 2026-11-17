## ADDED Requirements

### Requirement: The floor roster names disciplines by id and states the tournament's day facts
Every discipline on the floor roster SHALL carry the discipline's stable id beside its
slug.

**Why the id.** A slug is editable until someone enters the discipline
(`discipline-identity`). Floor tables refer to a discipline by its id, so they survive a
slug edit made before anyone has entered.

**Day facts.** The floor roster SHALL state the tournament's date and its timezone.

#### Scenario: A slug edit keeps the floor's format
- **WHEN** the organizer saves a format for "LS" and then renames the slug to "LSO" before anyone has entered
- **THEN** the floor roster states the discipline under "LSO" with the same id, and its format is still found

### Requirement: A person is one human, decided by row and by the office's identity rule
The floor roster SHALL list each person once. A person states a key, a name, a club, a
nationality and a HEMA Ratings identifier. Only persons holding at least one listed
entry are listed.

A fencer seated in several individual disciplines SHALL be one person with one entry
per discipline. The replay already states them as a single row.

**The office's identity rule.** A team member row (`mem:`) SHALL be the same person as
a registration-backed row (`reg:`, `imp:` or `man:`) or as another member row by the
rule the public tournament list counts fencers with (`public-browsing`, owner decision
2026-11-16):
- where both rows state a HEMA Ratings identifier, they are one person exactly when the
  identifiers are equal. Two different identifiers are two people whatever their names;
- where either row states none, they are one person when their names are equal after
  folding case and diacritics and collapsing whitespace.

The floor SHALL apply the office's own implementation of that rule, so the two cannot
drift apart.

**What is never joined.**
- Two registration-backed rows. Each is its own registration, as the office counts
  them, and a duplicate is the office's dedup to resolve.
- Two member rows of one team. A team's lineup needs every member as a distinct person.

**The joined person** takes its key, name, club, nationality and HEMA Ratings
identifier from its anchor row, as the public roster states that row. The anchor is the
registration-backed row, or the member row with the lowest member id when there is
none. A member row that matches several persons joins the first, in that order, whose
every row it is the same person as. So no person joins two different identifiers.

#### Scenario: A fencer in two disciplines is one person
- **WHEN** a fencer is seated in Longsword Open and Sabre Open
- **THEN** the floor roster lists one person with two entries

#### Scenario: An individual who also fights on a team is one person
- **WHEN** a fencer seated in Longsword Open with HEMA Ratings id 123 is also a member of a seated team, and that member row carries 123
- **THEN** the floor roster lists one person, keyed by the fencer's row id, who holds the individual entry and appears among the team's members

#### Scenario: A member without an identifier joins by name
- **WHEN** the individual "Jan Novák" carries id 123 and a team's member row "jan  novak" carries no identifier
- **THEN** the floor roster lists one person, keyed by the individual's row id

#### Scenario: Two identifiers are two people
- **WHEN** the individual "Jan Novák" carries 123 and a member row "Jan Novák" carries 456
- **THEN** they are two persons

#### Scenario: Two registrations with one identifier are not merged
- **WHEN** two registration-backed rows both carry 123
- **THEN** they are two persons, and a member row with 123 joins the first of them

#### Scenario: Namesakes on one team stay two
- **WHEN** one team lists two members both named "Petr Svoboda" without identifiers
- **THEN** the floor roster lists them as two persons

## REMOVED Requirements

### Requirement: A person is one human, decided by row and by confirmed HEMA Ratings identity
**Reason**: The owner chose the office's identity rule on 2026-11-16: a member joins by
equal identifier, or by folded name where either has none. The confirmed-identifier-only
join, and its "no row is merged by name", no longer hold.
**Migration**: Replaced by "A person is one human, decided by row and by the office's
identity rule". Person keys of registration-backed rows are unchanged.
