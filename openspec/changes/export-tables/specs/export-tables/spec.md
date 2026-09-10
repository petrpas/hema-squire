## ADDED Requirements

### Requirement: The Export phase is a band of tables
The Export phase SHALL replace the single fencer table with a band of tabs, each
tab one table. The band SHALL be derived from the tournament rather than fixed:
a **Fencers** tab first, then one tab per individual discipline in the
tournament's discipline order, then one tab per extra-item category for which
the tournament offers at least one item, goods categories before programme
categories.

A category the tournament offers nothing in SHALL have no tab, and a category
the tournament does offer SHALL have one whatever it is — a tournament selling
parking or running a seminar SHALL be exported as completely as one selling
T-shirts. A team discipline SHALL have no tab, for the reason it produces no
worksheet: its entries are teams, not registrations, and there is no roster of
individuals to seed.

The selected tab SHALL be kept visible in a band that scrolls, as every other
tab band in the console is.

#### Scenario: Tabs follow what the tournament offers
- **WHEN** a tournament offering two individual disciplines, a rental and a merch item is exported
- **THEN** the band holds Fencers, the two disciplines, Rentals and Merch, and no afterparty or seminar tab

#### Scenario: A category with no items has no tab
- **WHEN** the same tournament has no afterparty item
- **THEN** no afterparty tab is shown, and the tournament's export is complete without one

#### Scenario: An unnamed category is not omitted
- **WHEN** a tournament offers a seminar and an item in the "other goods" category
- **THEN** each has a tab of its own

#### Scenario: A team discipline is not a tab
- **WHEN** a tournament offers one individual and one team longsword discipline
- **THEN** only the individual discipline has a tab

### Requirement: Each tab states its own columns and order
The **Fencers** tab SHALL list name, nationality, club, HEMA Ratings identifier,
disciplines and paid, in registration order.

A **discipline** tab SHALL list name, nationality, club, HEMA Ratings identifier,
rating, rank and paid, ordered by paid then registration order.

An **item category** tab SHALL list name, nationality, club, the items the fencer
selected in that category with their quantities, and paid, ordered by paid then
registration order. It SHALL list only fencers holding a selection in that
category.

A row a deletion has taken out of the table SHALL appear in no tab, as it appears
in no export.

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

#### Scenario: An item tab lists only its buyers
- **WHEN** four of thirty fencers ordered a T-shirt
- **THEN** the Merch tab lists those four and states which shirt each ordered

#### Scenario: Quantity is stated
- **WHEN** a fencer ordered two T-shirts
- **THEN** their row states the item with its quantity

#### Scenario: A deleted row is in no tab
- **WHEN** a row is deleted on the Fencers phase and the organizer opens Export
- **THEN** it appears on no tab

#### Scenario: A tolerated shortfall reads as paid
- **WHEN** a registration is settled within tolerance for 50 less than its total
- **THEN** its paid column reads yes on every tab, and the shortfall is stated on Payments

#### Scenario: A registration owing nothing has not paid
- **WHEN** a fencer's entries all sit in a queue, so the registration is priced at zero and has been credited nothing
- **THEN** their paid column reads no on every tab

### Requirement: Every tab filters to the paid
Each tab SHALL offer a switch between all rows and active rows only. Active SHALL
mean the registration is settled — whether Squire collected the money or the
organizer waived the price by hand — so that the switch answers the same question
on a tournament whose payments Squire does not handle. A registration credited
nothing and waived by nobody SHALL NOT be active, whatever it owes.

On an item tab the switch SHALL narrow the tab's own population: those who
ordered the item **and** paid.

Each tab SHALL hold its own switch state. Moving between tabs SHALL NOT carry a
selection across, because the tabs answer different questions.

#### Scenario: The switch narrows to the paid
- **WHEN** twenty of thirty fencers have paid and the organizer switches the Fencers tab to active only
- **THEN** twenty rows are listed

#### Scenario: A hand-marked registration is active
- **WHEN** the tournament's payments are handled outside Squire and the organizer has marked a registration paid by hand
- **THEN** that registration is listed under active only

#### Scenario: A reversed credit takes a row off the active list
- **WHEN** the organizer reverses the credited transaction that had settled a registration
- **THEN** the next read of any tab lists that registration under all rows and not under active only

#### Scenario: The switch is per tab
- **WHEN** the organizer switches the Merch tab to active only and moves to the Fencers tab
- **THEN** the Fencers tab still lists everybody

#### Scenario: An item tab narrows twice
- **WHEN** four fencers ordered a T-shirt and two of them have paid, and the organizer switches the Merch tab to active only
- **THEN** those two are listed

### Requirement: A discipline tab is a seeding roster
Switched to active only, a discipline tab SHALL order its fencers by rating,
highest first — the seeding order — rather than by registration. A fencer with no
rating SHALL sort last, in registration order among their like.

The tab SHALL draw one line at the discipline's capacity. Fencers holding a
seated entry SHALL be above it; fencers holding a substitute entry in that
discipline SHALL be below it whatever the sort key says, in the queue order
`seating-queue` fixes.

