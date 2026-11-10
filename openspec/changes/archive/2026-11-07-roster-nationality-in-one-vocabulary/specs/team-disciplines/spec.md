## MODIFIED Requirements

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

A member's nationality SHALL be held as the two-letter ISO country code of the country
it names, whatever vocabulary it was given in — the reading the Matching evidence
register and every identity column after it use (`etl-console`), so that one column does
not read `CZ` on the fencer table and `Czech Republic` on a roster beside it. Where no
country can be identified from the spelling, that spelling SHALL stand as given: a
spelling Squire cannot read is still what it was given. The rule SHALL hold wherever a
member is written, so that every screen listing members states one vocabulary without
converting anything itself.

The canonical JSON export (`data-export`) SHALL state the member's nationality as the
record holds it, as it states every other stored field: it is a dump reporting rows, not
a display. A restore SHALL apply this reading to what the document carries, as it already
parses a classification out of an older document's discipline code — a document written
before this reading restores into rows that obey it, rather than into the only rows in
the database that do not.

Member identity SHALL be local to its roster. The same person named on two rosters
produces two independent members, and a member is never linked to a registration or a
fencer account, even when a HEMA Ratings identifier would match one.

#### Scenario: Member bound through the HR search
- **WHEN** the entering fencer types a partial name and selects a search result
- **THEN** the member is stored with that profile's identifier, canonical name, club, and nationality

#### Scenario: One vocabulary across the roster
- **WHEN** a member is bound to a profile the fighters index records as `Czech Republic`
- **THEN** the member's nationality reads `CZ` on the Teams tab, in the organizer's teams view and on the public roster

#### Scenario: A country Squire cannot read keeps its words
- **WHEN** a member is bound to a profile whose nationality names no country Squire can identify
- **THEN** that spelling is kept as given and the member is not treated as incomplete

#### Scenario: Member HR does not know
- **WHEN** the entering fencer types a name and the search offers no matching profile
- **THEN** the member is stored with that name and no identifier, and is treated as a complete member everywhere

#### Scenario: Member is not an account
- **WHEN** a roster names a person who has no Squire account
- **THEN** no account, no invitation, no registration, and no payment obligation is created for that person

#### Scenario: Same person on two rosters
- **WHEN** two teams name the same HEMA Ratings profile
- **THEN** both rosters carry their own member row and neither team is affected by the other
