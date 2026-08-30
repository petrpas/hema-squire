## MODIFIED Requirements

### Requirement: Deduplication of records sharing an HR identity
Imported records sharing an hr_id SHALL be queued for the organizer's review with a proposed merge: inputs ordered by registration time, merge proposal prepared by an LLM, prefilled with the most recent explicit value per field. The proposal SHALL be correctable before it is confirmed — field by field and in its note — and what the organizer confirms SHALL be the proposal as they left it. Nothing merges until the organizer confirms; the confirmation SHALL persist as a rule, with a merge note recorded and superseded values visible in the audit trail.

#### Scenario: Fencer registered twice
- **WHEN** two imported rows carry the same hr_id
- **THEN** the pair appears in a decision queue with a prefilled merge proposal, and after the organizer confirms, one merged record remains, carrying a note describing the merge

#### Scenario: The proposal is corrected before it is confirmed
- **WHEN** the organizer changes a field of the prefilled merge and then confirms
- **THEN** the merged record carries the changed value, and the LLM's proposal is not what took effect

### Requirement: Three-band deduplication without HR identity
Candidate duplicate groups among records without an hr_id SHALL be classified by an LLM into three bands: surely (merged automatically), likely (queued for the organizer's decision), and possible (discarded without action). Organizer decisions on likely groups SHALL persist as rules.

A group the classifier merged of its own accord SHALL be visible in the console as a decision the machine took, and the organizer SHALL be able to withdraw it in one action, as fixed by `etl-console`. Automatic is not silent: the band exists to spare the organizer a confirmation, not to hide a change to the fencer list.

A group in the possible band SHALL leave no trace in the console. It is discarded to keep false positives off the screen, and surfacing it would defeat the classification.

#### Scenario: Likely duplicate queued
- **WHEN** two no-id records are classified as likely duplicates
- **THEN** the pair appears in a decision queue and nothing merges until the organizer decides

#### Scenario: An automatic merge is shown and withdrawable
- **WHEN** two no-id records are classified as surely duplicates and merged by the run
- **THEN** the console lists the group as merged by the machine, and one action withdraws the merge

#### Scenario: A possible group is not shown
- **WHEN** two no-id records are classified as possible duplicates
- **THEN** nothing merges and no candidate appears in the console
