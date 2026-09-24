## MODIFIED Requirements

### Requirement: The substitute queue holds no money
A substitute placement SHALL owe nothing. Substitute placements SHALL NOT be priced, SHALL NOT be billed, and SHALL NOT be offered payment instructions, whatever else the registration carrying them holds. Money SHALL be requested for a queued placement only when the organizer promotes it.

This is what keeps the queue free of money that would otherwise need refunding for a seat that never existed. It is a property of the **placement**, not of the registration: a registration may hold a seated placement it owes for and a queued placement it does not, and the money follows the placement in each case.

Four consequences follow and SHALL hold:

- Queue length and queue position SHALL be counted from substitute placements on **live** registrations — those reserved within their validity window, and those paid — rather than from the registration's state. A registration that has paid for a seated placement SHALL still be counted, at the place its queue moment gives it, for a placement it holds in the queue. Counting from reserved registrations alone would drop a paid fencer out of the queue they are waiting in and hand their position to somebody else.
- A registration holding a substitute placement SHALL NOT expire on a lapsed payment window; it is demoted instead, as `registration` fixes. Money owed for a seat SHALL NOT cost the fencer a queue place they never owed for.
- Money arriving on a registration sitting entirely in the queue SHALL NOT be credited to it **while it sits there**. Where the tournament lets paying substitutes take free places (`tournament-admin`), such a registration MAY be told what it would owe — its claim — and a payment of it SHALL seat the registration before it is credited, as **A paying substitute takes free places** fixes; the money is never credited to a registration that holds no seat. It SHALL be held for the organizer's decision, as `payments` fixes under **Payments arriving on a queued registration**, and a registration sitting entirely in the queue SHALL NOT read as paid whatever it has been credited, as `payment-ledger` fixes. Money it already held when it was moved there — a forfeited deposit — stays recorded against it and counts on promotion.
- Returning a placement to the queue SHALL be refused once the registration has been paid. Demoting a seat that has been paid for would leave money in the queue, and the organizer's route for a paid registration is cancellation, which carries the existing refund handling.

#### Scenario: Queued registration owes nothing
- **WHEN** a fencer's registration is entirely substitute placements
- **THEN** its total is zero, no payment instructions are available to it, and no reminder is sent

#### Scenario: Queued placement on a billed registration still owes nothing
- **WHEN** a registration holds one seated placement and one queued placement
- **THEN** its total covers the seated placement alone, and the queued placement adds nothing to what is owed

#### Scenario: Money requested on promotion
- **WHEN** the organizer promotes a queued registration
- **THEN** its total is computed for the promoted placements, a payment window opens, and payment instructions are sent

#### Scenario: A paid fencer keeps their queue position
- **WHEN** a fencer who has paid for a seated placement also holds a queued placement, and a second fencer registered later holds a queued placement in the same discipline
- **THEN** the paid fencer is counted in that discipline's queue length and ranks ahead of the later fencer by queue moment

#### Scenario: Paid registration cannot be returned to the queue
- **WHEN** the organizer attempts to return a paid registration to the queue
- **THEN** the action is refused with a message directing them to cancellation, and the registration keeps its seat

#### Scenario: Money sent from the queue is not credited
- **WHEN** a transaction carrying the VS of a registration sitting entirely in the queue arrives
- **THEN** it is not credited, the registration stays unpaid and in the queue, and the transaction awaits the organizer's decision

### Requirement: Queue view for the organizer
The organizer SHALL have a view of the substitute queue as a **band of rosters**, one tab per individual discipline in the tournament's discipline order, each tab labelled and counted as the Export phase labels and counts its discipline tabs. Each roster SHALL list the same fencers, in the same order and with the same line, as the Export roster of that discipline in its own order: seated fencers above the line, queued fencers below it in queue order. The two views SHALL be drawn from one ordering, so that the line cannot fall in one place here and another there. The view SHALL NOT offer the seeding order or the active-only switch: it is read in the tab's own order, and the unpaid are the fencers it exists for.

Each row SHALL state the fencer, their club, their rating as the Export roster states it (not editable here), and:
- on a seated row, the money: paid, settled by hand, or what is owed with the date by which it is due, or that nothing is due where no window runs;
- on a queued row, its position and its **queue moment**.

The **queue moment** of a placement is the moment its place in the queue counts from: the registration time for a placement queued at registration, and the moment of demotion for one moved there for non-payment. Each entry's queue moment SHALL be stated as a day and a clock time together, on the 24-hour scale to the minute, read in the tournament's own zone — never as a day alone. The queue is ordered by that moment, and two fencers on either side of the line can share a day; the view SHALL show what it is ordering by, and SHALL say which of the two the moment is, so that a fencer demoted at settlement is legibly behind one who registered later.

The view SHALL state each discipline's free places, so the organizer can see how many promotions are available.

The view's row actions SHALL be two, and SHALL be its only row actions: **promote** (↑) on a queued row and **return to the queue** (↓) on a seated row. Each SHALL be offered only where the server would carry it out — promotion while the discipline has a free place, return while the registration is unpaid — and a row whose registration would be refused SHALL NOT carry the arrow. A row with no registration behind it SHALL carry neither arrow and SHALL say that it holds no seat yet. An action refused all the same — another organizer acting first — SHALL be reported in words naming why, never as the server's code.

After an action the view SHALL re-read the roster, the band's counts and the discipline's free places, and the console's other readers of the money SHALL be told the tournament changed.

