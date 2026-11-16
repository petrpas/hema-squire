## MODIFIED Requirements

### Requirement: Each tab states its own columns and order
Every tab but Summary and Revenue SHALL open with a **position** column numbering its rows
from 1 in the order they are displayed — after the tab's filter and in the tab's
own order. On a discipline tab the numbering SHALL run straight across the
capacity line, so the first fencer below it states how far past capacity they
stand; the line itself SHALL carry no number. On screen the position SHALL be drawn as the
table's gutter, as **Position in the list** (`etl-console`) draws it, with no heading; the
copy SHALL head it `Poř.` (`Pos.` in English), as the spreadsheet does.

The **Fencers** tab SHALL list, after the position, name, nationality, club, HEMA
Ratings identifier, disciplines and paid, in registration order.

An **individual discipline** tab SHALL list, after the position, name,
nationality, club, HEMA Ratings identifier, rating, rank and paid, ordered by
paid then registration order.

A **team discipline** tab SHALL list its teams, ordered by paid then the moment
the team entered, each team stating after the position its name and paid — the
standing of the registration it was entered on. The fencer who entered the team
SHALL be stated by a hint over the team's name, and not in the row; the team's
member count against the discipline's bounds SHALL NOT be stated on this tab,
since the roster beneath it shows who is on it. Each team's fighters
SHALL stand beneath it in roster order, each stating name, nationality, club,
HEMA Ratings identifier, rating and rank, and no paid of its own: a fighter holds
no registration, and a team is paid for once. The position column SHALL number
teams, not fighters, since the tab is read as a list of teams.

An **item category** tab SHALL list, after the position, name, nationality, club,
the items the fencer selected in that category with their quantities, and paid,
ordered by paid then registration order. It SHALL list only fencers holding a
selection in that category.

The **Summary** tab SHALL list the columns and rows `export-summary` fixes. It
carries no position column, because its order is the offer's and a number
stating a place in it would state nothing. The **Revenue** tab SHALL list the
columns and rows `export-revenue` fixes, without a position column for the same
reason.

A row a deletion has taken out of the table SHALL appear in no tab, as it appears
in no export.

The columns that state a number — the position, the HEMA Ratings identifier,
the rating and the rank — SHALL stand right-aligned with their digits in columns
under one another; every other column SHALL stand left-aligned.

Where a row is bound to a HEMA Ratings profile, its nationality and club SHALL be
stated as HEMA Ratings records them, over what the fencer gave; a value the
profile does not carry SHALL leave the fencer's own standing. A row with no
profile SHALL state what the fencer gave. The nationality SHALL be stated as its
ISO code in every case.

The paid column SHALL state the registration's settled state as yes or no and
nothing else — settled as `payment-ledger` derives it, from a live waiver or a
lane credited to within tolerance, never from a mark a reader could find
disagreeing with the money behind it. A registration settled short of its total
SHALL read as paid here;
what it still owes is stated in the Payments phase, which is where that shortfall
is worked. This narrows `payments`' rule that a settled registration short of its
total states the shortfall, and it is narrowed deliberately: these tables are
read by a check-in desk and consumed by a spreadsheet downstream, where a column
that is sometimes a word and sometimes a sum can be neither counted nor filtered.

#### Scenario: The fencers table is the whole tournament
- **WHEN** the organizer opens the Fencers tab
- **THEN** every fencer the tournament knows is listed in registration order with their disciplines and their paid mark

#### Scenario: HEMA Ratings speaks for a bound fencer
- **WHEN** a fencer who left the club blank is bound to a profile that records a club
- **THEN** every tab and the worksheet state the profile's club and its nationality code

#### Scenario: Rows are numbered as displayed
- **WHEN** the organizer switches a tab of thirty fencers, twenty of them paid, to active only
- **THEN** the position column reads 1 to 20 down the table

#### Scenario: The numbering runs across the line
- **WHEN** a discipline of capacity 24 has 24 seated fencers and 3 queued
- **THEN** the first fencer below the line is numbered 25 and the line has no number

#### Scenario: An item tab lists only its buyers
- **WHEN** four of thirty fencers ordered a T-shirt
- **THEN** the Merch tab lists those four and states which shirt each ordered

#### Scenario: Quantity is stated
- **WHEN** a fencer ordered two T-shirts
- **THEN** their row states the item with its quantity

#### Scenario: The summary has no position column
- **WHEN** the organizer opens the Summary tab
- **THEN** its first column is the item

#### Scenario: The revenue has no position column
- **WHEN** the organizer opens the Revenue tab
- **THEN** its first column names what each line prices

#### Scenario: A deleted row is in no tab
- **WHEN** a row is deleted on the Fencers phase and the organizer opens Export
- **THEN** it appears on no tab

#### Scenario: A tolerated shortfall reads as paid
- **WHEN** a registration is settled within tolerance for 50 less than its total
- **THEN** its paid column reads yes on every tab, and the shortfall is stated on Payments

#### Scenario: A registration owing nothing has not paid
- **WHEN** a fencer's entries all sit in a queue, so the registration is priced at zero and has been credited nothing
- **THEN** their paid column reads no on every tab

#### Scenario: A team tab reads as teams with their fighters
- **WHEN** the organizer opens the tab of a team discipline holding six teams of four
- **THEN** six numbered team rows are listed, each with its four fighters beneath it stating their ratings and ranks, and no fighter carries a paid cell

#### Scenario: A team row states only its name and paid
- **WHEN** the organizer opens a team tab whose team Wolves was entered by Petr Paščenko and names four of three to four
- **THEN** Wolves' row reads its number, Wolves and its paid, with no "entered by" and no member count in it

#### Scenario: Who entered a team is a hint
- **WHEN** the organizer points at Wolves' name on the team tab
- **THEN** a hint states that Petr Paščenko entered the team


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
empty. The entering fencer and the member count do not travel. The screen itself SHALL keep the team rows with their fighters beneath
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

## ADDED Requirements

### Requirement: A discipline tab states whose ratings are not fetched
A discipline tab, individual or team, SHALL state in its rail card, beside the
ratings refresh, when the ratings it shows were last fetched, and how many of its
fighters are bound to a HEMA Ratings identifier for which no snapshot holds a
fetch. A fighter bound after the latest snapshot — a team member matched or typed
in since — is one of them. Where none is missing, the card SHALL state the moment
alone; where no snapshot was ever taken, it SHALL say so in place of the moment.

The statement SHALL NOT fetch anything. Fetching stays the refresh's, which an
organizer starts.

A fighter whose fetched page holds no rating in the discipline's category is not
missing: HEMA Ratings was asked and has no rating for them, and the rating cell
stays empty.

#### Scenario: No snapshot yet
- **WHEN** the organizer opens a team tab whose 56 bound fighters have never had a snapshot taken
- **THEN** the card states that ratings have not been fetched yet and that 56 fighters wait for them, beside the refresh

#### Scenario: Members bound after the snapshot
- **WHEN** a snapshot was taken on 10 November and three team members were matched to profiles since
- **THEN** the card states the 10 November fetch and that 3 fighters have no fetched rating

#### Scenario: Everything fetched
- **WHEN** every bound fighter of the tab was in the latest snapshot
- **THEN** the card states only when the ratings were fetched

#### Scenario: Unrated in the category is not missing
- **WHEN** a fighter was in the latest snapshot but holds no sabre rating on HEMA Ratings
- **THEN** the fighter is not counted as missing and their rating cell is empty
