## MODIFIED Requirements

### Requirement: The rail states the destination as a link
Where the tournament has a stored destination, the Export phase's rail SHALL state it as a
link that opens the spreadsheet. The export control, the link, the control that forgets
the destination and the JSON download SHALL stand on one row, in that order, each as an
icon whose word is its accessible name and whose hint says what it does. The card holding
them SHALL be headed **Export all** (`Exportovat vše`). The English tick SHALL stand above
this card and the open tab's card, not in either (`export-tables`).

Every control of the card SHALL carry a hint saying what it does, opened by hovering or
focusing the control itself, and the card SHALL carry no standing paragraph explaining
them.

While an export is running the link SHALL be withdrawn, and SHALL return when the run
concludes. The withdrawal is how a run states that it is a run: the export has no progress
to report and no interruption to offer, so the one honest signal of "working, then done" is
the destination going away and coming back. It SHALL return on failure as well as on
success — the spreadsheet is still where it is — with the failure stated separately.

#### Scenario: A stored destination is a link on arrival
- **WHEN** the organizer opens the Export phase on a tournament that has a destination
- **THEN** the rail states it as a link, before any export has been run in this visit

#### Scenario: The link withdraws for the run
- **WHEN** the organizer presses export
- **THEN** the link is absent while the export runs and present again once it concludes

#### Scenario: A failed run still leaves the link
- **WHEN** an export fails
- **THEN** the failure is stated and the destination is stated as a link beside it
