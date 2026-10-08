## MODIFIED Requirements

### Requirement: Finances reach the spreadsheet only by a tick
The export card SHALL offer a checkbox **Include finances** (`Zahrnout finance`)
under its row of actions. The English tick stands above the card, not in it
(`export-tables`). It SHALL be offered to every organizer, whatever
their language, and SHALL be off whenever the Export phase is opened. It SHALL
NOT be stored.

The Sheets export SHALL write the `Revenue` worksheet only when the tick is on.
When the tick is off, the export SHALL NOT write, clear or delete a `Revenue`
worksheet the spreadsheet already holds, and the card SHALL state, under the
tick, that a revenue worksheet from an earlier export is left as it was.

The tick SHALL govern the spreadsheet alone: the Revenue tab, its copy and the
JSON download SHALL be the same whether it is on or off.

#### Scenario: Off by default
- **WHEN** the organizer opens the Export phase and writes to Sheets without touching the tick
- **THEN** no Revenue worksheet is written, and the export reports the worksheets it did write without Revenue

#### Scenario: Ticked
- **WHEN** the organizer ticks Include finances and writes to Sheets
- **THEN** the Revenue worksheet is written whole

#### Scenario: An earlier revenue worksheet is left alone
- **WHEN** the spreadsheet holds a Revenue worksheet from an earlier export and the organizer writes to Sheets with the tick off
- **THEN** that worksheet still holds what it held

#### Scenario: Not remembered
- **WHEN** the organizer exported with the tick on, left Export and came back
- **THEN** the tick is off

#### Scenario: Offered in English too
- **WHEN** an organizer working in English opens the export card
- **THEN** no English tick is shown, and the Include finances tick is