Where the tournament's conduct creates no substitute placements, no fencer SHALL
be marked as queued and the line SHALL mark only where capacity falls in the
current order. The line SHALL state which of the two it is, so that a reader is
never left to infer it from a setting they may not know about.

The line SHALL be a marking within one table, not a split into two. What leaves
the tab — copied or written to a spreadsheet — SHALL carry every fencer in one
block in the displayed order and SHALL NOT carry the line.

#### Scenario: Active only seeds by rating
- **WHEN** the organizer switches a discipline tab to active only
- **THEN** the highest-rated paid fencer is first and the lowest last

#### Scenario: An unrated fencer sorts last
- **WHEN** one paid fencer in that discipline has no rating
- **THEN** they are listed after every rated fencer

#### Scenario: The queue is below the line
- **WHEN** a discipline with capacity 16 has 16 seated fencers and 3 holding substitute entries
- **THEN** the 16 are above the line in seeding order and the 3 below it in queue order

#### Scenario: A highly rated substitute stays below
- **WHEN** one of those 3 has the highest rating in the discipline
- **THEN** they are still below the line

#### Scenario: No queue, only a capacity mark
- **WHEN** a tournament whose conduct creates no substitute placements has 20 fencers in a discipline of capacity 16
- **THEN** the line falls after the 16th row, states that it marks capacity rather than a queue, and no fencer is marked as queued

#### Scenario: The line does not leave the screen
- **WHEN** the organizer copies a discipline tab holding a queue
- **THEN** the copied rows are every fencer in the displayed order and carry no line

### Requirement: The rating is the organizer's to correct
The rating cell of a discipline tab SHALL be editable. A typed rating SHALL
persist as a rule replayed over the projection, keyed to the row and the
discipline, so a fencer entered in two disciplines carries two independent
corrections.

The typed rating SHALL be the rating every reader gets: the tab's order, the
capacity line, and the spreadsheet export alike. A ratings refresh SHALL NOT
overwrite it — a refresh stores what HEMA Ratings currently says, and the
correction is replayed over that, so the correction stands until it is removed.
Removing it SHALL expose the fetched value again, as removing any rule exposes
what it covered.

A corrected rating SHALL be marked as an organizer's edit wherever it is shown,
by the same marking every other manual edit carries, and SHALL appear in the
phase's manual-edits log with its discipline named.

Rank SHALL NOT be editable. It states what HEMA Ratings says, and an overridden
rating standing beside an unchanged rank is the intended reading: the correction
is the organizer's, the rank is the register's.

#### Scenario: A typed rating stands
- **WHEN** the organizer types a rating into a discipline tab and reloads the console
- **THEN** the typed rating is shown, marked as a manual edit

#### Scenario: A refresh does not overwrite it
- **WHEN** the organizer refreshes ratings after typing one
- **THEN** the typed rating is still shown and every other fencer's rating is the freshly fetched one

#### Scenario: Removing the correction exposes the fetch
- **WHEN** the organizer removes that edit from the manual-edits log
- **THEN** the cell states the fetched rating again

#### Scenario: The correction reaches the order and the line
- **WHEN** a typed rating puts a fencer above another
- **THEN** the active-only order lists them in that order

#### Scenario: Two disciplines, two corrections
- **WHEN** a fencer entered in longsword and rapier has their longsword rating corrected
- **THEN** their rapier rating is unchanged

#### Scenario: Rank is not editable
- **WHEN** the organizer clicks a rank cell
- **THEN** no edit opens

### Requirement: A table leaves by the clipboard
Every tab SHALL offer a copy action putting the table on the clipboard as
tab-separated values with a header row, in the order and with the filter on
screen, so it pastes into a spreadsheet as the columns it is.

Marker and layout SHALL NOT travel: the capacity line does not, and a manual-edit
marking does not. What travels is the values.

#### Scenario: A tab is pasted into a spreadsheet
- **WHEN** the organizer copies the Fencers tab and pastes into a spreadsheet
- **THEN** the columns land in their own cells under their own headers

#### Scenario: The copy follows the filter
- **WHEN** the organizer copies a tab switched to active only
- **THEN** only the active rows are copied

### Requirement: A table can leave in English
The Export phase SHALL offer a tick rendering what leaves it in English: the
copied values and the worksheets written to the organizer's spreadsheet, headers
and yes/no values alike. The table on screen SHALL stay in the organizer's own
language, because the table is also where they work.

The tick SHALL be offered only to an organizer whose interface language is not
already English, where it would change nothing.

#### Scenario: An English copy from a Czech console
- **WHEN** a Czech-speaking organizer ticks the English option and copies the Fencers tab
- **THEN** the pasted header reads Name, Nat., Club and the paid column reads Yes and No

#### Scenario: The screen is not switched
- **WHEN** the same organizer ticks it
- **THEN** the table on screen is still in Czech

#### Scenario: Not offered where it would do nothing
- **WHEN** an organizer whose interface is English opens the Export phase
- **THEN** no such tick is shown
