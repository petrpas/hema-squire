# seating-queue Specification

## Purpose
Define the substitute queue as the tournament's holding area once seating has
settled: that a queued registration holds no money, how the organizer promotes a
queued registration into a free seat and returns a seated one to the queue, how
the organizer settles seating by hand ahead of the deadline, and what the
organizer sees when reading a queue.
## Requirements
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

### Requirement: Organizer promotion from the queue
The organizer SHALL be able to promote a queued registration into a seat, one discipline at a time, whenever that discipline has a free place. Promotion SHALL mark the placement as seated, compute what is now owed, open a payment window, and send payment instructions.

Promotion SHALL be available whatever the registration has already paid. A registration that has settled its seated placements and still holds a queued one SHALL be promotable, and promotion SHALL bill the **difference** its new placement adds rather than a fresh total: what the fencer has already paid stands, and a registration that has paid in full does not revert to being unpaid because it gained a placement. This follows the same rule an amendment does when it adds a priced row to a paid registration.

The notice a promotion sends SHALL name the discipline whose place has opened, state the amount now due rather than the registration's total, and state the date by which it is due. A fencer who has already paid once SHALL NOT be sent a demand that reads as though nothing had been paid.

**WHEN the tournament's payments feature is off, promotion SHALL seat the placement and stop there**: no payment window SHALL open, no due date SHALL be set, and no payment instructions SHALL be sent. The promoted fencer SHALL be notified that they have a place, and the amount their registration comes to SHALL be stated as information. A promotion that opens no window cannot lapse, so such a registration SHALL never return to the queue on a clock; it stays seated until the organizer returns it.

The payment window opened by promotion SHALL NOT outlive the tournament: it SHALL be the configured payment window or the remainder of the time until the tournament date, whichever is shorter.

Promotion SHALL re-evaluate at once every transaction flagged because it arrived while the registration sat entirely in the queue, before the promotion notice is composed, so that money the fencer already sent is credited against the seat it now pays for and the notice states what is still due after it. A promotion whose held money covers what the placement adds SHALL leave the registration paid, and its notice SHALL say so rather than ask for payment.

Promotion SHALL be refused when the discipline has no free place, and when the registration is in a state that cannot hold a seat — cancelled or expired. Having been paid SHALL NOT be such a state.

**A lapsed promotion window SHALL take back only what the promotion seated.** Promotion SHALL record, on each placement and team it seats, that it was seated by a promotion not yet paid for; the record SHALL be cleared once the registration reads as settled. When the payment window a promotion opened lapses unpaid — before or after seating settles — the placements and teams so recorded SHALL return to the queue, at the **end**, the registration SHALL be repriced, and every placement it had already paid for SHALL keep its seat. Only where the registration still owes money after that SHALL the ordinary outcome of a lapsed window apply to what remains. A registration that paid for one seat SHALL NOT lose it for not paying for a second one it was offered.

A promoted placement whose payment window then lapses unpaid SHALL return to the substitute queue rather than expiring out of it, at the **end** of the queue, as every demotion for non-payment does — once seating has settled the queue is the tournament's holding area, and expiring would discard a fencer the organizer deliberately chose. It SHALL be notified as `registration` fixes under **Demotion is announced**. Before seating settles, a lapsed payment window SHALL expire the reservation as it does today, unless the registration still holds a substitute placement, which `registration` demotes rather than expires.

#### Scenario: Promotion into a free seat
- **WHEN** the organizer promotes a queued fencer into a discipline with a free place
- **THEN** the placement becomes seated, the amount owed is computed, a payment window opens, and payment instructions are sent

#### Scenario: Promotion of a paid registration bills the difference
- **WHEN** the organizer promotes the queued placement of a registration whose seated placements are paid in full
- **THEN** the placement becomes seated, the fencer owes only what the new placement adds, the registration does not revert to unpaid, and a fresh payment window opens

#### Scenario: Promotion notice states the discipline and the amount due
- **WHEN** a promotion opens a payment window
- **THEN** the notice names the discipline whose place has opened, states the amount now due rather than the registration's total, and states the date by which it is due

#### Scenario: Promotion on a payments-off tournament asks for nothing
- **WHEN** the organizer of a payments-off tournament promotes a queued fencer into a free place
- **THEN** the placement becomes seated, no payment window opens, no due date is set, and the fencer is told they have a place with no payment instructions

#### Scenario: Promotion into a full discipline refused
- **WHEN** the organizer attempts to promote into a discipline at capacity
- **THEN** the action is refused and the queue is unchanged

#### Scenario: Promotion of a cancelled registration refused
- **WHEN** the organizer attempts to promote a placement on a cancelled or expired registration
- **THEN** the action is refused and the queue is unchanged

#### Scenario: Payment window clamped to the tournament
- **WHEN** a fencer is promoted three days before the tournament on a tournament with a seven-day payment window
- **THEN** the payment window closes at the tournament date rather than after seven days

#### Scenario: Promoted fencer lets the window lapse
- **WHEN** a fencer promoted after seating settled does not pay before their payment window closes
- **THEN** they return to the end of the substitute queue, still reserved and owing nothing, rather than expiring, and are notified

#### Scenario: Lapsed window before settlement still expires
- **WHEN** a reservation's payment window closes unpaid on a tournament whose seating has not settled, and the registration holds no substitute placement
- **THEN** the reservation expires as it does today

#### Scenario: A payments-off promotion never lapses back
- **WHEN** time passes on a payments-off tournament after a promotion
- **THEN** the promoted registration stays seated and returns to the queue only if the organizer returns it

#### Scenario: A paid seat survives an unpaid promotion
- **WHEN** a registration paid for Longsword is promoted into Sabre before seating settles and lets the promotion window lapse unpaid
- **THEN** Sabre returns to the end of the queue, Longsword keeps its seat, the registration reads as paid, and nothing expires

