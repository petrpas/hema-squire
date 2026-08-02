## MODIFIED Requirements

### Requirement: Section allocation to tabs
Every Setup settings section SHALL belong to exactly one tab, and no section SHALL be
dropped, duplicated, or split by this navigation:

- `TOURNAMENT` — the tournament's identity fields (display name, subtitle, logo, date,
  location, description, qualification statement, registration window, registration
  instructions) and the titular organizers.
- `DISCIPLINES` — the disciplines table and the team composition deadline.
- `EXTRA` — the extra-items table.
- `PAYMENTS` — the currency and exchange-rate section, the VS series statement, and the
  discount list.
- `OTHER` — console team access and the danger zone.
- `PUBLISH` — the publication state, the items blocking publication, and the publish
  action, as fixed by `tournament-publication`.

The team composition deadline SHALL sit below the disciplines table and SHALL be offered
only while at least one discipline row is of the team kind, including a row added in the
current unsaved draft. It SHALL be written by the `DISCIPLINES` tab's single save control
along with the table, and a deadline already stored on a tournament whose team
disciplines have all been removed SHALL be retained rather than cleared.

Within a tab, sections SHALL keep their existing relative order, except on
`TOURNAMENT`, where the identity fields follow the order fixed by `tournament-admin`.
Sections that are shown only to the tournament owner SHALL keep that restriction; when
a non-owner opens `OTHER` and it would therefore be empty, the tab SHALL NOT be
offered at all rather than opening onto nothing. `PUBLISH` SHALL be offered to every
account with console access.

#### Scenario: Every section reachable
- **WHEN** the organizer visits all six tabs
- **THEN** every settings section that existed before this change is present on exactly one of them

#### Scenario: Deadline appears with the first team row
- **WHEN** the organizer sets a discipline row's kind to team in an unsaved draft
- **THEN** the composition deadline field appears below the table, and saving the tab writes both the row and the deadline

#### Scenario: Deadline hidden without team disciplines
- **WHEN** the tournament offers only individual disciplines
- **THEN** no composition deadline field is shown on `DISCIPLINES`

#### Scenario: Stored deadline survives removing the team discipline
- **WHEN** the organizer removes the last team discipline from a tournament that had a composition deadline set
- **THEN** the field stops being shown and the stored deadline is not cleared

#### Scenario: Money settings together
- **WHEN** the organizer opens `PAYMENTS`
- **THEN** the currency and exchange rate, the VS series statement, and the discount list are shown together

#### Scenario: Non-owner sees no empty tab
- **WHEN** a console team member who is not the tournament owner opens Setup
- **THEN** the `OTHER` tab is not offered, and the remaining five tabs — including `PUBLISH` — behave as usual
