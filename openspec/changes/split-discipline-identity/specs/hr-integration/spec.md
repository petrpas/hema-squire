## MODIFIED Requirements

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
