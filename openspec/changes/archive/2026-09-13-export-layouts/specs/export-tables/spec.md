## MODIFIED Requirements

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

The band SHALL stand on the line of the phase's title where both fit, and SHALL be as long as its tabs and end at its last tab. It SHALL NOT
draw an empty stretch of frame after it. Where the tabs are wider than the
screen, the band SHALL be one full-width strip that scrolls, as every other tab
band in the console is, and the selected tab SHALL be kept visible in it.

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

#### Scenario: The band stands beside the title
- **WHEN** the organizer opens the Export phase on a wide screen
- **THEN** the band is on the same line as the tables' title, after it

#### Scenario: The band ends at its last tab
- **WHEN** a tournament with three tabs is exported on a wide screen
- **THEN** the band's frame ends at the third tab

### Requirement: Each tab states its own columns and order
Every tab SHALL open with a **position** column, headed `#`, numbering its rows
from 1 in the order they are displayed — after the tab's filter and in the tab's
own order. On a discipline tab the numbering SHALL run straight across the
capacity line, so the first fencer below it states how far past capacity they
stand; the line itself SHALL carry no number.

The **Fencers** tab SHALL list, after the position, name, nationality, club, HEMA
Ratings identifier, disciplines and paid, in registration order.

A **discipline** tab SHALL list, after the position, name, nationality, club, HEMA
Ratings identifier, rating, rank and paid, ordered by paid then registration
order.

An **item category** tab SHALL list, after the position, name, nationality, club,
the items the fencer selected in that category with their quantities, and paid,
ordered by paid then registration order. It SHALL list only fencers holding a
selection in that category.

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

#### Scenario: A deleted row is in no tab
- **WHEN** a row is deleted on the Fencers phase and the organizer opens Export
- **THEN** it appears on no tab

#### Scenario: A tolerated shortfall reads as paid
- **WHEN** a registration is settled within tolerance for 50 less than its total
- **THEN** its paid column reads yes on every tab, and the shortfall is stated on Payments

#### Scenario: A registration owing nothing has not paid
- **WHEN** a fencer's entries all sit in a queue, so the registration is priced at zero and has been credited nothing
- **THEN** their paid column reads no on every tab

### Requirement: A table leaves by the clipboard
Every tab SHALL offer a copy action putting the table on the clipboard as
tab-separated values with a header row, in the order and with the filter on
screen, so it pastes into a spreadsheet as the columns it is.

Marker and layout SHALL NOT travel: the capacity line does not, and a manual-edit
marking does not. What travels is the values. The position column SHALL travel
as the first column, numbering the copied rows as they were numbered on screen,
because the order it states — a seeding position, a place past capacity — is a
value the reader keeps. The spreadsheet write SHALL NOT carry it.

#### Scenario: A tab is pasted into a spreadsheet
- **WHEN** the organizer copies the Fencers tab and pastes into a spreadsheet
- **THEN** the columns land in their own cells under their own headers, the first headed #

#### Scenario: The copy follows the filter
- **WHEN** the organizer copies a tab switched to active only
- **THEN** only the active rows are copied, numbered from 1

#### Scenario: The spreadsheet has no position column
- **WHEN** the organizer writes the export to the organizer's spreadsheet
- **THEN** no worksheet carries the position column

### Requirement: Every tab filters to the paid
Each tab SHALL offer a switch between all rows and active rows only. Active SHALL
mean the registration is settled — whether Squire collected the money or the
organizer waived the price by hand — so that the switch answers the same question
on a tournament whose payments Squire does not handle. A registration credited
nothing and waived by nobody SHALL NOT be active, whatever it owes.

On an item tab the switch SHALL narrow the tab's own population: those who
ordered the item **and** paid.

The switch SHALL filter and nothing else: it SHALL NOT change the order a tab
lists its rows in.

The switch SHALL hold one value for the whole band. Moving between tabs SHALL
keep it, so that an organizer who has narrowed to the paid keeps reading the paid
on every tab they open.

#### Scenario: The switch narrows to the paid
- **WHEN** twenty of thirty fencers have paid and the organizer switches the Fencers tab to active only
- **THEN** twenty rows are listed

#### Scenario: A hand-marked registration is active
- **WHEN** the tournament's payments are handled outside Squire and the organizer has marked a registration paid by hand
- **THEN** that registration is listed under active only

#### Scenario: A reversed credit takes a row off the active list
- **WHEN** the organizer reverses the credited transaction that had settled a registration
- **THEN** the next read of any tab lists that registration under all rows and not under active only

#### Scenario: The switch holds across tabs
- **WHEN** the organizer switches the Merch tab to active only and moves to the Fencers tab
- **THEN** the Fencers tab lists only the paid, and its switch is on

#### Scenario: An item tab narrows twice
- **WHEN** four fencers ordered a T-shirt and two of them have paid, and the organizer switches the Merch tab to active only
- **THEN** those two are listed

### Requirement: A discipline tab is a seeding roster
A discipline tab SHALL offer, beside its active-only switch, a tick ordering its
fencers by rating, highest first — the seeding order — rather than by
registration. The tick SHALL be independent of the switch: either may be on
without the other, so that the organizer can see the seeding of everybody
entered or of the paid alone. A fencer with no rating SHALL sort last, in
registration order among their like. The tick SHALL be offered on a discipline
tab only, since no other tab has a rating to order by, and SHALL hold one value
across every discipline tab, as the active-only switch holds across the band.

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

#### Scenario: The seeding order orders by rating
- **WHEN** the organizer ticks the seeding order on a discipline tab
- **THEN** the highest-rated fencer is first and the lowest last

