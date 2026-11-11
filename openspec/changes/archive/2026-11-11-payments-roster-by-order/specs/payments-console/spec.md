## ADDED Requirements

### Requirement: The registration table states what each order holds
The Payments phase's registration table SHALL carry a **Contents** column
("Obsah" / "Contents") that states in a few words what each registration is billed
for. Only what is billed SHALL be counted: a placement in a queue is not.

The statement SHALL be composed from the order's billed lines, in this order:
- teams: one team is named. Two or more are counted ("2 týmy").
- individual disciplines: each is named by its short name.
- extra items: counted as a sum of their quantities ("3 položky").

The parts SHALL be joined by a middle dot. A part with nothing in it SHALL be left
out. A row that is billed for nothing SHALL read as absent, in the table's idiom
for a cell with nothing to state.

The column SHALL be present on the Payments phase whether or not Squire handles
the tournament's payments, because what an order holds is a fact either way.

#### Scenario: One team
- **WHEN** a registration entered the team "Hema Praha" and nothing else
- **THEN** its Contents cell reads the team's name

#### Scenario: A mixed order
- **WHEN** a registration entered two teams and the individual longsword discipline, and bought three weapon rentals
- **THEN** its Contents cell reads "2 týmy · LS · 3 položky"

#### Scenario: A queued team is not counted
- **WHEN** a registration entered two teams and one of them is waitlisted
- **THEN** its Contents cell names the one seated team, as it would for an order of one team

### Requirement: Every order unfolds into its priced lines
Every row of the Payments registration table that is billed for something SHALL
unfold in place, from its Contents cell, into the lines its total is made of. It
SHALL use the idiom the Teams console uses to unfold a roster. Rows SHALL be
unfoldable whatever the number of their lines, so that the table reads the same
way on every row.

The lines SHALL be:
- one line per individual discipline entered, at its price
- one line per team entered, naming the team and its discipline, at the
  discipline's per-team price
- one line per extra item, with its quantity where it is more than one and the
  sum for that quantity. On a tournament priced the legacy way, the flat rental
  and afterparty fees are stated as such lines.
- one negative line per discount, and one for a discount code, stating what it
  took

The lines SHALL be stated in the tournament's local currency. That is EUR on a
tournament whose local currency is EUR, and the local currency on a tournament that
also accepts EUR. The local price is what the order was itemised at.

The extra items SHALL be stated as the order's own, not divided among its teams.
An item belongs to the registration that bought it.

#### Scenario: Unfolding a mixed order
- **WHEN** the organizer unfolds a registration that entered teams A and B in sabre, the individual longsword, three weapon rentals and the afterparty, and that was granted a club discount
- **THEN** the lines read team A with its price, team B with its price, longsword with its price, the rentals ×3 with their sum, the afterparty with its price, and the discount as a negative amount

#### Scenario: Every row unfolds
- **WHEN** a registration holds a single team and nothing else
- **THEN** its row still unfolds, into that one line

#### Scenario: EUR-local tournament
- **WHEN** the tournament's local currency is EUR
- **THEN** every line is stated in EUR

### Requirement: Queued placements are shown and not counted
A placement that is in a queue, whether a substitute discipline entry or a
waitlisted team, SHALL appear among the unfolded lines of its order with the price
it would carry. It SHALL be greyed and set in italic so that it reads as not
counted, and it SHALL NOT enter the Contents summary, the sum of the lines or the
difference line. Extra items of an order whose every placement is queued are not
billed, and SHALL be shown the same way.

#### Scenario: A waitlisted team among the lines
- **WHEN** the organizer unfolds a registration whose second team is waitlisted
- **THEN** the waitlisted team's line is greyed and italic, and the lines that are counted sum to the order's total

### Requirement: A difference to the issued total is stated, not hidden
The lines SHALL be priced at the prices that stand now. Where they do not sum to
the order's issued total, because a price was changed after the order was issued,
the unfolded order SHALL end with a line stating the difference to the issued
total. The issued total SHALL stay what it is: changing a price after issuing is
the organizer's act, and the organizer settles the difference with the tools that
exist for it (a waiver, a recorded payment, an amendment). Where the lines and the
total agree, no such line SHALL be shown.

#### Scenario: A price changed after issuing
- **WHEN** a registration was issued with three rentals at 150 each and the organizer has since changed the rental price to 200
- **THEN** the rentals line reads 600 at the price that stands now, and a closing line states the difference of 150 against the issued total, which is unchanged

#### Scenario: Nothing changed
- **WHEN** the lines sum to the issued total
- **THEN** no difference line is shown

## MODIFIED Requirements

### Requirement: The phase is a set of tables behind two bands
The Payments phase SHALL present the organizer's payment work as **two tables**
in the phase's main area, with the **discount codes table** beside them on a
tournament that has any code, reached through two tab bands: the first choosing
between the registration table, the payments and the codes, the second — shown only while the
payments are chosen — choosing between **credited** and **uncredited** payments.
Each band SHALL carry the console's own tab idiom, and each payments tab SHALL
state its own count, so that work in a table nobody is looking at is still
visible. The registration tab and the codes tab SHALL carry no count: these counts mean
outstanding work, and a roster size among them would read as more of it. The registration tab SHALL be labelled as the registrations ("Registrace" / "Registrations"), not as the fencers: the table it opens lists orders, and on a team tournament many of its rows belong to holders who do not fight. The phase's rail
SHALL hold only the operation's parameters and the manual-edits log, as every
other phase's rail does.

Which table a payment belongs to SHALL be decided by **the credit journal** —
whether the payment holds a live credit — and not by the transaction's status. A
payment the matcher marked resolved while crediting nothing is uncredited money
and belongs with the work.

Each table SHALL load independently of the other and of the registration table. A
table with nothing to show SHALL say so rather than disappear, and its tab SHALL
remain with its zero rather than being withdrawn.

The phase's sheet heading SHALL name the phase's own subject rather than the
fencer table's, as the Import phase's heading already does.

#### Scenario: Nothing outstanding
- **WHEN** the organizer opens the Payments phase on a tournament where nothing has been credited and nothing awaits resolution
- **THEN** both payments tabs show a count of zero, and whichever is opened states that it is empty in a single line

#### Scenario: The second band appears with the money
- **WHEN** the organizer chooses the payments in the first band
- **THEN** a second band appears beside it offering the credited and the uncredited payments, and the first band still offers the registration table

#### Scenario: The fencer table gives way to whichever table is read
- **WHEN** the organizer opens either payments table
- **THEN** that table is what the phase shows, and returning to the registration tab lists every registration with its payment state as before

#### Scenario: One table fails to load
- **WHEN** the request behind the uncredited payments fails while the other succeeds
- **THEN** that table reports its own failure, and the credited table and the registration table still render their data

#### Scenario: The phase names itself
- **WHEN** the organizer opens the Payments phase
- **THEN** the sheet heading names the management of payments rather than the registered fencers

#### Scenario: No codes, no tab
- **WHEN** the organizer opens the Payments phase of a tournament with no discount code
- **THEN** the first band offers the registration table and the payments, as it does without the feature

#### Scenario: The codes tab appears with the first code
- **WHEN** the tournament has a discount code
- **THEN** the first band offers the codes table as well, with no count, whether or not anyone has used one

#### Scenario: The first tab names registrations
- **WHEN** the organizer opens the Payments phase
- **THEN** the first tab of the first band reads "Registrace" in Czech and "Registrations" in English
