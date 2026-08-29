# table-import Specification

## Purpose
Import external registration tables and process them with LLM parsing, HR matching, and deduplication, materializing LLM outputs as reusable decisions.

## Requirements

### Requirement: External table import
The organizer MAY import an external registration table (CSV, XLSX, or Google Sheet) instead of, or alongside, in-app registrations. Imported records SHALL retain provenance (source file and row) and the originally registered name (reg_name) whenever a canonical name is later applied.

#### Scenario: Legacy Google Form export
- **WHEN** the organizer imports a Google Form response sheet
- **THEN** each row becomes a fencer record traceable back to its source row

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

### Requirement: LLM matching to HEMA Ratings
Imported fencers without a confirmed hr_id SHALL be fuzzy-matched by an LLM against the fighters index, tolerant of diacritics, nicknames, and transliterations. Results SHALL surface as ✓/?/✗ verdicts for review in the Matching phase; organizer corrections SHALL persist as rules.

#### Scenario: Transliterated name
- **WHEN** an imported fencer's name differs from their HR profile only by transliteration
- **THEN** the profile is proposed as a match candidate rather than reported as unmatched

### Requirement: Deduplication of records sharing an HR identity
Imported records sharing an hr_id SHALL be queued for the organizer's review with a proposed merge: inputs ordered by registration time, merge proposal prepared by an LLM, prefilled with the most recent explicit value per field. Nothing merges until the organizer confirms; the confirmation SHALL persist as a rule, with a merge note recorded and superseded values visible in the audit trail.

#### Scenario: Fencer registered twice
- **WHEN** two imported rows carry the same hr_id
- **THEN** the pair appears in a decision queue with a prefilled merge proposal, and after the organizer confirms, one merged record remains, carrying a note describing the merge

### Requirement: Three-band deduplication without HR identity
Candidate duplicate groups among records without an hr_id SHALL be classified by an LLM into three bands: surely (merged automatically), likely (queued for the organizer's decision), and possible (discarded without action). Organizer decisions on likely groups SHALL persist as rules.

#### Scenario: Likely duplicate queued
- **WHEN** two no-id records are classified as likely duplicates
- **THEN** the pair appears in a decision queue and nothing merges until the organizer decides

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

### Requirement: Re-uploading a corrected table
The organizer MAY upload a corrected version of a table already imported. The newest upload SHALL replace the previous one as the tournament's imported batch; rows the new file no longer contains SHALL leave the fencer list with it.

A row the new file carries unchanged SHALL be recognised as the same row: its stored parse SHALL be reused without invoking the LLM again, and any correction the organizer has made to it SHALL still apply. A row whose content the new file changes SHALL be parsed afresh, and corrections made against its previous content SHALL NOT be carried onto it — the organizer corrected a row that no longer exists.

Re-uploading SHALL NOT disturb decisions recorded about fencers on the fencer list, nor the parse decisions of rows not present in either file.

#### Scenario: Corrected file preserves earlier corrections
- **WHEN** the organizer fixes two rows in the source spreadsheet, re-uploads it, and the remaining rows are byte-identical
- **THEN** only the two changed rows are parsed by the LLM, and the organizer's corrections to the unchanged rows still stand

#### Scenario: Row dropped from the file
- **WHEN** a re-uploaded file omits a row the previous upload contained
- **THEN** that row is no longer part of the tournament's imported batch

#### Scenario: Corrections do not follow changed content
- **WHEN** the organizer corrected a club on a row and the re-uploaded file states different content for that row
- **THEN** the row is parsed afresh and the earlier correction does not apply to it
