## MODIFIED Requirements

### Requirement: In-app tournament creation
An account holding the global Organizer role or higher SHALL be able to create a tournament from the tournament picker via a minimal dialog asking display name and date. The slug SHALL be auto-derived from the name and be editable before submission. Derivation SHALL append the event's year only when the slugified name does not already carry one: a four-digit group between 1900 and 2099 standing as its own token in the slug counts as a year already present, and in that case the slug is the slugified name alone. The creator SHALL become the tournament's Tournament Owner and land in the console's Setup phase. Accounts below the Organizer role SHALL NOT be able to create tournaments.

Creation SHALL take two dialogs, not one. The first creates the tournament from the fields above; the second, opened once the tournament exists, chooses its mode as fixed by `tournament-modes`. A tournament SHALL be created with none of its features enabled, so that the second dialog only ever turns things on, and dismissing it leaves an easy-mode tournament rather than an unfinished one.

#### Scenario: Create from picker
- **WHEN** an account with the Organizer role submits the "New tournament" dialog with a name and date
- **THEN** the tournament is created with the derived slug, the account becomes its Tournament Owner, the Tournament Mode dialog opens, and the console then opens on the Setup phase

#### Scenario: Year appended when the name carries none
- **WHEN** the organizer types "Prague Open" with a date in 2026
- **THEN** the derived slug is `prague-open-2026`

#### Scenario: Year not appended twice
- **WHEN** the organizer types "My Tournament 2027" with a date in 2026
- **THEN** the derived slug is `my-tournament-2027`, with no second year appended

#### Scenario: Digits that are not a year
- **WHEN** the organizer types "Turnaj 3 zbraní" with a date in 2026
- **THEN** the derived slug is `turnaj-3-zbrani-2026`, because `3` is not a four-digit year

#### Scenario: Slug collision
- **WHEN** the derived slug is already taken
- **THEN** creation is rejected with a clear error, the mode dialog does not open, and the user can edit the slug

#### Scenario: Fencer cannot create
- **WHEN** an account with only the Fencer role attempts to create a tournament
- **THEN** creation is rejected with an authorization error

#### Scenario: Created tournament starts with no features
- **WHEN** a tournament is created and the mode dialog is dismissed
- **THEN** the tournament is in easy mode and the console opens on Setup

### Requirement: Payment and reservation parameters
Per tournament with the payments feature enabled, the organizer SHALL configure, in Setup: the payment mode, the payment window in days, the reminder day, and the public-list treatment of unpaid registrations. In deposit mode the organizer SHALL additionally configure the deposit amount. The bank account payments are collected into is configured in Setup alongside them, as fixed by `setup-navigation`.

**None of these parameters SHALL be offered while the payments feature is off**, as fixed by `tournament-modes`: a tournament Squire collects no money for has no payment mode to choose, no window to open and no reminder to send. Their stored values SHALL be retained and SHALL be offered again, unchanged, when the feature is turned back on. Every rule below governs a tournament whose payments feature is on.

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
- **WHEN** the organizer chooses how unpaid registrations appear on the public participant list
- **THEN** the choice is offered in Setup and takes effect on the public list

#### Scenario: Reminder day at or beyond expiry rejected
- **WHEN** the organizer sets the reminder day to 5 with a payment window of 5 days
- **THEN** the update is rejected with a message naming both values, and no tournament is left in a state where reminders are silently never sent

#### Scenario: Reminder day shortened below a valid reminder
- **WHEN** the organizer shortens the payment window to 3 days on a tournament whose reminder day is 4
- **THEN** the update is rejected, since the combination would stop reminders being sent

#### Scenario: No payment parameters while payments are off
- **WHEN** the organizer of a payments-off tournament looks through every Setup tab
- **THEN** no payment mode, deposit, payment window, reminder day, unpaid-list treatment or bank account field is offered anywhere

#### Scenario: Parameters return unchanged with the feature
- **WHEN** an organizer turns payments off on a tournament with a 5-day window and a day-3 reminder, and later turns payments back on
- **THEN** the window is still 5 days and the reminder still day 3

### Requirement: Setup completeness
Mandatory setup SHALL comprise: display name, date, location, at least one titular organizer, at least one discipline with a unit price, the bank account payments are collected into whenever the tournament charges anything at all **and its payments feature is on**, and — whenever the tournament prices in EUR as a second currency — every rendered EUR price field: each discipline's EUR price, each extra item's EUR price, and the EUR amount of each fixed discount. Every team discipline SHALL additionally have valid roster bounds, and a team discipline missing them SHALL be reported as a missing item. The team composition deadline SHALL NOT be part of mandatory setup: a tournament may offer team disciplines without one. A tournament still pricing through the legacy fixed weapon-rental/afterparty parameters SHALL be reported as blocked from enabling EUR, naming those parameters and directing the organizer to itemized extra services. The recorded exchange ratio is a Setup convenience only and is never part of completeness.

The bank account is mandatory **on a tournament Squire collects money for** because a published tournament accepts registrations, and a registration that cannot be paid holds a place against a deadline the fencer has no way to meet. Completeness is the only guarantee the registration path relies on, so the account SHALL be guaranteed by the same rule as every other mandatory item rather than checked again when a fencer asks how to pay.