#### Scenario: A paid seat survives after settlement too
- **WHEN** the same happens after seating settled, with a team promoted instead of Sabre
- **THEN** the team returns to the end of the waitlist and the paid Longsword seat stays

#### Scenario: Promotion credits money sent from the queue
- **WHEN** a fencer sitting entirely in the queue sent 1750 that was held for the organizer, and the organizer promotes them into a place priced 1750
- **THEN** the held transaction is credited, the registration reads as paid, and the promotion notice confirms the place without asking for payment

#### Scenario: Promotion counts a forfeited deposit
- **WHEN** a registration demoted at settlement holding a 500 deposit is promoted into a place priced 1750
- **THEN** it owes 1250, and the notice states 1250 as due

### Requirement: Organizer return to the queue
The organizer SHALL be able to return a seated registration to the substitute queue, one discipline at a time — the inverse of promotion. Returning SHALL mark the placement as a substitute, free the seat, and close any payment window the registration was under.

A returned placement SHALL take back the queue moment it held before it was promoted, or its registration time where it was never queued, so that returning and promoting again does not cost the fencer their place relative to other substitutes. The organizer's return is a correction, not a demotion for non-payment: it SHALL NOT send the placement to the end of the queue, and SHALL NOT send the demotion notice.

#### Scenario: Seated registration returned to the queue
- **WHEN** the organizer returns a reserved, unpaid, seated registration to the queue
- **THEN** its placement becomes a substitute, the seat is freed, and no payment window remains on it

#### Scenario: Queue position preserved
- **WHEN** a registration never queued before is returned to the queue among substitutes who registered both before and after it
- **THEN** it sits between them in registration order

#### Scenario: A demoted and promoted fencer returns to where they were
- **WHEN** a fencer demoted to the end of the queue at settlement is promoted, and the organizer then returns them
- **THEN** they take back the place their demotion gave them, not their registration-time place and not a new place at the end

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

### Requirement: Seating settles on the tournament's own day
The seating deadline SHALL be evaluated as a whole day in the tournament's
timezone, as `day-boundaries` fixes for every date the organizer entered.
Seating settles once the whole of the deadline's local day has passed, and not
before — a tournament held in Prague settles after midnight in Prague, whatever
timezone the deployment runs in.

The three questions the deadline answers SHALL be answered on that one clock:
when the automatic settlement pass fires, whether seating counts as settled for
a registration arriving now, and how far a reservation is from its reminder day
when the deadline is what anchors it. A deployment SHALL NOT be able to reach a
state where seating counts as settled while the settlement pass has not run.

#### Scenario: Settlement waits for the local midnight
- **WHEN** a tournament held in a zone ahead of UTC has a seating deadline of the 20th, and a lifecycle pass runs after midnight UTC on the 21st but before midnight where the tournament is held
- **THEN** seating is not settled, no registration is demoted, and a registration arriving now still takes a free seat

#### Scenario: Settled-ness and settlement agree
- **WHEN** a registration is submitted at the same moment a lifecycle pass runs, on a deployment whose process timezone is not UTC
- **THEN** the registration is placed by the same answer the pass acted on — queued if the pass settled, seated if it did not

#### Scenario: The deadline holds across process timezones
- **WHEN** the same tournament and the same moment are judged on deployments in different process timezones
- **THEN** seating settles on the same day in all of them

### Requirement: A conditional registration moves as one
A registration carrying a participation condition (`registration`, **Participation condition**) SHALL be promoted and returned as one wherever the condition is concerned.

**Promotion.** Promoting any placement of a registration whose condition is not met SHALL seat every discipline of the condition together with the placement promoted. It SHALL be offered and carried out only while every discipline of the condition, and the promoted discipline, has a free place, and SHALL be refused otherwise with a reason naming the discipline that has none. It SHALL bill what the newly seated placements add, as every promotion does. Promoting a placement outside the condition of a registration whose condition is already met SHALL be an ordinary promotion of that placement alone.

**Return.** Returning to the queue any placement belonging to a met condition SHALL return the whole registration: every seated placement, inside the condition and outside it, since the fencer does not come without the condition. Returning a placement outside the condition SHALL return that placement alone. The organizer's return SHALL keep each placement's queue moment, as every organizer's return does.

**Queue view.** A queued row of a conditional registration SHALL state the other disciplines the registration waits for. Its promote arrow SHALL be offered only when all of them have a free place, so that the rows the organizer can seat now are legible as those carrying an arrow. Its position SHALL remain its place in queue order; a conditional registration ahead of the line in one discipline does not stop a later fencer from being promoted there.

Demotion for non-payment already moves a whole registration and SHALL continue to.

#### Scenario: Promoting a conditional registration
- **WHEN** the organizer promotes a registration waiting on Longsword and Sabre and both have free places
- **THEN** both are seated at once and the registration is billed for both

#### Scenario: Arrow withheld while one discipline is full
- **WHEN** Longsword frees a place but Sabre is still full
- **THEN** the registration's Longsword row states that it also waits for Sabre and carries no promote arrow

#### Scenario: A later fencer may be promoted past it
- **WHEN** the conditional registration stands first in the Longsword queue and cannot be seated
- **THEN** the second fencer in that queue carries the promote arrow and may be seated

#### Scenario: Returning one placement of a condition returns all
- **WHEN** the organizer returns the Sabre placement of a registration seated in Longsword and Sabre under a condition
- **THEN** both placements are queued and the registration owes nothing

#### Scenario: A placement outside the condition moves alone
- **WHEN** the organizer returns the Rapier placement of a registration whose condition is Longsword and Sabre
- **THEN** only Rapier is queued

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
