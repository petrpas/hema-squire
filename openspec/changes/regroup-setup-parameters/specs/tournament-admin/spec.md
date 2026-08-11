## MODIFIED Requirements

### Requirement: Payment and reservation parameters
Per tournament, the organizer SHALL configure, in Setup: the payment mode, the payment window in days, the reminder day, and the public-list treatment of unpaid registrations. In deposit mode the organizer SHALL additionally configure the deposit amount. The bank account payments are collected into is configured in Setup alongside them, as fixed by `setup-navigation`.

The amount-matching tolerance in percent SHALL remain a per-tournament value but SHALL be configured in the console's payments phase rather than in Setup: it is tuned against transactions that already exist, while reconciliation is running, and is not a decision taken before the tournament is published.

The **payment mode** SHALL be one of:

- **immediate payment** — the full amount is owed at registration;
- **reservation with deposit** — a deposit is owed at registration and the balance by the seating deadline;
- **reservation without deposit** — nothing is owed at registration and the full amount is owed by the seating deadline.

It SHALL default to immediate payment, which is the behaviour of a tournament created before the mode existed.

The mode SHALL be offered as a choice between three explained options rather than a bare list of names. Each option SHALL state its consequence in one line, expressed in the tournament's own configured values — the payment window in days and the effective seating deadline — so that changing either rewrites what the options say. The deposit amount SHALL be entered within its own option, as part of that option's statement, rather than as a separate field appearing elsewhere. The seating deadline SHALL be shown in these statements as text resolved from the timeline, including its fallback where it is unset, and SHALL NOT be editable there.

The **payment window** is the number of days between money being requested and money being due; it exists because bank transfers do not settle instantly. It SHALL apply wherever money is requested — at registration in immediate and deposit modes, and on promotion from the substitute queue in every mode. It SHALL be accepted between 2 and 7 days inclusive. A tournament configured before that range was introduced SHALL keep its stored value until the parameter is next edited.

The **deposit** SHALL be a flat amount, never a percentage of the total, so that amending a registration can never change a deposit that has already been paid. It is a price like every other: a whole-unit amount in the tournament's local currency, plus an independent EUR amount where the tournament prices in EUR, and it participates in the setup completeness check on the same terms as other prices. It SHALL be required and greater than zero in deposit mode, and SHALL be ignored in the other modes.

The **expiry grace period** — how long after a reservation expires a payment carrying its VS may still reinstate it, subject to capacity — SHALL be fixed at 48 hours and SHALL NOT be offered to the organizer. It is a tolerance for bank settlement latency rather than a decision about the tournament. Its stored value SHALL be retained so it can be offered again without a migration, and a tournament carrying a different stored value SHALL continue to use it.

The **refundable-until date** SHALL NOT be offered to the organizer. Refunds are settled by the organizer outside the system for now. The stored date, the refund state and the refundability flag SHALL be retained against a future refund policy, and nothing SHALL be computed from the date while it cannot be set.

The reminder day MUST fall before the payment window ends. A reminder day at or beyond the payment window SHALL be rejected with a message naming both values, because expiry runs before reminders: such a reservation would always be expired before its reminder was due, and no reminder would ever be sent.

#### Scenario: Parameters applied
- **WHEN** the organizer sets the payment window to 5 days and the reminder to day 3
- **THEN** new reservations expire after 5 unpaid days and reminder emails go out on day 3

#### Scenario: Mode chosen by reading its effect
- **WHEN** the organizer opens the payment mode on a tournament with a 5-day window and a seating deadline of 12 September
- **THEN** each of the three options states what it means in those terms, and the deposit amount is entered inside the deposit option

#### Scenario: Option text follows the configured values
- **WHEN** the organizer changes the payment window from 5 days to 3
- **THEN** the options restate their effect in days without the organizer saving or reopening the section

#### Scenario: Seating deadline shown, not edited, beside the mode
- **WHEN** the organizer reads the deposit option on a tournament whose seating deadline is unset
- **THEN** it names the registration close as the effective date, and offers no field to change it

#### Scenario: Mode defaults to immediate payment
- **WHEN** the organizer creates a tournament without choosing a payment mode
- **THEN** it is immediate payment, the full amount is owed at registration, and no deposit or seating behaviour applies

#### Scenario: Payment window outside the accepted range
- **WHEN** the organizer sets the payment window to 14 days
- **THEN** the update is rejected with a message naming the accepted range

#### Scenario: Grace period is not an organizer parameter
- **WHEN** the organizer looks through every Setup tab and every console phase panel
- **THEN** no expiry grace period field is offered, and reinstatement continues to work at 48 hours

#### Scenario: Tolerance stays with reconciliation
- **WHEN** the organizer needs to widen the amount-matching tolerance during reconciliation
- **THEN** it is offered in the console's payments phase and not in Setup

#### Scenario: Unpaid-list treatment has an editor
- **WHEN** the organizer chooses how unpaid registrations appear on the public participant list
- **THEN** the choice is offered in Setup and takes effect on the public list

