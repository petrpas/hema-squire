## MODIFIED Requirements

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

After the seating deadline the system SHALL NOT promote anyone automatically by any rule. The view presents the data; the organizer decides.

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

#### Scenario: No automatic promotion
- **WHEN** the seating deadline passes and seats are freed by demotion
- **THEN** no queued registration is promoted automatically, and every seat is filled by an explicit organizer action

### Requirement: Organizer-triggered seating settlement
The organizer SHALL be able to settle seating from the console before the seating deadline arrives — closing seating early once the roster is as they want it. It SHALL do exactly what the deadline does: demote every registration still owing money to the substitute queue, and place every subsequent registration in the queue rather than a seat.

A registration whose lifecycle clocks are dormant SHALL NOT be demoted, by the deadline or by the organizer, as fixed by `registration`'s **One dormancy predicate governs the lifecycle passes**. The two triggers SHALL leave the same registrations alone, since they are one operation reached two ways.

It SHALL be available in every payment mode. In immediate mode it demotes nobody but still closes seating. Where every registration is dormant it likewise demotes nobody and still closes seating.

The count the console states before firing SHALL be the set the settlement then moves. The two SHALL be one selection, so that a confirmation SHALL NOT promise a demotion that settlement will not carry out.

It SHALL be refused on a tournament whose seating has already settled, so settlement happens once however it is triggered.

It SHALL NOT be reversible, and the console SHALL confirm before firing it, stating how many registrations will be demoted and, where any of them carries a team, how many teams will be waitlisted with them. The organizer's route to correct an individual case afterwards is promotion.

The action SHALL live in the Queue phase's rail, beside the seating deadline and whether and when seating settled, so that the organizer settles with the rosters it will change in view. Once seating has settled the rail SHALL state when, and SHALL NOT offer the action.

#### Scenario: Organizer settles early
- **WHEN** the organizer settles seating a week before the seating deadline
- **THEN** every registration still owing money is demoted to the queue, and the tournament is recorded as settled

#### Scenario: Confirmation states the effect
- **WHEN** the organizer opens the settle action on a tournament with eleven unpaid seated registrations
- **THEN** the confirmation states that eleven registrations will be moved to the queue and that the action cannot be undone

#### Scenario: Teams counted in the confirmation
- **WHEN** four of the registrations settlement would demote carry one seated team each
- **THEN** the confirmation states the registrations and that four teams will be waitlisted with them

#### Scenario: Settled seating stated in the rail
- **WHEN** the organizer opens the Queue phase after seating settled
- **THEN** the rail states when it settled and offers no settle action

#### Scenario: The count excludes what settlement will not move
- **WHEN** the organizer opens the settle action on a tournament holding four unpaid seated registrations and six dormant ones
- **THEN** the confirmation states four, and settling then demotes exactly those four

#### Scenario: Settling twice refused
- **WHEN** the organizer attempts to settle a tournament whose seating has already settled
- **THEN** the action is refused and nothing changes

#### Scenario: Scheduled settlement does not follow a manual one
- **WHEN** the seating deadline passes on a tournament the organizer already settled by hand
- **THEN** no registration is demoted a second time, including any the organizer promoted in between

#### Scenario: Settling in immediate mode
- **WHEN** the organizer settles seating on an immediate-mode tournament
- **THEN** no registration is demoted and subsequent registrations join the queue

#### Scenario: Settling a tournament that asks for no money
- **WHEN** the organizer settles seating on a tournament whose payments feature is off
- **THEN** no registration is demoted, every seat is kept, and the tournament is recorded as settled
