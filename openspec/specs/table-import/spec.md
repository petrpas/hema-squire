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

### Requirement: Clearing the tournament's imported content
The organizer MAY clear everything the tournament has imported. Clearing SHALL remove every uploaded batch, every source row those batches carried, every decision taken about those rows — parses, match proposals, merge proposals, dedup classifications — and every manual correction recorded against them. The removal SHALL be a deletion of the data, not a marking of it: nothing cleared SHALL remain visible, restorable, or countable anywhere in the console afterwards, and the tournament SHALL read as one that never imported anything.

Clearing SHALL leave every row that did not come from a file untouched. In-app registrations and manually entered rows SHALL keep their content, their notes, their fixed numbers, and the decisions and edits recorded about them.

Where a correction or a merge decision names both an imported row and a row of another population, clearing SHALL remove that decision too — it was taken about a row that no longer exists — while leaving the other row itself in place.

Clearing SHALL NOT be offered as an undo of a single upload: it removes all imported content at once, including batches superseded by later uploads, so that clearing never leaves an older file's rows behind to become the table again.

#### Scenario: Wrong file removed altogether
- **WHEN** the organizer uploads the wrong table and then clears
- **THEN** the Import view is empty, no imported row appears on the fencer list, and the Import log is empty

#### Scenario: Registrations survive a clear
- **WHEN** a tournament with twelve in-app registrations and an imported batch is cleared
- **THEN** the twelve registrations remain on the fencer list with their numbers and their edit history unchanged

#### Scenario: Superseded batches go too
- **WHEN** the organizer has uploaded three successive files and clears
- **THEN** no rows of any of the three remain, and the Import view does not fall back to an earlier upload

#### Scenario: Re-import after a clear starts clean
- **WHEN** the organizer clears and then uploads the correct file
- **THEN** every row of the new file is parsed afresh, with no decision or correction carried over from the cleared content

#### Scenario: Merge decision naming a cleared row
- **WHEN** an imported row had been merged into an in-app registration and the tournament is cleared
- **THEN** the merge is gone along with the imported row, and the registration stands on its own, unmerged

### Requirement: Clearing is warned about and irreversible
Clearing SHALL be confirmed before it happens. The confirmation SHALL state what is about to be removed — how many rows, from how many uploaded files — and SHALL state plainly that the removal cannot be undone. It SHALL be distinguishable from the reversible row deletion the table already offers, which removes a row from view while keeping it restorable.

Dismissing the confirmation SHALL leave everything as it was. Confirming SHALL be final: no undo action, no restore, and no entry in any log SHALL bring the cleared content back.

#### Scenario: Confirmation states the cost
- **WHEN** the organizer activates the clear action on a tournament holding forty imported rows from two files
- **THEN** the confirmation names the forty rows and the two files, and says the removal cannot be undone

#### Scenario: Dismissed confirmation changes nothing
- **WHEN** the organizer dismisses the confirmation
- **THEN** the imported rows, decisions and corrections all remain exactly as before

#### Scenario: No undo after confirming
- **WHEN** the organizer confirms the clear and then looks for a way back
- **THEN** none is offered, and the manual-edits log holds no entry that restores the cleared content

#### Scenario: Nothing to clear
- **WHEN** the organizer opens Import on a tournament that has imported nothing
- **THEN** the clear action is not offered
