## MODIFIED Requirements

### Requirement: Canonical JSON export
The full tournament dataset SHALL be exportable in the application's own versioned JSON format, sufficient to reconstruct the fencer table, registrations, and payment states.

The document SHALL additionally carry every team and every roster member, so that a restore reconstructs teams and rosters exactly as they stood: each team with its discipline, its entering fencer's registration, its name, its waitlisted state and its entry order, and each member with its position, name, and — where bound — HEMA Ratings identifier, club, and nationality. A roster member SHALL be exported as the plain record it is, never as a fencer account, and restoring one SHALL NOT create an account. Discipline kind and roster bounds, and the tournament's team composition deadline, SHALL be exported with their owners.

The document version SHALL be raised for this addition. Documents produced before it SHALL remain loadable and SHALL restore with no teams, no rosters, every discipline individual, and no composition deadline.

#### Scenario: Round-trip fidelity
- **WHEN** a tournament is exported and re-imported into an empty deployment
- **THEN** the reconstructed fencer table matches the original

#### Scenario: Teams and rosters round-trip
- **WHEN** a tournament with a team discipline, four teams (one waitlisted) and their rosters is exported and re-imported into an empty deployment
- **THEN** every team is reconstructed with its name, discipline, entering fencer, waitlisted state and entry order, and every roster with its members in order and their HEMA Ratings bindings intact

#### Scenario: Unbound members survive
- **WHEN** an exported roster contains members with no HEMA Ratings identifier
- **THEN** they are restored by name with no identifier and no account is created for them

#### Scenario: Older document still loads
- **WHEN** a document produced before teams existed is restored
- **THEN** it loads, every discipline is individual, and the deployment carries no teams and no composition deadline

### Requirement: Google Sheets export in the legacy format
The system SHALL export to Google Sheets in the v1 format: a Fencers worksheet with columns Reg. | Name | Nat. | Club | HR_ID | Disciplines | Paid | Afterparty | Borrow weapons | Notes, and one worksheet per discipline with columns No. | Name | Nat. | Club | HR_ID | HRating | HRank.

Teams SHALL NOT change this format. A roster member SHALL NOT appear in the Fencers worksheet — they hold no registration, so they have no row — and a team discipline SHALL NOT produce a worksheet. How team participation reaches the in-tournament tooling is out of scope here.

#### Scenario: Downstream compatibility
- **WHEN** the sheet export completes
- **THEN** the v1 in-tournament tooling can consume the sheet unchanged

#### Scenario: Teams absent from the sheet
- **WHEN** a tournament with team disciplines and rosters is exported to Sheets
- **THEN** the worksheets are exactly those the same tournament would produce without teams, and no roster member appears in the Fencers worksheet
