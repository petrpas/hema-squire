## ADDED Requirements

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