A discipline nobody is queued in SHALL still have its tab, its roster stating its seated fencers with no line drawn below them.

After the seating deadline the system SHALL NOT promote anyone automatically by any rule over the queue. The view presents the data; the organizer decides. The one exception is a fencer's own payment where the tournament lets paying substitutes take free places (**A paying substitute takes free places**); it is triggered by the fencer, not by the queue's order.

A queued row whose payment is being held SHALL state it, so that the organizer sees who has already paid for a place they are waiting for.

#### Scenario: Queue listed in order
- **WHEN** the organizer opens the Queue tab of a discipline with four waiting fencers
- **THEN** all four are listed below the line in queue order with their positions and queue moments, and the discipline's free places are stated

#### Scenario: The same line as Export
- **WHEN** the organizer compares a discipline's Queue roster with its Export roster in the tab's own order
- **THEN** the same fencers stand above and below the line, in the same order

#### Scenario: Two entries registered on one day
- **WHEN** two of the queued fencers registered on the same day, minutes apart
- **THEN** their entries state different clock times, and the order they are listed in is legible from those times

#### Scenario: A demoted fencer is legibly at the end
- **WHEN** a fencer who registered early was demoted at settlement and sits behind a substitute who registered later
- **THEN** their entry states the moment of demotion and that it is one, so the order is legible

#### Scenario: Money stated on the seated
- **WHEN** a discipline holds one paid fencer and one who owes 1750 by the 12th
- **THEN** the first row states paid and the second states 1750 owed by the 12th

#### Scenario: No arrow the server would refuse
- **WHEN** a discipline is full and a seated fencer has paid
- **THEN** no queued row carries a promote arrow and the paid row carries no return arrow

#### Scenario: A refusal in words
- **WHEN** another organizer fills the last free place a moment before this one presses promote
- **THEN** the refusal states that the discipline is full, not a code

#### Scenario: A discipline with nobody queued
- **WHEN** a discipline has no substitutes
- **THEN** its tab is present and lists its seated fencers with no queue below them

#### Scenario: A held payment stated
- **WHEN** a queued fencer's payment is held for the organizer
- **THEN** their row states that a payment is held

#### Scenario: No automatic promotion
- **WHEN** the seating deadline passes on a tournament that does not let paying substitutes take places, and seats are freed by demotion
- **THEN** no queued registration is promoted automatically, and every seat is filled by an explicit organizer action

## ADDED Requirements

### Requirement: A paying substitute takes free places
Where the tournament lets paying substitutes take free places, a registration that sits wholly in the queue — at least one individual placement, every one of them queued — and whose lifecycle clocks run SHALL have a **claim**: what it would owe with every one of its queued individual placements seated, less what it has already been credited. The claim SHALL be computed with the registration's frozen prices and stored in each currency the tournament prices in, beside its totals and recomputed with them, so that every surface and every QR code states one stored amount. Its waitlisted teams SHALL NOT be part of it and SHALL stay waitlisted.

A payment on such a registration SHALL seat it when both hold at the moment it is evaluated: its amount matches the claim in its lane within the tournament's tolerance, and every discipline the registration waits for has a free place. Then every queued individual placement SHALL be seated together, the registration SHALL be repriced, the payment SHALL be credited, and the fencer SHALL be told they have a place and that the payment was received. The seating SHALL be recorded under its own audit event, distinct from an organizer's promotion.

The payment SHALL seat everything the registration waits for or nothing: a registration waiting for two disciplines of which one has a free place SHALL NOT be seated in that one by its payment. This is the participation condition applied to what was paid for.

A payment that does not seat the registration SHALL be held, as `payments` fixes. A held payment whose amount matched the claim and whose only obstacle was a discipline without a free place SHALL be re-evaluated on every matching pass and SHALL seat the registration when the places free. Where several held payments wait for the same place, the one whose payment arrived first SHALL be seated first.

The organizer's actions SHALL stand beside this: they may promote any fencer, return any unpaid one, or refund a held payment, at any time, and no pass SHALL undo what they did.

A registration whose clocks are dormant SHALL have no claim, SHALL be offered no instructions, and SHALL NOT be seated by a payment.

#### Scenario: Payment seats a waiting fencer
- **WHEN** paying substitutes may take places, a fencer waiting for Longsword pays their claim of 1750, and Longsword has a free place
- **THEN** they are seated, credited, and told they have a place

#### Scenario: Payment into a full discipline waits
- **WHEN** the same payment arrives while Longsword is full
- **THEN** it is held, the fencer is told it is held, and they stay in the queue

#### Scenario: A held payment seats itself when a place frees
- **WHEN** a place in Longsword frees and the next matching pass runs
- **THEN** the fencer whose held payment arrived first is seated and credited

#### Scenario: Everything or nothing
- **WHEN** a fencer waiting for Longsword and Sabre pays their claim while only Longsword has a free place
- **THEN** they are not seated in Longsword, and the payment is held

#### Scenario: Forfeited deposit counts toward the claim
- **WHEN** a registration demoted at settlement holding a 500 deposit waits for a place priced 1750
- **THEN** its claim is 1250

#### Scenario: A dormant registration has no claim
- **WHEN** a hand-entered registration waits in the queue on a tournament that lets paying substitutes take places
- **THEN** it is offered no instructions, and a payment on it is held for the organizer
