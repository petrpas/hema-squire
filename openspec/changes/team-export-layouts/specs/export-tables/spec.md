## MODIFIED Requirements

### Requirement: A table leaves by the clipboard
Every tab SHALL offer a copy action putting the table on the clipboard as
tab-separated values with a header row, in the order and with the filter on
screen, so it pastes into a spreadsheet as the columns it is.

Marker and layout SHALL NOT travel: the capacity line does not, and a manual-edit
marking does not. What travels is the values. The position column SHALL travel
as the first column, numbering the copied rows as they were numbered on screen,
because the order it states — a seeding position, a place past capacity — is a
value the reader keeps. The spreadsheet write carries a position column of its
own, numbering the worksheet as `data-export` fixes.

A **team discipline** tab SHALL be copied flat, in the columns its worksheet
carries (`data-export`, A team discipline's worksheet is flat): one row per
fighter, in the tab's order of teams and each team's roster order, each row
stating its team's number as the position, the team's name, the fighter's name,
nationality, club, HEMA Ratings identifier, rating and rank, and the team's paid.
The team's number, name and paid SHALL be repeated on every one of its rows, so
that a pasted copy sorts and filters without parting a fighter from their team.
A team with no fighter on its roster SHALL be one row with the fighter cells
empty. The entering fencer and the member count do not travel; they are the
screen's. The screen itself SHALL keep the team rows with their fighters beneath
them that `Each tab states its own columns and order` fixes.

#### Scenario: A tab is pasted into a spreadsheet
- **WHEN** the organizer copies the Fencers tab and pastes into a spreadsheet
- **THEN** the columns land in their own cells under their own headers, the first headed `Poř.`

#### Scenario: The copy follows the filter
- **WHEN** the organizer copies a tab switched to active only
- **THEN** only the active rows are copied, numbered from 1

#### Scenario: The spreadsheet numbers its own rows
- **WHEN** the organizer writes the export to the organizer's spreadsheet
- **THEN** each worksheet but Summary and Revenue opens with a position column headed `Poř.`, numbered as `data-export` fixes

#### Scenario: A team tab is copied flat
- **WHEN** the organizer copies a team discipline tab listing Wolves with four fighters and Bears with three
- **THEN** the clipboard holds a header and seven rows, the first four stating 1, Wolves and Wolves' paid, the last three stating 2, Bears and Bears' paid, each with its own fighter

#### Scenario: A team copy carries no console facts
- **WHEN** the organizer copies a team discipline tab
- **THEN** no cell states the fencer who entered a team or its member count against the bounds

#### Scenario: A team copy follows the filter
- **WHEN** the organizer switches a team tab to active only, where one of its two teams has not paid, and copies it
- **THEN** only the paid team's fighters are copied, numbered 1
