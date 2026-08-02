## MODIFIED Requirements

### Requirement: Canonical JSON export
The full tournament dataset SHALL be exportable in the application's own versioned JSON format, sufficient to reconstruct the fencer table, registrations, and payment states.

A discipline SHALL be exported with its slug, its name, its weapon, its gender, and its material, and every reference to a discipline elsewhere in the document — an individual entry, a team — SHALL identify it by slug. The document SHALL NOT carry a discipline's derived taxonomy code, which is reconstructible from the exported classification. A restore SHALL resolve discipline references by slug, and SHALL reject a document referencing a slug it does not define rather than restoring a partial registration.

The document SHALL additionally carry every team and every roster member, so that a restore reconstructs teams and rosters exactly as they stood: each team with its discipline, its entering fencer's registration, its name, its waitlisted state and its entry order, and each member with its position, name, and — where bound — HEMA Ratings identifier, club, and nationality. A roster member SHALL be exported as the plain record it is, never as a fencer account, and restoring one SHALL NOT create an account. Discipline kind and roster bounds, and the tournament's team composition deadline, SHALL be exported with their owners.

The document version SHALL be raised for this addition. Documents produced before it SHALL remain loadable: a discipline carrying a code and no classification SHALL restore with that code as its slug and its classification parsed from it, which is exactly what the migration does to stored rows.

#### Scenario: Round-trip fidelity
- **WHEN** a tournament is exported and re-imported into an empty deployment
- **THEN** the reconstructed fencer table matches the original

#### Scenario: Tiers round-trip
- **WHEN** a tournament offering two longsword disciplines, with fencers entered in each, is exported and re-imported into an empty deployment
- **THEN** both disciplines are reconstructed under their own slugs, names, capacities and fees, and every fencer is restored into the one they had entered

#### Scenario: Individual and team in one weapon round-trip
- **WHEN** a tournament offering both an individual and a team longsword discipline is exported and re-imported
- **THEN** both are reconstructed with their own slugs and kinds, and no entry is attached to the wrong one

#### Scenario: Classification round-trips
- **WHEN** a tournament offering a discipline whose weapon is outside the taxonomy is exported and re-imported
- **THEN** that discipline is restored with its weapon, gender, material and name intact

#### Scenario: Dangling slug rejected
- **WHEN** a document references a discipline slug it does not define
- **THEN** the restore is rejected with the offending slug named, and no partial registration is created

#### Scenario: Teams and rosters round-trip
- **WHEN** a tournament with a team discipline, four teams (one waitlisted) and their rosters is exported and re-imported into an empty deployment
- **THEN** every team is reconstructed with its name, discipline, entering fencer, waitlisted state and entry order, and every roster with its members in order and their HEMA Ratings bindings intact

#### Scenario: Unbound members survive
- **WHEN** an exported roster contains members with no HEMA Ratings identifier
- **THEN** they are restored by name with no identifier and no account is created for them

#### Scenario: Older document still loads
- **WHEN** a document produced before disciplines carried a classification is restored
- **THEN** it loads, each discipline taking its old code as its slug and its classification parsed from that code, every discipline individual, and the deployment carries no teams and no composition deadline

### Requirement: Google Sheets export in the legacy format
The system SHALL export to Google Sheets in the v1 format: a Fencers worksheet with columns Reg. | Name | Nat. | Club | HR_ID | Disciplines | Paid | Afterparty | Borrow weapons | Notes, and one worksheet per discipline with columns No. | Name | Nat. | Club | HR_ID | HRating | HRank.

The Disciplines column SHALL carry discipline slugs, and each per-discipline worksheet SHALL be named for the discipline's slug. Slugs are unique within a tournament, so several disciplines classified alike produce several distinct worksheets and are distinguishable in the Disciplines column. A worksheet whose discipline has no HEMA Ratings counterpart SHALL still be produced, with its HRating and HRank columns empty.

Teams SHALL NOT change this format. A roster member SHALL NOT appear in the Fencers worksheet — they hold no registration, so they have no row — and a team discipline SHALL NOT produce a worksheet. How team participation reaches the in-tournament tooling is out of scope here.

#### Scenario: Downstream compatibility
- **WHEN** the sheet export completes
- **THEN** the v1 in-tournament tooling can consume the sheet unchanged

#### Scenario: Tiers produce separate worksheets
- **WHEN** a tournament offering two longsword disciplines is exported to Sheets
- **THEN** two worksheets are produced, named for the two slugs, each listing only its own entrants, and the Disciplines column distinguishes the two

#### Scenario: Unrated discipline still exported
- **WHEN** a tournament offering a discipline whose weapon is outside the taxonomy is exported to Sheets
- **THEN** that discipline's worksheet is produced with its entrants listed and its HRating and HRank columns empty

#### Scenario: Teams absent from the sheet
- **WHEN** a tournament with team disciplines and rosters is exported to Sheets
- **THEN** the worksheets are exactly those the same tournament would produce without teams, and no roster member appears in the Fencers worksheet
