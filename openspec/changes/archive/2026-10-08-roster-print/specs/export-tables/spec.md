## MODIFIED Requirements

### Requirement: A tab's controls are the phase's operations
Above its table, the Export phase SHALL show only the band. The controls acting on
the open tab SHALL be offered in the phase's operations rail, as every other
phase offers its operations there:
- the active-only switch, on every tab but Summary and Revenue,
- on a discipline tab, the seeding order tick,
- the copy action,
- on a discipline tab, the HR ratings refresh, and the PDF and PNG actions
  (`roster-print`).

The copy, the ratings refresh, the PDF and the PNG SHALL stand in one row as
icons, in that order — the copy a copy icon, the refresh a refresh icon, the
others their format — each named by its word for assistive technology and
carrying a hint that opens on hovering or focusing it and says what pressing it
does, as the actions of the export card do. The ratings refresh's hint SHALL say
that it refreshes the whole tournament, not the open discipline alone. Neither
the copy nor the refresh SHALL be a text button.

These controls SHALL be grouped in one card headed by the open tab's name, so
that the organizer can see which table a switch or a copy acts on without looking
back at the band. The card SHALL follow the selected tab: moving to another tab
SHALL keep the switch and the seeding order as they were, and SHALL offer the
seeding order, the ratings refresh and the PDF and PNG only where that tab is a
discipline.

The English tick SHALL stand in the rail above both cards — the open tab's and
the export card, headed **Export all** (`Exportovat vše`) — because it governs
what leaves the phase by the copy, the printouts and the spreadsheet alike, not
what one tab shows. The **Include finances** tick (`export-revenue`) SHALL sit in
the export card, because it governs what the spreadsheet write carries.

The outcome of a copy or a ratings refresh SHALL be stated in the card that
offered it.

#### Scenario: Nothing but the band above the table
- **WHEN** the organizer opens the Export phase
- **THEN** no switch, tick or button stands between the band and the table

#### Scenario: The card names the tab it acts on
- **WHEN** the organizer opens the Merch tab
- **THEN** the rail holds a card headed Merch with the active-only switch and the copy action, and neither the seeding order, the ratings refresh, nor the PDF and PNG actions

#### Scenario: The card follows the tab
- **WHEN** the organizer switches Merch to active only and opens the Sabre Open tab
- **THEN** the card is headed Sabre Open, its switch is still on, and it offers the seeding order and the ratings refresh

#### Scenario: The seeding order holds across disciplines
- **WHEN** the organizer ticks the seeding order on Sabre Open, opens Merch and then Longsword
- **THEN** Merch offers no seeding order, and Longsword is listed in seeding order with the tick on

#### Scenario: The summary card offers the copy alone
- **WHEN** the organizer opens the Summary tab
- **THEN** the rail holds a card headed Summary with the copy action and no switch, tick or refresh

#### Scenario: The revenue card offers the copy alone
- **WHEN** the organizer opens the Revenue tab
- **THEN** the rail holds a card headed Revenue with the copy action and no switch, tick or refresh

#### Scenario: The copy is an icon with a hint
- **WHEN** the organizer hovers or focuses the copy action on any tab
- **THEN** it is a copy icon, and a hint opens beside it saying it copies the table to the clipboard

#### Scenario: A discipline's actions in one row
- **WHEN** the organizer opens the Sabre Open tab
- **THEN** the copy, the ratings refresh, the PDF and the PNG stand in one row of icons in that order, each with its hint, and the refresh's hint says it refreshes the whole tournament

#### Scenario: The English tick stands above both cards
- **WHEN** a Czech-speaking organizer opens the Export phase
- **THEN** the English tick stands in the rail above the open tab's card and the card headed Export all, and is in neither

#### Scenario: The finances tick stays with the spreadsheet write
- **WHEN** a Czech-speaking organizer opens the Export phase
- **THEN** the card headed Export all holds Include finances, unticked

#### Scenario: A copy reports where it was asked
- **WHEN** the organizer copies a tab from the rail card
- **THEN** the card states how many rows were copied
