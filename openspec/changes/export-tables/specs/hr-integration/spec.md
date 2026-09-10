## MODIFIED Requirements

### Requirement: Ratings snapshots
The system SHALL fetch weighted rating and rank per fencer per discipline as dated snapshots. Exports SHALL use a selected snapshot, defaulting to the latest, **as corrected by the ratings an organizer has typed** (`export-tables`): a snapshot states what HEMA Ratings says, and a correction is replayed over it, so a refresh SHALL NOT overwrite a typed rating.

A refresh SHALL fetch a fighter's page at most once per run, whatever the tournament's disciplines, and SHALL parse it once. A refresh SHALL be startable from a discipline's export table, where the ratings being read are; it refreshes the tournament rather than that discipline, and SHALL say so, since a fighter page carries every category at once and narrowing the fetch to one discipline would save no request.

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

#### Scenario: A typed rating survives a refresh
- **WHEN** the organizer has corrected a fencer's longsword rating and then refreshes ratings
- **THEN** the snapshot stores the fetched value, the export tables and the spreadsheet still state the corrected one, and every other fencer's rating is the freshly fetched one

#### Scenario: One fetch per fighter per run
- **WHEN** a snapshot is taken for a tournament offering longsword, rapier and sabre disciplines for a fencer entered in all three
- **THEN** that fencer's page is fetched once and parsed once, and the three ratings are read from that one parse

#### Scenario: A refresh started from a discipline refreshes the tournament
- **WHEN** the organizer starts a refresh from the rapier export table
- **THEN** every individual discipline's ratings are refreshed and the action states that it refreshes the tournament