#### Scenario: Reminder day at or beyond expiry rejected
- **WHEN** the organizer sets the reminder day to 5 with a payment window of 5 days
- **THEN** the update is rejected with a message naming both values, and no tournament is left in a state where reminders are silently never sent

### Requirement: Registration window
A tournament SHALL have optional registration-opens and registration-closes dates. Registration SHALL be unavailable before the opens date (when set) and after the closes date (when set); with no closes date, registration stays available until the tournament date. With no opens date, registration is available as soon as the tournament is published (see `tournament-publication`).

These dates, the seating deadline and the team composition deadline SHALL be presented together as the tournament's timeline, in chronological order, anchored by the tournament's own date shown read-only at its foot. The order SHALL be fixed by meaning rather than by which dates are filled, so an unset date keeps its place in the sequence.

**Each date SHALL carry a hint stating what it governs and what happens when it is left unset**, since each falls back to something different and the fallback is otherwise invisible: registration opens on publication, the seating deadline falls on the registration close, the registration close falls on the tournament date, and an unset composition deadline means no deadline and no reminders. The composition deadline's hint SHALL lead with what it does not do — it checks and reminds, and locks nothing.

A tournament SHALL additionally have an optional amendments-close date, after which fencers may no longer amend their registrations even while registration itself remains open. It SHALL NOT be offered to the organizer; unset, amendment is available on exactly the same window as registration, which is the intended default. The stored date SHALL be retained and honoured where one is already set, so the field can be offered again without a migration.

A tournament SHALL additionally have an optional team composition deadline, constrained only to be a date on or before the tournament date. It SHALL be independent of the registration and amendment windows in both directions: it MAY fall before or after either, and no combination of the three SHALL be rejected on account of their order. It governs nothing but the check and the reminder fixed by `team-disciplines`, and SHALL have no effect on a tournament that offers no team discipline.

#### Scenario: Before opening
- **WHEN** a fencer visits registration before the registration-opens date
- **THEN** registration is unavailable and the opening date is shown

#### Scenario: No close date set
- **WHEN** no registration-closes date is set
- **THEN** registration remains available through the tournament date

#### Scenario: Dates read as a sequence
- **WHEN** the organizer opens the timeline with only the registration-opens date set
- **THEN** every date is shown in chronological order with its place kept, and the tournament date closes the sequence without a field to edit it

#### Scenario: Fallback stated on an unset date
- **WHEN** the organizer reads the seating deadline with no value set
- **THEN** its hint states that it falls on the registration close

#### Scenario: Composition deadline hint does not imply a lock
- **WHEN** the organizer reads the team composition deadline
- **THEN** its hint states that it reminds only, and that no roster is locked, no team is cancelled or queued, and no capacity is freed

#### Scenario: Amendments follow registration by default
- **WHEN** the organizer looks for an amendments-close date
- **THEN** none is offered, and amendment is available exactly while registration is available

#### Scenario: Stored amendments-close still honoured
- **WHEN** a tournament already carries an amendments-close date two weeks before registration closes
- **THEN** amendment still closes on that date, even though the field is no longer offered

#### Scenario: Composition deadline after amendments close
- **WHEN** a composition deadline falls four weeks after amendment has closed
- **THEN** the combination is accepted, and rosters stay editable after amendments have closed

## ADDED Requirements

### Requirement: Legacy fixed fees are cleared, not edited
The fixed weapon-rental and afterparty parameters, and the tournament-wide early-bird date that switches disciplines between their standard and early prices, SHALL NOT be offered as editable fields. They are the superseded pricing path: extra-service items replace the fixed fees, and the early-bird discount condition replaces the tournament-wide date. Their stored values SHALL be retained so that pre-itemized tournaments keep repricing reproducibly.

Because a tournament still carrying legacy fixed fees cannot enable EUR and is therefore blocked from publication, the organizer SHALL be offered a way to clear them. That control SHALL appear only while the tournament actually carries such fees, SHALL show the stored values it is about to discard, and SHALL sit on the same tab the completeness checklist attributes the blockage to. It SHALL NOT appear on a tournament that has no legacy fees.

Clearing SHALL be an explicit organizer action. No migration or automatic process SHALL zero these values, since doing so would silently change the price of a live tournament.

#### Scenario: Legacy fees not editable
- **WHEN** the organizer looks for the weapon-rental fee, the afterparty fee, or the early-bird date in Setup or in any console phase panel
- **THEN** none is offered as a field

#### Scenario: Blocked tournament can clear them
- **WHEN** a EUR-priced tournament still carries legacy fixed fees and is blocked from publication
- **THEN** the payments tab shows the stored fees and offers to clear them, and clearing unblocks publication

#### Scenario: Control absent when not needed
- **WHEN** a tournament carries no legacy fixed fees
- **THEN** no such control is shown anywhere in Setup

#### Scenario: Legacy totals stay reproducible
- **WHEN** a pre-itemized tournament that was never cleared is repriced
- **THEN** its stored legacy fees are used exactly as before
