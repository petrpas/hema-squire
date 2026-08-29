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
The system SHALL fetch weighted rating and rank per fencer per discipline as dated snapshots. Exports SHALL use a selected snapshot, defaulting to the latest.

The mapping from tournament disciplines to HEMA Ratings categories SHALL be a per-tournament parameter keyed by **taxonomy code** — the weapon × gender × material classification derived per `discipline-identity` — and not by a discipline's identity. Several disciplines classified alike therefore share one mapping entry, one configured override, and one fetched rating per fencer; the system SHALL offer no way to map them to different categories. A snapshot SHALL fetch once per distinct taxonomy code among the tournament's individual disciplines, not once per discipline.

A discipline whose weapon lies outside the HEMA taxonomy derives a taxonomy code no category mapping recognizes. Such a discipline SHALL carry no rating category and SHALL be skipped by the snapshot without being reported as a failure — the same path as a taxonomy code for which the organizer has configured no keyword. Where the organizer configures such a discipline, the console SHALL state at the point of configuration that it will carry no ratings, rather than leaving its absence to be discovered at export time. Team disciplines carry no HR rating category, as before.

#### Scenario: Snapshot selection
- **WHEN** the organizer exports discipline sheets
- **THEN** HRating and HRank come from the chosen dated snapshot

#### Scenario: Tiers share one category and one fetch
- **WHEN** a tournament offers two longsword disciplines and a snapshot is taken for a fencer entered in both
- **THEN** one longsword rating is fetched and it applies to both disciplines, and the mapping offers a single longsword entry to configure

#### Scenario: Override cannot drift between tiers
- **WHEN** the organizer overrides the category keyword for longsword in a tournament offering two longsword disciplines
- **THEN** the override governs both, and no per-discipline override is offered

#### Scenario: Discipline outside the taxonomy carries no ratings
- **WHEN** a snapshot is taken for a tournament offering a discipline whose weapon is outside the taxonomy
- **THEN** that discipline contributes no ratings, the snapshot completes normally, and no failure is reported

#### Scenario: Absence of ratings stated up front
- **WHEN** the organizer sets a discipline's weapon to one the taxonomy does not name
- **THEN** the console states that the discipline will carry no HEMA Ratings figures

### Requirement: Canonical naming
The HR canonical name SHALL be the display name for HR-bound fencers; the
originally registered name SHALL be preserved alongside it.

A fencer becomes HR-bound by a verdict — an organizer's resolution, or an id the
fencer supplied — and not by the existence of a match proposal. While a match is
only proposed, the registered name, club and nationality SHALL remain the
fencer's as given, and the profile's SHALL be shown alongside them as the
evidence for the proposal rather than in their place.

#### Scenario: Name normalization
- **WHEN** an imported fencer is bound to an HR profile with a differently spelled name
- **THEN** the HR spelling becomes the display name and the original stays retrievable

#### Scenario: Proposal does not normalize
- **WHEN** a match is proposed for an imported fencer but no verdict has been reached
- **THEN** the fencer's registered name, club and nationality are unchanged, and the profile's appear beside them

### Requirement: Nationality-filtered similarity search
The fighters-index search SHALL support an optional nationality filter that restricts the candidate space before name matching, and SHALL rank name matches by text similarity (diacritics-insensitive). The system SHALL expose the list of nationalities present in the index for building the filter. Results SHALL include hr_id, canonical name, nationality, and club.

#### Scenario: Nationality narrows then name ranks
- **WHEN** a search runs with nationality "Czechia" and name query "pascenko"
- **THEN** only Czech fighters are considered and results are ordered by name similarity to the query, each with hr_id, name, nationality, and club

#### Scenario: No nationality given
- **WHEN** a search runs with a name query and no nationality filter
- **THEN** the whole index is searched and results are ranked by name similarity
