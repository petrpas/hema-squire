## MODIFIED Requirements

### Requirement: The Export phase is a band of tables
The Export phase SHALL replace the single fencer table with a band of tabs, each
tab one table. The band SHALL be derived from the tournament rather than fixed:
a **Fencers** tab first, then one tab per discipline — individual and team
alike — in the tournament's discipline order, then one tab per extra-item category for which
the tournament offers at least one item, goods categories before programme
categories, then a **Summary** tab, whose table `export-summary` fixes, and
last a **Revenue** tab, whose table `export-revenue` fixes. Every tournament
has both.

A category the tournament offers nothing in SHALL have no tab, and a category
the tournament does offer SHALL have one whatever it is — a tournament selling
parking or running a seminar SHALL be exported as completely as one selling
T-shirts. A **team** discipline SHALL have a tab on the same terms as an
individual one: its fighters carry ratings, and rating and rank are stated on a
discipline tab and nowhere else, so a team discipline's fighters would otherwise
have their ratings fetched with nothing to show them. What that tab holds is
teams rather than registrations, which **Each tab states its own columns and
order** fixes.

The band SHALL stand on the line of the phase's title where both fit, and SHALL be as long as its tabs and end at its last tab. It SHALL NOT
draw an empty stretch of frame after it. Where the tabs are wider than the
screen, the band SHALL be one full-width strip that scrolls, as every other tab
band in the console is, and the selected tab SHALL be kept visible in it.

#### Scenario: Tabs follow what the tournament offers
- **WHEN** a tournament offering two individual disciplines, a rental and a merch item is exported
- **THEN** the band holds Fencers, the two disciplines, Rentals, Merch, Summary and Revenue, and no afterparty or seminar tab

#### Scenario: A category with no items has no tab
- **WHEN** the same tournament has no afterparty item
- **THEN** no afterparty tab is shown, and the tournament's export is complete without one

#### Scenario: An unnamed category is not omitted
- **WHEN** a tournament offers a seminar and an item in the "other goods" category
- **THEN** each has a tab of its own

#### Scenario: A team discipline is not a tab
- **WHEN** a tournament offers one individual and one team longsword discipline
- **THEN** each has a tab of its own — this scenario's answer is reversed by this change, and its heading is kept because a modified requirement replaces its whole block and may drop nothing

#### Scenario: Summary and Revenue close the band
- **WHEN** a tournament offering one discipline and nothing else is exported
- **THEN** the band holds Fencers, the discipline, Summary and Revenue, in that order

#### Scenario: The band stands beside the title
- **WHEN** the organizer opens the Export phase on a wide screen
- **THEN** the band is on the same line as the tables' title, after it

#### Scenario: The band ends at its last tab
- **WHEN** a tournament with four tabs is exported on a wide screen
- **THEN** the band's frame ends at the fourth tab, which is Revenue

### Requirement: Each tab states its own columns and order
Every tab but Summary and Revenue SHALL open with a **position** column, headed `#`, numbering its rows
from 1 in the order they are displayed — after the tab's filter and in the tab's
own order. On a discipline tab the numbering SHALL run straight across the
capacity line, so the first fencer below it states how far past capacity they
stand; the line itself SHALL carry no number.

The **Fencers** tab SHALL list, after the position, name, nationality, club, HEMA
Ratings identifier, disciplines and paid, in registration order.

An **individual discipline** tab SHALL list, after the position, name,
nationality, club, HEMA Ratings identifier, rating, rank and paid, ordered by
paid then registration order.

A **team discipline** tab SHALL list its teams, ordered by paid then the moment
the team entered, each team stating after the position its name, the fencer who
entered it, its member count against the discipline's minimum and maximum, and
paid — the standing of the registration it was entered on. Each team's fighters
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

### Requirement: A discipline tab is a seeding roster
An individual discipline tab SHALL offer, beside its active-only switch, a tick
ordering its fencers by rating, highest first — the seeding order — rather than by
registration. A **team** discipline tab SHALL NOT offer it: a team has no rating
to order by, and what a tournament makes of its fighters' ratings when it seeds is
the tournament's decision and not Squire's. The tab states the fighters' ratings
and the organizer seeds with them. The tick SHALL be independent of the switch: either may be on
without the other, so that the organizer can see the seeding of everybody
entered or of the paid alone. A fencer with no rating SHALL sort last, in
registration order among their like. The tick SHALL be offered on a discipline
tab only, since no other tab has a rating to order by, and SHALL hold one value
across every discipline tab, as the active-only switch holds across the band.

A team discipline tab SHALL draw its line at the discipline's capacity in teams,
with waitlisted teams below it in waitlist order, as the public team roster draws
it (`public-entrants`); the paragraphs below govern an individual tab.

The tab SHALL draw one line at the discipline's capacity. Fencers holding a
seated entry SHALL be above it; fencers holding a substitute entry in that
discipline SHALL be below it whatever the sort key says, in the queue order
`seating-queue` fixes.

Where the tournament's conduct creates no substitute placements, no fencer SHALL
be marked as queued and the line SHALL mark where capacity falls in the tab's
own order — paid first, then registration order. The seeding order SHALL NOT
move a fencer across that line: it orders the fencers above it among
themselves, and those below it keep the tab's own order, as a queue does. The line SHALL state which of the two it is, so that a reader is
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

#### Scenario: Seeding does not cross the capacity mark
- **WHEN** a tournament whose conduct creates no substitute placements has 44 paid fencers in a discipline of capacity 42 and the organizer ticks the seeding order
- **THEN** the first 42 in the tab's own order stay above the line, ordered by rating, and the other 2 stay below it in registration order however they rate

#### Scenario: The line does not leave the screen
- **WHEN** the organizer copies a discipline tab holding a queue
- **THEN** the copied rows are every fencer in the displayed order and carry no line

#### Scenario: Other tabs offer no seeding order
- **WHEN** the organizer opens the Fencers tab or an item tab
- **THEN** no seeding order tick is offered

#### Scenario: No seeding tick on a team tab
- **WHEN** the organizer opens a team discipline's tab
- **THEN** no seeding tick is offered, and the active-only switch is
