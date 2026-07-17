## ADDED Requirements

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
