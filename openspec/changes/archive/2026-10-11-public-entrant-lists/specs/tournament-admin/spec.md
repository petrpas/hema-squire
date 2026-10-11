## MODIFIED Requirements

### Requirement: Payment and reservation parameters
Per tournament with the payments feature enabled, the organizer SHALL configure, in Setup: the payment mode, the payment window in days, and the reminder day. In deposit mode the organizer SHALL additionally configure the deposit amount. The bank account payments are collected into is configured in Setup alongside them, as fixed by `setup-navigation`.

**None of these parameters SHALL be offered while the payments setting is off**, as fixed by `payments`: a tournament Squire collects no money for has no payment mode to choose, no window to open and no reminder to send. Their stored values SHALL be retained and SHALL be offered again, unchanged, when the feature is turned back on. Every rule below governs a tournament whose payments feature is on.

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

#### Scenario: Existing longer window kept until edited
- **WHEN** a tournament configured with a 10-day payment window is loaded and other parameters are read
- **THEN** its stored window is unchanged and reservations continue to behave as before

#### Scenario: Deposit required in deposit mode
- **WHEN** the organizer selects reservation with deposit and leaves the deposit amount empty
- **THEN** the update is rejected, naming the missing deposit

#### Scenario: Deposit priced in both currencies
- **WHEN** the tournament prices in EUR alongside its local currency and the organizer sets a deposit
- **THEN** both the local and the EUR deposit amounts are required, neither is derived from the other, and setup is incomplete until both are filled

#### Scenario: Grace period is not an organizer parameter
- **WHEN** the organizer looks through every Setup tab and every console phase panel
- **THEN** no expiry grace period field is offered, and reinstatement continues to work at 48 hours

#### Scenario: Tolerance stays with reconciliation
- **WHEN** the organizer needs to widen the amount-matching tolerance during reconciliation
- **THEN** it is offered in the console's payments phase and not in Setup

#### Scenario: Unpaid-list treatment has an editor
- **WHEN** the organizer looks through Setup's payment parameters for how unpaid registrations appear publicly
- **THEN** no such choice is offered: unpaid entrants are always shown faded, as `public-entrants` fixes

#### Scenario: Reminder day at or beyond expiry rejected
- **WHEN** the organizer sets the reminder day to 5 with a payment window of 5 days
- **THEN** the update is rejected with a message naming both values, and no tournament is left in a state where reminders are silently never sent

#### Scenario: Reminder day shortened below a valid reminder
- **WHEN** the organizer shortens the payment window to 3 days on a tournament whose reminder day is 4
- **THEN** the update is rejected, since the combination would stop reminders being sent

#### Scenario: No payment parameters while payments are off
- **WHEN** the organizer of a payments-off tournament looks through every Setup tab
- **THEN** no payment mode, deposit, payment window, reminder day or bank account field is offered anywhere

#### Scenario: Parameters return unchanged with the feature
- **WHEN** an organizer turns payments off on a tournament with a 5-day window and a day-3 reminder, and later turns payments back on
- **THEN** the window is still 5 days and the reminder still day 3
