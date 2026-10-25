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

### Requirement: Default rating category mapping
Every taxonomy code SHALL have a default HEMA Ratings category, or none, that applies wherever the tournament configures no override for that code. A fighter's page lists only HEMA Ratings' official categories, so a default SHALL name an official category. The defaults SHALL follow these rules:

- **Open and Men** SHALL take the weapon's "Mixed & Men's" category.
- **Women** SHALL take the weapon's "Underrepresented Genders & Women's" category, not its "Women's" category. HSQ offers no gender of its own for underrepresented genders.
- **Knife, Messer, Smallsword, and Sidesword & Dagger** have HEMA Ratings categories only among the unofficial ones, which a fighter's page does not list. They SHALL have no default category in any gender or material.
- Every **plastic** code SHALL have no default category.

| Weapon | Open, Men | Women |
|---|---|---|
| LS | Mixed & Men's Steel Longsword | Underrepresented Genders & Women's Steel Longsword |
| SA | Mixed & Men's Steel Sabre | Underrepresented Genders & Women's Steel Sabre |
| RA | Mixed & Men's Steel Single Rapier | Underrepresented Genders and Women's Steel Single Rapier |
| RD | Mixed & Men's Steel Rapier and Dagger | Underrepresented Genders and Women's Steel Rapier and Dagger |
| SB | Mixed & Men's Steel Sword and Buckler | Underrepresented Genders & Women's Steel Sword and Buckler |
| SS | Mixed & Men's Steel Single Sidesword | Underrepresented Genders & Women's Steel Single Sidesword |
| ST | Mixed & Men's  Singlestick | Underrepresented Genders & Women's  Singlestick |
| KN, ME, SM, SD | none | none |

Where the organizer configures a discipline whose weapon is a taxonomy weapon with no default category in any gender (KN, ME, SM, SD), the console SHALL state at the point of configuration that the discipline will carry no ratings, as it does for a weapon outside the taxonomy.

A snapshot already stored SHALL keep the ratings it stored. A changed default SHALL take effect from the next refresh.

#### Scenario: Women read the URG category
- **WHEN** a snapshot is taken for a women's longsword discipline and the fencer's page lists both "Women's Steel Longsword" and "Underrepresented Genders & Women's Steel Longsword"
- **THEN** the stored rating and rank are the ones from "Underrepresented Genders & Women's Steel Longsword"

#### Scenario: Rapier and dagger rated
- **WHEN** a snapshot is taken for an open rapier & dagger discipline and the fencer's page lists "Mixed & Men's Steel Rapier and Dagger"
- **THEN** the fencer's rapier & dagger rating and rank are stored

#### Scenario: New official weapons rated
- **WHEN** a snapshot is taken for an open single sidesword discipline and a women's singlestick discipline
- **THEN** they read "Mixed & Men's Steel Single Sidesword" and "Underrepresented Genders & Women's  Singlestick"

#### Scenario: Side weapon unrated without failure
- **WHEN** a snapshot is taken for a Messer discipline with no override configured
- **THEN** that discipline contributes no ratings, the snapshot completes normally, and no failure is reported

#### Scenario: Side weapon's absence stated up front
- **WHEN** the organizer chooses Knife, Messer, Smallsword, or Sidesword & Dagger as a discipline's weapon
- **THEN** the console states that the discipline will carry no HEMA Ratings figures

#### Scenario: Plastic stays unrated
- **WHEN** a snapshot is taken for a plastic longsword discipline with no override configured
- **THEN** that discipline contributes no ratings and no failure is reported

#### Scenario: Earlier snapshot untouched
- **WHEN** a tournament holds a snapshot taken before this mapping took effect
- **THEN** that snapshot still states the ratings it stored, and only a refresh stores ratings read under the new mapping

### Requirement: Category matched by whole normalized name
A fencer's rating category SHALL be found by comparing the whole category name on the fighter's page with the category configured for the taxonomy code, whether that category is a default or an organizer's override. A configured name that appears only inside a longer category name SHALL NOT match. Before the comparison both names SHALL be normalized: a leading list dash (`- `, which the fighter page prints before every category under its weapon heading) is removed, `&` and the word `and` are treated as the same, runs of whitespace collapse to one space, leading and trailing whitespace is removed, and case is ignored. HEMA Ratings spells categories inconsistently ("& Women's" beside "and Women's", a doubled space in Singlestick), and the normalization makes those spellings match without letting one category match another. A weapon heading row (`Longsword`) SHALL match no configured category unless the configured category is that bare heading.

#### Scenario: Women's does not match the URG category
- **WHEN** the configured category is "Women's Steel Longsword" and the fencer's page lists only "Underrepresented Genders & Women's Steel Longsword"
- **THEN** no rating is stored for that code

#### Scenario: Ampersand and "and" match
- **WHEN** the configured category is "Mixed & Men's Steel Rapier & Dagger" and the fencer's page lists "Mixed & Men's Steel Rapier and Dagger"
- **THEN** the rating is stored

#### Scenario: Listed category matches through its dash
- **WHEN** the fencer's page lists "- Mixed & Men's Steel Longsword" under the heading "Longsword"
- **THEN** it matches the configured "Mixed & Men's Steel Longsword"

#### Scenario: Doubled space matches
- **WHEN** the fencer's page lists "Mixed & Men's  Singlestick" with two spaces and the configured category is "Mixed & Men's Singlestick"
- **THEN** the rating is stored

#### Scenario: Override matched the same way
- **WHEN** the organizer overrides longsword with "mixed & men's steel longsword" in lower case
- **THEN** it matches the page's "Mixed & Men's Steel Longsword", and does not match any longer category that contains it

