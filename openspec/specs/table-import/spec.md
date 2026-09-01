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
Imported fencers without a confirmed hr_id SHALL be fuzzy-matched by an LLM
against the fighters index, tolerant of diacritics, nicknames, and
transliterations. Results SHALL surface for review in the Matching phase as one
of three machine verdicts, and organizer corrections SHALL persist as rules.

The three machine verdicts are:

- **found** — the profile agrees with the registration on every signal the
  system can check: the names carry the same **name key**, the nationality does
  not contradict, and that name key identifies exactly one fighter in the index.
  Nothing was judged, only looked up, and the row owes the organizer no work.
- **proposed** — a match the model reached by judgment: a differing spelling, a
  nickname, a transliteration, a name carrying a token the other does not, a
  contradicting field, or a name key that more than one fighter in the index
  answers to. The row owes the organizer a look.
- **no match** — the model found no profile it would stand behind.

A **name key** is a name reduced to its words, each folded so that diacritics
and case do not distinguish it, taken without regard to the order the words
appear in. Two names share a key when they carry the same words: *Jan Novák* and
*Novák Jan* are one person under two conventions, and the system SHALL treat
them as agreeing. Names differing by a word one carries and the other does not
SHALL NOT share a key — a name key is not a subset test.

The tier SHALL be derived by the system from the stored match decision and the
index, not taken from a confidence the model reports about itself, so that the
same decision always yields the same tier and the reason for it is legible in
the claim and evidence registers the organizer is already looking at. A club
that differs SHALL NOT by itself hold a match out of **found**; club spellings
vary too freely to carry that weight.

The two sides name a country in different vocabularies — a registration writes
an ISO code, the fighters index writes an English name — so nationalities SHALL
be resolved to the country they name before they are compared, and SHALL
contradict only where they resolve to different countries. Comparing the
spellings instead would make nearly every fencer registered from abroad look
like a disagreement. Where either spelling names no country the system can
identify, the nationalities SHALL NOT be held to contradict: failing to
interpret a spelling is not the fencer disagreeing with their profile, and the
row would show no reason for the demotion.

An ambiguous name key SHALL never read as **found**, however exactly it
matches: where the index holds more than one fighter under the same name key,
the choice among them is a judgment, and the organizer makes it. Ambiguity SHALL
be judged by the same key the agreement is judged by, so that two fighters
indexed as *Jan Novák* and *Novák Jan* count as the ambiguity they are.

Deriving the tier SHALL NOT require re-invoking the LLM: a decision already
stored SHALL take its tier on the next recomputation of the table.

#### Scenario: Transliterated name
- **WHEN** an imported fencer's name differs from their HR profile only by transliteration
- **THEN** the profile is proposed as a match candidate rather than reported as unmatched, and the row reads proposed

#### Scenario: Exact hit owes no work
- **WHEN** an imported fencer's name key is carried by exactly one indexed fighter and their nationality agrees
- **THEN** the row reads found and is not queued for the organizer's attention

#### Scenario: Differing club does not demote an exact hit
- **WHEN** an imported fencer's name key matches unambiguously but their registered club is spelled differently from the profile's
- **THEN** the row still reads found

#### Scenario: A code and a country name are one country
- **WHEN** an imported fencer registered as "PL" matches unambiguously to a profile the index records as "Poland"
- **THEN** the nationalities are found to agree and the row reads found

#### Scenario: An uninterpretable nationality demotes nothing
- **WHEN** either side spells a nationality the system cannot resolve to a country
- **THEN** the nationalities are not held to contradict, and the other signals decide the tier

#### Scenario: Surname-first registration
- **WHEN** an imported fencer is registered as "Novák Jan" and the matched profile reads "Jan Novák"
- **THEN** the row reads found, the reversed order not being a difference the organizer needs to adjudicate

#### Scenario: An extra given name is a difference
- **WHEN** an imported fencer's name carries a word the matched profile's does not
- **THEN** the names do not share a key and the row reads proposed

#### Scenario: Two fighters share a name key
- **WHEN** an imported fencer's name key is answered by more than one fighter in the index
- **THEN** the row reads proposed however exact the match, and the organizer chooses

#### Scenario: Existing decisions take a tier without a rerun
- **WHEN** the table is recomputed after the tiers are introduced, over match decisions stored before them
- **THEN** each stored decision takes its tier, and no LLM call is made

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

### Requirement: Decision persistence and incrementality
LLM outputs — parses, match proposals, merges, classifications — SHALL be materialized as decisions. Reruns SHALL reuse stored decisions; only rows without decisions SHALL invoke the LLM.

A decision SHALL become durable as soon as the work that produced it completes, not only when the whole run completes. A run that stops partway — interrupted, failed, or abandoned — SHALL leave every decision it had already produced standing, and running the same work again SHALL reuse them and invoke the LLM only for what remains.

Decisions stored before disciplines carried slugs SHALL remain readable: a stored decision describing a discipline as a weapon, gender, and material SHALL resolve to the discipline whose classification matches, and SHALL be treated as ambiguous — as an unresolved parse is — where more than one offered discipline matches. Such decisions SHALL NOT be re-parsed merely because their shape is older; they are replaced when their row changes and is parsed afresh.

#### Scenario: Cheap rerun
- **WHEN** the organizer reruns after changing a display parameter
- **THEN** no LLM call is made for already-decided rows

#### Scenario: Partial parse survives an interruption
- **WHEN** an import has parsed sixty of two hundred and twenty rows and the server restarts
- **THEN** the sixty parses stand as decisions, and re-uploading the same file parses only the remaining rows

#### Scenario: Partial parse survives a failure
- **WHEN** an import fails partway because the LLM becomes unreachable
- **THEN** the rows parsed before the failure keep their decisions

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

### Requirement: Import, matching and deduplication are started rather than awaited
Uploading a table, running matching, and running deduplication SHALL each start an operation of the tournament and return at once, rather than hold their request open for the length of the work. Each SHALL be subject to the tournament's one-operation-at-a-time rule and SHALL be reported on through its record.

Uploading SHALL record the uploaded file and its rows before returning, so that a batch reaches the tournament whole even where the organizer abandons the response. Only the parsing of those rows SHALL proceed in the background.

Where no LLM is configured, an upload SHALL still record its batch and rows and SHALL report that the rows are unparsed, as it does today, without starting an operation that has nothing to do.

#### Scenario: Upload returns before the parse
- **WHEN** the organizer uploads a table of two hundred rows
- **THEN** the upload returns immediately, the batch and its rows exist, and parsing runs as an operation

#### Scenario: Batch survives an abandoned upload response
- **WHEN** the organizer navigates away the moment after uploading
- **THEN** the batch and all its source rows are recorded, and the parse continues

#### Scenario: Matching started while an import parses
- **WHEN** an import operation is running and the organizer starts matching
- **THEN** the start is refused and names the running import

#### Scenario: No LLM configured
- **WHEN** the organizer uploads a table on a deployment with no LLM configured
- **THEN** the batch and its rows are recorded, the rows are reported unparsed, and no operation is started
