# discipline-identity Specification

## Purpose
Define a discipline's identity as a slug distinct from its name and from its classification (weapon, gender, material), and define the taxonomy code derived from that classification for joining a discipline to systems outside itself (HEMA Ratings categories, imports).

## Requirements

### Requirement: Discipline identity is a slug
A discipline SHALL be identified within its tournament by a **slug**: a short string, unique among that tournament's disciplines, used as the discipline's identifier in API paths, in registration payloads, in exports, in spreadsheet columns, and in import parses. A tournament MAY offer any number of disciplines whose classification is identical; nothing SHALL prevent two disciplines from sharing a weapon, gender, material, or kind. A discipline's slug SHALL NOT be its name and SHALL NOT be its classification: renaming a discipline SHALL NOT change its slug, and two disciplines classified alike SHALL carry different slugs.

#### Scenario: Two tiers of one weapon
- **WHEN** the organizer adds two longsword disciplines, naming one for its top bracket and the other for its open bracket
- **THEN** both are created, each with its own slug, capacity, and price, and registration offers them as two separate entries

#### Scenario: Individual and team in the same weapon
- **WHEN** the organizer adds an individual longsword discipline and a team longsword discipline to one tournament
- **THEN** both are created and neither is rejected as a duplicate

#### Scenario: Renaming does not move identity
- **WHEN** an unreferenced discipline's name is changed
- **THEN** its slug is unchanged, and every export, spreadsheet column, and stored reference still resolves to it

### Requirement: Slug generation and override
The system SHALL generate a discipline's slug from its kind and its classification when the discipline is created, disambiguating against the tournament's existing slugs by appending a counter. A team discipline's generated slug SHALL be distinguishable from that of an individual discipline classified alike, so that a tournament running both offers two slugs that state which is which. The organizer MAY override the generated slug with one of their own. An override SHALL be subject to the same uniqueness check as a generated slug, and an attempt to take a slug already used in that tournament SHALL be refused with a message naming the conflict.

Every slug SHALL be normalized before it is stored, whether generated or supplied by the organizer, so that it is safe to place in a URL path, a spreadsheet column, and an import parse: diacritics folded to their unaccented forms, every run of characters outside letters, digits, and `-` collapsed to a single `-`, and leading and trailing `-` removed. Normalization SHALL preserve case, so that a slug derived from a taxonomy code reads as that code does everywhere else in the system. Normalization applies when a slug is written; it SHALL NOT by itself rewrite a slug already stored, which changes only when the discipline is edited or by an explicit migration.

#### Scenario: Slug generated from classification
- **WHEN** the organizer adds an open steel individual longsword discipline to a tournament that has none
- **THEN** its slug is generated as `LS` without the organizer entering anything

#### Scenario: Team discipline slug states its kind
- **WHEN** the organizer adds a team longsword discipline to a tournament that already offers an individual longsword discipline
- **THEN** its slug is generated as `Team-LS`, and the individual discipline's slug is unchanged

#### Scenario: Collision disambiguated
- **WHEN** the organizer adds a second open steel individual longsword discipline
- **THEN** its slug is generated as `LS-2`, and the first discipline's slug is unchanged

#### Scenario: Organizer overrides the slug
- **WHEN** the organizer replaces the generated slugs of two longsword disciplines with `LS-A` and `LS-B`
- **THEN** both are accepted as typed and used thereafter as those disciplines' identifiers

#### Scenario: Override collides
- **WHEN** the organizer sets a discipline's slug to one another discipline in the same tournament already uses
- **THEN** the change is refused, the conflict is named, and neither discipline's slug changes

#### Scenario: Slug generated from a weapon outside the taxonomy
- **WHEN** the organizer adds a discipline whose weapon is `Tešák`
- **THEN** its slug is generated as `Tesak`, carrying no character that would need encoding in a URL or a spreadsheet column

#### Scenario: Override normalized
- **WHEN** the organizer overrides a slug with `Sword & Buckler (variant)`
- **THEN** it is stored as `Sword-Buckler-variant`, and that is the identifier used thereafter

#### Scenario: Existing slugs not rewritten
- **WHEN** a tournament created before slugs stated their kind holds a team discipline whose slug is `LS-2`
- **THEN** that slug is unchanged, and every stored URL, export, and spreadsheet column still resolves to it

### Requirement: Slug frozen once referenced
A discipline's slug SHALL be editable while no registration references the discipline, and SHALL be frozen once any individual entry or any team references it. An attempt to change a frozen slug SHALL be refused. This is the same freeze condition that governs a discipline's kind, and the two SHALL be evaluated against the same references.

#### Scenario: Slug edited before anyone registers
- **WHEN** the organizer changes the slug of a discipline no fencer has entered
- **THEN** the change is accepted

