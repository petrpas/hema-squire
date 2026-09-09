## MODIFIED Requirements

### Requirement: Past tournaments tab
The Proběhlé turnaje tab SHALL list every published, non-cancelled tournament dated before today, ordered by date descending, whether or not the account was involved with it. Cards SHALL carry the same lines as an upcoming card — name, subtitle, bold date and place, organizers, per-discipline counts — and SHALL state the account's own registration state when it held one, or an organizer mark when it only organized. Selecting a past tournament SHALL open its detail in read-only mode.

The "today" that splits upcoming from held SHALL be **one global boundary, the UTC day**, and SHALL NOT be evaluated per tournament in that tournament's own zone. This list mixes tournaments from many zones and is answered by one comparison over all of them; the cost of an honest per-row boundary is a worse query, and its only effect is that a tournament held today stays under the upcoming tabs for the first hours of a morning east of UTC. This is a decision, not an oversight, and it is stated here so it is not read as one.

#### Scenario: Participated tournament listed
- **WHEN** a fencer opens the Past tab having had a paid registration for a tournament held last month
- **THEN** that tournament is listed with its data and its paid state, and opens in read-only detail when selected

#### Scenario: Unrelated past tournament listed too
- **WHEN** a past tournament exists where the fencer had no registration and is not its organizer
- **THEN** it is listed in the Past tab, with no registration state and no organizer mark

#### Scenario: Organized tournament marked
- **WHEN** an organizer opens the Past tab for a tournament they organized but did not fence in
- **THEN** the tournament is listed with an organizer mark and no registration state

#### Scenario: Never-published past tournament hidden
- **WHEN** a past tournament was never published
- **THEN** it does not appear in the Past tab for anyone, including its organizer

#### Scenario: The split is the same for every tournament
- **WHEN** two published tournaments held in different timezones share a date, and that date is yesterday in UTC
- **THEN** both appear in the Past tab, neither having waited for its own local midnight

#### Scenario: The split does not follow the deployment
- **WHEN** the Past tab is listed on a deployment whose process timezone is not UTC
- **THEN** the same tournaments are listed as on any other deployment
