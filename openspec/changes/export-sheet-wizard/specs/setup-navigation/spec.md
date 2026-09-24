## MODIFIED Requirements

### Requirement: Section allocation to tabs
Every Setup settings section SHALL belong to exactly one tab, and no section SHALL be
dropped, duplicated, or split by this navigation:

- `TOURNAMENT` — the tournament's identity fields (display name, subtitle, logo, date,
  city, address, description, qualification statement, registration instructions) and the
  titular organizers.
- `DISCIPLINES` — the disciplines table.
- `EXTRA` — the extra-items table.
- `TIMELINE` — every date that governs the tournament as a whole: when registration
  opens, the seating deadline, when registration closes, and the team composition
  deadline.
- `PAYMENTS` — how fencers pay (the payment mode, the deposit, the payment window and
  the reminder day), the bank account payments are collected into, the currency and
  exchange-rate section, the VS series statement, the discount list, and — only while
  the tournament still carries them — the legacy fixed fees.
- `OTHER` — the tournament mode, console team access, and the danger zone.
- `PUBLISH` — the publication state, the items blocking publication, and the publish
  action, as fixed by `tournament-publication`.

The payment-mode section SHALL stand first on `PAYMENTS`, before the bank account the
money arrives in; the bank account SHALL keep its place ahead of the currency it is
denominated in.

**A section whose feature is off SHALL NOT be shown**, as fixed by `tournament-features`,
and its stored values SHALL be retained rather than cleared. On `PAYMENTS` this SHALL
divide the tab: while payments are off, the tab — then titled `PRICING` — SHALL hold the
currency and exchange-rate section, the discount list, and any legacy fixed fees the
tournament still carries, and SHALL NOT hold the payment mode, the deposit, the payment
window, the reminder day, the bank account or the VS series statement. On `TIMELINE` the
seating deadline SHALL be offered only while payments are on, since nothing settles
against it when no money is owed. The mode section on `OTHER` SHALL be shown in every
mode, because it is the way back.

**One field, one editor.** A field that governs whether a tournament may be published
SHALL be offered in exactly one place, so that an organizer reading it in Setup is
reading the value the publication check reads. This SHALL hold for the bank account, the
deposit amount, and the legacy fixed fees alike. No tournament parameter SHALL be offered
in the console's phase panels. A feature turned off SHALL NOT move a field to a second
editor: it removes the one editor there is, and the item it governs is reported on
`PUBLISH` naming the feature that restores it.

**A tool's destination is not a tournament parameter.** A value that only says where one
console tool puts its output — governing no rule, gating no publication, read by nothing
but the tool itself — SHALL be configured with that tool in its phase panel rather than in
Setup, and SHALL then not appear in Setup at all. The export sheet address is such a
value, and is fixed there by `data-export`. This is the only exception to the paragraph
above, and it does not weaken it: the field still has exactly one editor.

The team composition deadline SHALL sit on `TIMELINE` in its chronological place, and
SHALL be offered only while the team disciplines feature is on and at least one
discipline row is of the team kind, including a row added in the current unsaved draft on
`DISCIPLINES`. A deadline already stored on a tournament whose team disciplines have all
been removed, or whose team feature has been turned off, SHALL be retained rather than
cleared.

The registration window — when registration opens and closes — SHALL sit on `TIMELINE`
in every mode. The tournament's own date SHALL remain editable on `TOURNAMENT` and SHALL
appear on `TIMELINE` read-only, as the anchor the other dates run towards.

Within a tab, sections SHALL keep their existing relative order, except on
`TOURNAMENT`, where the identity fields follow the order fixed by `tournament-admin`.
Sections that are shown only to the tournament owner SHALL keep that restriction; when
a non-owner opens `OTHER` and it would therefore be empty, the tab SHALL NOT be
offered at all rather than opening onto nothing. `PUBLISH` SHALL be offered to every
account with console access.

#### Scenario: Every section reachable
- **WHEN** the organizer of a tournament with every feature enabled visits all seven tabs
- **THEN** every settings section the tournament has is present on exactly one of them, and every tournament parameter is present on one of them

#### Scenario: Deadline appears with the first team row
- **WHEN** the organizer of a tournament with the team feature on sets a discipline row's kind to team in an unsaved draft on `DISCIPLINES`
- **THEN** the composition deadline field appears in its place on `TIMELINE`

#### Scenario: Deadline hidden without team disciplines
- **WHEN** the tournament offers only individual disciplines
- **THEN** no composition deadline field is shown on `TIMELINE`

#### Scenario: Stored deadline survives removing the team discipline
- **WHEN** the organizer removes the last team discipline from a tournament that had a composition deadline set
- **THEN** the field stops being shown and the stored deadline is not cleared

#### Scenario: Money settings together
- **WHEN** the organizer of a payments-enabled tournament opens `PAYMENTS`
- **THEN** how fencers pay, the bank account, the currency and exchange rate, the VS series statement, and the discount list are shown together, with the payment mode first and the bank account ahead of the currency

#### Scenario: Pricing tab holds only what survives payments being off
- **WHEN** the organizer of a payments-off tournament opens `PRICING`
- **THEN** it holds the currency and exchange-rate section and the discount list, and offers no payment mode, deposit, payment window, reminder day, bank account or VS series statement

#### Scenario: Seating deadline follows the payments feature
- **WHEN** the organizer turns payments off on a tournament with a seating deadline set
- **THEN** `TIMELINE` stops offering the seating deadline, the stored date is unchanged, and registration opens and closes are still offered

#### Scenario: Mode section always on OTHER
- **WHEN** the tournament owner opens `OTHER` on a tournament with no feature enabled
- **THEN** the tournament mode section is present alongside the console team and the danger zone

#### Scenario: Bank account has one editor
- **WHEN** the organizer looks for the bank account in the console's payments-phase panels
- **THEN** it is not offered there, and `PAYMENTS` in Setup is the only place it can be edited

#### Scenario: Deposit has one editor
- **WHEN** the organizer looks for the deposit amount in the console's payments-phase panels
- **THEN** it is not offered there, and `PAYMENTS` in Setup is the only place it can be edited

#### Scenario: Tournament date is shown but not edited on the timeline
- **WHEN** the organizer opens `TIMELINE`
- **THEN** the tournament date is shown as the timeline's anchor with no field to change it, and `TOURNAMENT` remains the only place it can be edited

#### Scenario: Non-owner sees no empty tab
- **WHEN** a console team member who is not the tournament owner opens Setup
- **THEN** the `OTHER` tab is not offered, and the remaining tabs its mode allows — including `PUBLISH` — behave as usual

#### Scenario: The export address is not in Setup
- **WHEN** the organizer of a published tournament visits every Setup tab
- **THEN** none of them offers the export sheet address, and `OTHER` carries the mode section, console team access and the danger zone

#### Scenario: The exception is narrow
- **WHEN** the organizer looks in a console phase panel for any tournament parameter other than the export sheet address
- **THEN** it is not offered there, and its one editor is in Setup