#### Scenario: Slug frozen after an individual entry
- **WHEN** a fencer has entered a discipline and the organizer attempts to change its slug
- **THEN** the change is refused and the discipline keeps its slug

#### Scenario: Slug frozen after a team entry
- **WHEN** a team has been entered into a team discipline and the organizer attempts to change its slug
- **THEN** the change is refused and the discipline keeps its slug

### Requirement: Frozen identity is reported, not discovered by attempting an edit
A discipline SHALL report whether its identity is frozen, alongside the discipline itself, so that an organizer surface can withhold an edit rather than offer one the system will refuse. The reported state SHALL be derived from the same references that govern the freeze — any individual entry or any team pointing at the discipline, whatever the state of that entry — and SHALL NOT be derived from the count of occupied seats, which excludes cancelled and expired entries, excludes substitutes, and does not apply to team disciplines at all. The report SHALL cover the whole of what freezes together: slug, classification, and kind. A discipline's name SHALL NOT be covered by it, since a name stays editable for the tournament's whole life.

#### Scenario: Frozen state accompanies the discipline
- **WHEN** a surface reads a tournament's disciplines
- **THEN** each one states whether its identity is frozen, without that surface having to attempt an edit to find out

#### Scenario: A cancelled entry still freezes
- **WHEN** a fencer has entered a discipline and that registration has since been cancelled, leaving no seat occupied
- **THEN** the discipline reports its identity as frozen, and an attempt to change its slug is refused

#### Scenario: A team entry freezes a team discipline
- **WHEN** a team has been entered into a team discipline
- **THEN** that discipline reports its identity as frozen

#### Scenario: An unreferenced discipline is not frozen
- **WHEN** a discipline exists that no entry and no team references
- **THEN** it reports its identity as not frozen, and its slug, classification, and kind can all be changed

#### Scenario: Name editable on a frozen discipline
- **WHEN** the organizer renames a discipline whose identity is frozen
- **THEN** the rename is accepted, and the discipline's slug, classification, and kind are unchanged

### Requirement: Discipline classification
A discipline SHALL carry its classification as separate fields: **weapon**, **gender**, and **material**. Gender SHALL be one of Open, Women, or Men, and material SHALL be one of Steel or Plastic; both are closed sets. Weapon SHALL offer the HEMA taxonomy weapons (LS Longsword, SA Sabre, RA Single Rapier, RD Rapier & Dagger, SB Sword & Buckler) and SHALL additionally accept a weapon the taxonomy does not name. A discipline whose weapon is outside the taxonomy SHALL require an explicit name, since none can be generated for it; a discipline whose weapon is within the taxonomy SHALL have its name generated by default and SHALL allow it to be replaced. A generated name SHALL state that a discipline is a team discipline, so that a tournament offering both an individual and a team discipline classified alike does not present a fencer with two entries bearing the same name.

#### Scenario: Classification entered as fields
- **WHEN** the organizer adds a discipline choosing sabre, women, and plastic
- **THEN** the discipline records those three values separately, and its name defaults to the taxonomy name for that combination

#### Scenario: Team discipline name states its kind
- **WHEN** the organizer adds an individual longsword discipline and a team longsword discipline, accepting the generated name for both
- **THEN** the two names differ, and the team discipline's name states that it is a team discipline

#### Scenario: Weapon outside the taxonomy
- **WHEN** the organizer adds a discipline whose weapon is Messer
- **THEN** it is accepted, and the organizer is required to give it a name

#### Scenario: Custom weapon without a name
- **WHEN** the organizer adds a discipline with a weapon outside the taxonomy and leaves the name empty
- **THEN** the discipline is refused with a message stating that a name is required for this weapon

### Requirement: Taxonomy code derived for external joins
A discipline's **taxonomy code** SHALL be derived from its weapon, gender, and material, in the form the HEMA taxonomy uses (optional material prefix, weapon code, gender suffix — `LS`, `SAW`, `Plastic LSM`). It SHALL NOT be stored as a discipline's own field and SHALL NOT identify a discipline. It SHALL be the key by which the system joins a discipline to anything outside itself, so that disciplines sharing a classification share that join and cannot drift apart. A discipline whose weapon is outside the taxonomy SHALL derive a taxonomy code that no external mapping recognizes, and SHALL be treated as having no external counterpart rather than as an error.

#### Scenario: Tiers share one external join
- **WHEN** a tournament offers two longsword disciplines and the organizer configures the external mapping for longsword
- **THEN** one mapping governs both disciplines, and there is no way to configure them differently

#### Scenario: Custom weapon has no counterpart
- **WHEN** a discipline's weapon is outside the taxonomy
- **THEN** it resolves to no external counterpart, and its absence is not reported as a failure
