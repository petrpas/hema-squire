# hr-integration Specification

## Purpose
Integrate with HEMA Ratings: maintain a cached fighters index, detect source format drift, snapshot ratings per discipline, and apply canonical HR naming.

## Requirements

### Requirement: Fighters index
The system SHALL maintain a cached index of HEMA Ratings fighters (hr_id, canonical name, nationality, club), refreshable on demand, serving account-creation search and import matching.

#### Scenario: Index refresh
- **WHEN** the organizer triggers an index refresh
- **THEN** newly registered HR fighters become findable in account creation and matching

### Requirement: Source format drift detection
WHEN the HEMA Ratings page format changes and parsing yields an implausible result, the system SHALL fail loudly with actionable diagnostics rather than store a degraded index.

#### Scenario: Broken scrape
- **WHEN** a refresh parses out an anomalously small or malformed fighters list
- **THEN** the previous index is kept and the operator is shown what failed

### Requirement: Ratings snapshots
The system SHALL fetch weighted rating and rank per fencer per discipline as dated snapshots. The mapping from tournament disciplines to HEMA Ratings categories SHALL be a per-tournament parameter. Exports SHALL use a selected snapshot, defaulting to the latest.

#### Scenario: Snapshot selection
- **WHEN** the organizer exports discipline sheets
- **THEN** HRating and HRank come from the chosen dated snapshot

### Requirement: Canonical naming
The HR canonical name SHALL be the display name for HR-bound fencers; the originally registered name SHALL be preserved alongside it.

#### Scenario: Name normalization
- **WHEN** an imported fencer is bound to an HR profile with a differently spelled name
- **THEN** the HR spelling becomes the display name and the original stays retrievable

### Requirement: Nationality-filtered similarity search
The fighters-index search SHALL support an optional nationality filter that restricts the candidate space before name matching, and SHALL rank name matches by text similarity (diacritics-insensitive). The system SHALL expose the list of nationalities present in the index for building the filter. Results SHALL include hr_id, canonical name, nationality, and club.

#### Scenario: Nationality narrows then name ranks
- **WHEN** a search runs with nationality "Czechia" and name query "pascenko"
- **THEN** only Czech fighters are considered and results are ordered by name similarity to the query, each with hr_id, name, nationality, and club

#### Scenario: No nationality given
- **WHEN** a search runs with a name query and no nationality filter
- **THEN** the whole index is searched and results are ranked by name similarity