**A tournament whose payments feature is off SHALL NOT be required to record a bank account, whatever it charges**, and SHALL NOT have one reported as missing. Squire requests no money for such a tournament, sends no payment instructions and reconciles no transactions, as fixed by `tournament-modes`; the prices it carries state what the event costs and are settled outside the system. Every other mandatory item SHALL be unaffected by the payments feature, because the rest of completeness is about what the tournament offers rather than about collecting for it.

A tournament SHALL be treated as charging when any price it can build a total from is above zero — any discipline's unit or early-bird price in either currency, any extra item's price in either currency, or any of the legacy fixed weapon-rental and afterparty parameters. Discounts SHALL NOT be considered, since they only reduce a total and cannot make a free tournament charge. A tournament that charges nothing SHALL be publishable with no bank account recorded. Completeness therefore depends on price **values** and not merely on their presence, so a tournament with payments enabled SHALL become incomplete at the moment it first sets a nonzero price without an account to collect it into — including a published tournament, whose save SHALL then be refused until the account is supplied.

An item whose editor the tournament's features conceal SHALL still be reported, and SHALL name the feature that restores its editor, as fixed by `setup-navigation`. Completeness reads the tournament's contents, not its features: a hidden team discipline is still a team discipline and is still checked for roster bounds.

Complete mandatory setup SHALL be the precondition for publishing a tournament, and SHALL NOT by itself make a tournament public: publication is the explicit act fixed by `tournament-publication`. The items still unconfigured SHALL be named on the Setup phase's `PUBLISH` tab, which is where the organizer learns what stands between the tournament and publication. A tournament that has not been published SHALL NOT accept registrations, whether or not its mandatory setup is complete.

A tournament published before the bank account became mandatory SHALL remain published and SHALL NOT be un-published by this rule, since the guarantee attaches at the moment of publication and cannot be applied retroactively. Such tournaments SHALL be reportable, so that an organizer can be told to supply the account rather than discovering it through a fencer who cannot pay.

#### Scenario: Blocking items shown
- **WHEN** the organizer opens `PUBLISH` for a tournament without location and without discipline prices
- **THEN** the tab lists location and the missing unit prices as blocking publication

#### Scenario: Missing roster bounds block publication
- **WHEN** a tournament has a team discipline with no roster bounds set
- **THEN** the `PUBLISH` tab lists that discipline's roster bounds as blocking publication

#### Scenario: Composition deadline never blocks
- **WHEN** a tournament offers a fully configured team discipline and no composition deadline
- **THEN** the `PUBLISH` tab reports nothing missing on that account and publication is available

#### Scenario: Missing EUR price blocks publication
- **WHEN** a CZK + EUR tournament has a discipline whose EUR price is empty
- **THEN** the missing EUR price is listed as blocking publication, with no separate exchange-rate requirement

#### Scenario: Legacy fixed fees block EUR
- **WHEN** the organizer enables EUR on a tournament still pricing through the fixed weapon-rental or afterparty parameters
- **THEN** those parameters are named as blocking EUR and the organizer is directed to itemized extra services

#### Scenario: Missing bank account blocks publication
- **WHEN** the organizer publishes a priced, payments-enabled tournament whose every other mandatory item is configured but which has recorded no bank account
- **THEN** the attempt is refused and names the bank account as the item still missing

#### Scenario: A priced tournament with payments off needs no account
- **WHEN** the organizer publishes a tournament with priced disciplines, the payments feature off and no bank account recorded
- **THEN** the publication succeeds and no missing bank account is reported

#### Scenario: Turning payments on makes the account mandatory
- **WHEN** the organizer turns the payments feature on for a published, priced tournament with no bank account recorded
- **THEN** the bank account is reported as missing, `PAYMENTS` carries the marker, and it is offered on that tab

#### Scenario: A tournament that charges nothing needs no account
- **WHEN** the organizer publishes a tournament whose every discipline and extra item is priced at zero and which has recorded no bank account
- **THEN** the publication succeeds and no missing bank account is reported

#### Scenario: Setting the first price makes the account mandatory
- **WHEN** a published, payments-enabled tournament that charged nothing is saved with a nonzero discipline price and still no bank account
- **THEN** the save is refused, naming the bank account, and the price is not stored

#### Scenario: Discounts alone do not make a tournament charge
- **WHEN** a tournament priced entirely at zero carries a fixed discount and has no bank account
- **THEN** it is still treated as charging nothing and remains publishable

#### Scenario: Bank account cannot be cleared after publication
- **WHEN** the organizer of a published, priced, payments-enabled tournament saves its payment settings with the bank account emptied
- **THEN** the save is refused and the stored account is unchanged

#### Scenario: Hidden team discipline still checked
- **WHEN** a tournament with the team feature off holds a team discipline with no roster bounds
- **THEN** the roster bounds are reported as blocking publication, naming the team disciplines feature as what restores their editor

#### Scenario: Setup completed
- **WHEN** the last mandatory item is filled
- **THEN** the `PUBLISH` tab lists nothing blocking and offers the publish action; the tournament remains invisible to fencers and closed to registration until it is published
