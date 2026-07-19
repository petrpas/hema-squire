## ADDED Requirements

### Requirement: Nationality-filtered similarity search
The fighters-index search SHALL support an optional nationality filter that restricts the candidate space before name matching, and SHALL rank name matches by text similarity (diacritics-insensitive). The system SHALL expose the list of nationalities present in the index for building the filter. Results SHALL include hr_id, canonical name, nationality, and club.

#### Scenario: Nationality narrows then name ranks
- **WHEN** a search runs with nationality "Czechia" and name query "pascenko"
- **THEN** only Czech fighters are considered and results are ordered by name similarity to the query, each with hr_id, name, nationality, and club

#### Scenario: No nationality given
- **WHEN** a search runs with a name query and no nationality filter
- **THEN** the whole index is searched and results are ranked by name similarity