#### Scenario: The seeding order does not filter
- **WHEN** the organizer ticks the seeding order with active only off
- **THEN** unpaid fencers are listed too, in their places by rating

#### Scenario: Active only does not reorder
- **WHEN** the organizer switches a discipline tab to active only without the seeding order
- **THEN** the paid fencers are listed in registration order

#### Scenario: An unrated fencer sorts last
- **WHEN** one fencer in that discipline has no rating and the seeding order is ticked
- **THEN** they are listed after every rated fencer

#### Scenario: The queue is below the line
- **WHEN** a discipline with capacity 16 has 16 seated fencers and 3 holding substitute entries
- **THEN** the 16 are above the line in the tab's current order and the 3 below it in queue order

#### Scenario: A highly rated substitute stays below
- **WHEN** one of those 3 has the highest rating in the discipline and the seeding order is ticked
- **THEN** they are still below the line

#### Scenario: No queue, only a capacity mark
- **WHEN** a tournament whose conduct creates no substitute placements has 20 fencers in a discipline of capacity 16
- **THEN** the line falls after the 16th row, states that it marks capacity rather than a queue, and no fencer is marked as queued

#### Scenario: The line does not leave the screen
- **WHEN** the organizer copies a discipline tab holding a queue
- **THEN** the copied rows are every fencer in the displayed order and carry no line

#### Scenario: Other tabs offer no seeding order
- **WHEN** the organizer opens the Fencers tab or an item tab
- **THEN** no seeding order tick is offered

## ADDED Requirements

### Requirement: Every tab states how many it lists
Every tab SHALL state, beside its name, how many rows it lists.

A **discipline** tab SHALL state two numbers: the fencers holding a seated entry
in the discipline, then the fencers holding a substitute entry in it, joined as
`24 + 3`. Where nobody holds a substitute entry, the second number and its `+`
SHALL be left out. That is always the case on a tournament whose conduct creates
no substitute placements. The seated number SHALL be stated even when it is
zero, because a discipline with nobody entered is something the organizer needs
to see.

The **Fencers** tab and each **item category** tab SHALL state one number: the
rows the tab lists.

The counts SHALL be of the tab's whole population, as the tab lists it with the
active-only switch off, and a row a deletion took out of the table SHALL count
nowhere. The switch SHALL NOT change a count. The count states how large the tab
is, and a number that changed with a per-tab switch would make two tabs
incomparable at a glance.

The counts SHALL follow the tournament's rows. A registration entered, deleted,
restored or moved in or out of a queue SHALL be reflected in the band on the
next read, without the organizer reopening the phase.

#### Scenario: A discipline states its seated fencers and its queue
- **WHEN** Sabre Open has 24 fencers holding a seated entry and 3 holding a substitute entry
- **THEN** its tab reads SABRE OPEN 24 + 3

#### Scenario: An empty queue is not stated
- **WHEN** Longsword has 16 seated fencers and nobody queued
- **THEN** its tab reads LONGSWORD 16, with no + 0

#### Scenario: The Fencers and item tabs state one number
- **WHEN** a tournament knows 41 fencers and 7 of them have borrowed equipment
- **THEN** the Fencers tab reads 41 and the rental tab reads 7

#### Scenario: The switch does not change the count
- **WHEN** 20 of Sabre Open's 24 seated fencers have paid and the organizer switches that tab to active only
- **THEN** the tab still reads 24 + 3

#### Scenario: A deleted row is not counted
- **WHEN** the organizer deletes one of the 41 rows on the Fencers phase and opens Export
- **THEN** the Fencers tab reads 40

### Requirement: A tab's controls are the phase's operations
Above its table, the Export phase SHALL show only the band. The controls acting on
the open tab SHALL be offered in the phase's operations rail, as every other
phase offers its operations there:
- the active-only switch,
- on a discipline tab, the seeding order tick,
- the copy action,
- on a discipline tab, the HR ratings refresh with its statement that it refreshes
  the whole tournament.

These controls SHALL be grouped in one card headed by the open tab's name, so
that the organizer can see which table a switch or a copy acts on without looking
back at the band. The card SHALL follow the selected tab: moving to another tab
SHALL keep the switch and the seeding order as they were, and SHALL offer the
seeding order and the ratings refresh only where that tab is a discipline.

The English tick SHALL sit with the spreadsheet write and the JSON download,
because it governs what leaves the phase by the clipboard and by the spreadsheet
alike, not what one tab shows.

The outcome of a copy or a ratings refresh SHALL be stated in the card that
offered it.

#### Scenario: Nothing but the band above the table
- **WHEN** the organizer opens the Export phase
- **THEN** no switch, tick or button stands between the band and the table

#### Scenario: The card names the tab it acts on
- **WHEN** the organizer opens the Merch tab
- **THEN** the rail holds a card headed Merch with the active-only switch and the copy action, and neither the seeding order nor the ratings refresh

#### Scenario: The card follows the tab
- **WHEN** the organizer switches Merch to active only and opens the Sabre Open tab
- **THEN** the card is headed Sabre Open, its switch is still on, and it offers the seeding order and the ratings refresh

#### Scenario: The seeding order holds across disciplines
- **WHEN** the organizer ticks the seeding order on Sabre Open, opens Merch and then Longsword
- **THEN** Merch offers no seeding order, and Longsword is listed in seeding order with the tick on

#### Scenario: A copy reports where it was asked
- **WHEN** the organizer copies a tab from the rail card
- **THEN** the card states how many rows were copied
