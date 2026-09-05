## ADDED Requirements

### Requirement: Intake takes in only rows new to the tournament
Uploads SHALL accumulate rather than replace. A tournament's imported rows SHALL be the union of every row every upload has brought, and an upload SHALL take in only those of its rows the tournament does not already hold.

A row SHALL be recognised as one the tournament already holds when its content is identical to a row already imported — the same fingerprint that already lets a re-upload reuse a stored parse. Recognition SHALL be exact. A row whose content the organizer has changed since the previous upload SHALL be taken in as a new row; the two rows describing one fencer SHALL be settled by deduplication, as any such pair is.

A recognised row SHALL NOT be taken in a second time: it SHALL keep the parse decision, the match proposal, the corrections and the fixed number it already has, and no new source row SHALL be created for it. Where a file carries a row more times than the tournament holds it, the further occurrences SHALL be taken in as the distinct rows they are.

The outcome an upload reports SHALL state how many of the file's rows were recognised and skipped, distinctly from those parsed and those whose stored parse was reused, so that a large file bringing few rows does not read as a failure.

#### Scenario: The same form export, a few rows longer
- **WHEN** the organizer uploads a Google Form export, and later uploads it again with four rows appended and the rest unchanged
- **THEN** four rows are taken in and parsed, the earlier rows are recognised and skipped, and the table holds every row of both uploads exactly once

#### Scenario: An unchanged row keeps everything it has
- **WHEN** a row the organizer corrected by hand appears unchanged in a later upload
- **THEN** it is recognised, its correction still applies, its fixed number is unchanged, and the LLM is not invoked for it

#### Scenario: An edited row arrives as a new row
- **WHEN** the organizer fixes a club in the source spreadsheet and uploads the file again
- **THEN** that row is taken in as a new row and parsed afresh, the row with the old content remains in the table, and the two are offered to deduplication

#### Scenario: A file bringing nothing new
- **WHEN** the organizer uploads a file every row of which the tournament already holds
- **THEN** no row is taken in, no LLM call is made, and the outcome states that every row was recognised

#### Scenario: A duplicate line taken in as its own row
- **WHEN** a tournament holds one copy of a row and a later file carries that row twice
- **THEN** the first copy is recognised and the second is taken in as a distinct row, for deduplication to settle

## MODIFIED Requirements

### Requirement: Re-uploading a corrected table
The organizer MAY upload a corrected version of a table already imported. The upload SHALL add what is new to the tournament and SHALL NOT replace what it already holds.

A row the new file carries unchanged SHALL be recognised as the same row: its stored parse SHALL be reused without invoking the LLM again, and any correction the organizer has made to it SHALL still apply. A row whose content the new file changes SHALL be taken in and parsed afresh, and corrections made against its previous content SHALL NOT be carried onto it — the organizer corrected a row that no longer exists.

A row the new file no longer contains SHALL remain in the tournament. Once imported, a row belongs to the tournament rather than to the upload that carried it, and an upload that omits it is not distinguishable from one that never carried it. Removing such a row SHALL be the reversible row deletion the table offers, or a clear.

Re-uploading SHALL NOT disturb decisions recorded about fencers on the fencer list, nor the parse decisions of rows not present in either file.

#### Scenario: Corrected file preserves earlier corrections
- **WHEN** the organizer fixes two rows in the source spreadsheet, re-uploads it, and the remaining rows are byte-identical
- **THEN** only the two changed rows are parsed by the LLM, and the organizer's corrections to the unchanged rows still stand

#### Scenario: Row dropped from the file stays
- **WHEN** a re-uploaded file omits a row the previous upload contained
- **THEN** that row remains in the table with its number and its decisions, and the organizer may delete it if it does not belong

#### Scenario: Corrections do not follow changed content
- **WHEN** the organizer corrected a club on a row and the re-uploaded file states different content for that row
- **THEN** the row with the new content is parsed afresh and the earlier correction does not apply to it
