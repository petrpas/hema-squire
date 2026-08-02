## MODIFIED Requirements

### Requirement: LLM parsing of imported rows
Imported rows SHALL be parsed by an LLM into the canonical fencer record: registration time, name (first name first), nationality, email, club, hr_id when present, disciplines, weapon rentals, afterparty, after-sparring, accommodation, and notes. Content that fits no field SHALL land in notes; parsing doubts SHALL be recorded in a problems field and surfaced in the console.

The disciplines of a parsed row SHALL be **chosen from the disciplines the tournament offers**, identified by slug, rather than described as a weapon, gender, and material for the system to resolve. The parser SHALL be given the tournament's offered disciplines as slug and name together, so that a name — which is what carries a tier, a bracket, or a weapon the taxonomy does not know — is available as matching evidence. A parse SHALL NOT yield a discipline the tournament does not offer.

Where a row's content could mean any of several offered disciplines and does not say which — a source row naming a weapon in a tournament that splits that weapon across brackets — the parse SHALL record a problem and leave the discipline unresolved rather than choosing one. Legacy sources predate such splits and do not carry the information; guessing is not permitted where the source is silent.

#### Scenario: Messy source row
- **WHEN** a row's content does not map cleanly to the record
- **THEN** the record is created with its problems field populated and the row is flagged for review

#### Scenario: Discipline chosen from the offered list
- **WHEN** a row names a weapon the tournament offers exactly once
- **THEN** the parse yields that discipline's slug

#### Scenario: Row naming a tier resolves
- **WHEN** a tournament splits longsword into two named brackets and a source row names the weapon and the bracket
- **THEN** the parse yields the slug of the matching bracket

#### Scenario: Ambiguous row left unresolved
- **WHEN** a tournament splits longsword into two brackets and a source row names only the weapon
- **THEN** the parse records a problem for that row, leaves the discipline unresolved, and the row is flagged for the organizer to decide

#### Scenario: Weapon outside the taxonomy parsed
- **WHEN** a tournament offers a discipline whose weapon is outside the taxonomy and a source row names it
- **THEN** the parse yields that discipline's slug, the offered name having identified it

### Requirement: Decision persistence and incrementality
LLM outputs — parses, match proposals, merges, classifications — SHALL be materialized as decisions. Reruns SHALL reuse stored decisions; only rows without decisions SHALL invoke the LLM.

Decisions stored before disciplines carried slugs SHALL remain readable: a stored decision describing a discipline as a weapon, gender, and material SHALL resolve to the discipline whose classification matches, and SHALL be treated as ambiguous — as an unresolved parse is — where more than one offered discipline matches. Such decisions SHALL NOT be re-parsed merely because their shape is older; they are replaced when their row changes and is parsed afresh.

#### Scenario: Cheap rerun
- **WHEN** the organizer reruns after changing a display parameter
- **THEN** no LLM call is made for already-decided rows

#### Scenario: Older decision still resolves
- **WHEN** a row parsed before disciplines carried slugs is read after the migration, and its classification matches exactly one offered discipline
- **THEN** it resolves to that discipline without a new LLM call

#### Scenario: Older decision made ambiguous by a later split
- **WHEN** a row parsed before a tier split is read after the organizer has split that weapon into two disciplines
- **THEN** it is reported as unresolved for the organizer to decide, and is not silently attached to either
