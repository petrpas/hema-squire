# data-export Specification

## Purpose
Export tournament data in the canonical JSON format and the legacy Google Sheets format consumed by v1 in-tournament tooling.

## Requirements

### Requirement: Canonical JSON export
The full tournament dataset SHALL be exportable in the application's own versioned JSON format, sufficient to reconstruct the fencer table, registrations, and payment states.

#### Scenario: Round-trip fidelity
- **WHEN** a tournament is exported and re-imported into an empty deployment
- **THEN** the reconstructed fencer table matches the original

### Requirement: Google Sheets export in the legacy format
The system SHALL export to Google Sheets in the v1 format: a Fencers worksheet with columns Reg. | Name | Nat. | Club | HR_ID | Disciplines | Paid | Afterparty | Borrow weapons | Notes, and one worksheet per discipline with columns No. | Name | Nat. | Club | HR_ID | HRating | HRank.

#### Scenario: Downstream compatibility
- **WHEN** the sheet export completes
- **THEN** the v1 in-tournament tooling can consume the sheet unchanged

### Requirement: Repeat-export preservation semantics
Re-exporting to an existing sheet SHALL leave manually managed columns (Reg., No.) untouched, SHALL always refresh HRating and HRank, and SHALL write other cells only when blank or unchanged, preserving downstream manual work.

#### Scenario: Manual numbering survives
- **WHEN** the organizer re-exports after downstream staff filled the No. column
- **THEN** the numbering is preserved while ratings refresh

### Requirement: Export scope
Deleted (withdrawn) rows SHALL be excluded from exports. Payment state SHALL be exported in the Paid column.

#### Scenario: Withdrawn fencer
- **WHEN** a row was deleted in the console before export
- **THEN** the fencer appears in no exported worksheet
