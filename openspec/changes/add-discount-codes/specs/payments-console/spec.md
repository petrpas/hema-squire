## RENAMED Requirements

- FROM: `### Requirement: The phase is two tables behind two bands`
- TO: `### Requirement: The phase is a set of tables behind two bands`

## MODIFIED Requirements

### Requirement: The phase is a set of tables behind two bands
The Payments phase SHALL present the organizer's payment work as **two tables**
in the phase's main area, with the **discount codes table** beside them on a
tournament that has any code, reached through two tab bands: the first choosing
between the fencer table, the payments and the codes, the second — shown only while the
payments are chosen — choosing between **credited** and **uncredited** payments.
Each band SHALL carry the console's own tab idiom, and each payments tab SHALL
state its own count, so that work in a table nobody is looking at is still
visible. The fencer tab and the codes tab SHALL carry no count: these counts mean
outstanding work, and a roster size among them would read as more of it. The phase's rail
SHALL hold only the operation's parameters and the manual-edits log, as every
other phase's rail does.

Which table a payment belongs to SHALL be decided by **the credit journal** —
whether the payment holds a live credit — and not by the transaction's status. A
payment the matcher marked resolved while crediting nothing is uncredited money
and belongs with the work.

Each table SHALL load independently of the other and of the fencer table. A
table with nothing to show SHALL say so rather than disappear, and its tab SHALL
remain with its zero rather than being withdrawn.

The phase's sheet heading SHALL name the phase's own subject rather than the
fencer table's, as the Import phase's heading already does.

#### Scenario: Nothing outstanding
- **WHEN** the organizer opens the Payments phase on a tournament where nothing has been credited and nothing awaits resolution
- **THEN** both payments tabs show a count of zero, and whichever is opened states that it is empty in a single line

#### Scenario: The second band appears with the money
- **WHEN** the organizer chooses the payments in the first band
- **THEN** a second band appears beside it offering the credited and the uncredited payments, and the first band still offers the fencer table

#### Scenario: The fencer table gives way to whichever table is read
- **WHEN** the organizer opens either payments table
- **THEN** that table is what the phase shows, and returning to the fencer tab lists every registration with its payment state as before

#### Scenario: One table fails to load
- **WHEN** the request behind the uncredited payments fails while the other succeeds
- **THEN** that table reports its own failure, and the credited table and the fencer table still render their data

#### Scenario: The phase names itself
- **WHEN** the organizer opens the Payments phase
- **THEN** the sheet heading names the management of payments rather than the registered fencers

#### Scenario: No codes, no tab
- **WHEN** the organizer opens the Payments phase of a tournament with no discount code
- **THEN** the first band offers the fencer table and the payments, as it does without the feature

#### Scenario: The codes tab appears with the first code
- **WHEN** the tournament has a discount code
- **THEN** the first band offers the codes table as well, with no count, whether or not anyone has used one

## ADDED Requirements

### Requirement: The codes table says who holds what
The discount codes table SHALL list one row per live registration carrying a code, stating the fencer, the code's name and its code text, what the code deducted in the local currency, and whether the registration reads as paid. A line beside the tab band SHALL state, per code, its uses against its limit, an unlimited code stating its uses alone. A code nobody holds SHALL appear in that line and in no row.

The table SHALL load independently of the phase's other tables, SHALL require console access, and SHALL say so in a single line when nobody holds a code. Registrations that cancelled or expired SHALL NOT be listed, so that the rows always agree with the uses stated.

#### Scenario: Who used it
- **WHEN** three fencers registered with a code limited to 10
- **THEN** the table lists the three with what each was deducted, and the line states 3 / 10

#### Scenario: A cancellation leaves the table
- **WHEN** one of them cancels
- **THEN** the row disappears and the line states 2 / 10

#### Scenario: Nobody yet
- **WHEN** a tournament has codes and none has been used
- **THEN** the table says so in one line and the line beside the band states each at zero

#### Scenario: A revival past the limit
- **WHEN** a revival takes a single-use code to two holders
- **THEN** both are listed and the line states 2 / 1
