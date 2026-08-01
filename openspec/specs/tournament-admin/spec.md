# tournament-admin Specification

## Purpose
Define and configure tournaments in a multi-tournament deployment: disciplines, pricing, payment and reservation parameters, and organizer authorization.

## Requirements

### Requirement: Multiple tournaments in one deployment
The system SHALL host multiple tournaments concurrently in a single deployment. Registrations, rules, operation parameters, pricing, and exports SHALL be tournament-scoped; fencer accounts SHALL be shared globally.

#### Scenario: Two tournaments run in parallel
- **WHEN** organizers administer two tournaments at the same time
- **THEN** the data, rules, and parameters of one tournament are invisible to and unaffected by the other

### Requirement: Tournament definition
A tournament SHALL be defined by internal name, display name, an optional subtitle, an optional logo, date, communication language, location (free text), an optional description, a qualification statement, a list of titular organizers, and a set of disciplines. The subtitle is free text that MAY be longer than the display name and is frequently empty; every presentation of the tournament SHALL render correctly whether or not the subtitle is set. The logo is an optional image supplied by the organizer, stored with the tournament and served for display; the system SHALL bound its size on upload (reject oversized uploads and re-encode to a bounded image) so it stays small. The description is optional free-form text of arbitrary length, authored in markdown and stored verbatim as its markdown source; it SHALL be presented as formatted content according to `organizer-prose`, which fixes the honored subset, the sanitizer allowlist, and the presentation rules. Titular organizers are free-text names of clubs or other entities shown publicly as the tournament's organizers, each with an optional link; they are independent of account-based console access. Each discipline SHALL have a code and human-readable name drawn from the HEMA taxonomy (weapon LS/SA/RA/RD/SB × gender Open/Women/Men × material Steel/Plastic), a capacity limit, a unit price, optional schedule fields (`when`, `where`) mainly for multi-day events, and an optional ruleset consisting of a short style name and an optional external link. In the console, a discipline SHALL be identified by its name in emphasized text, and each of its optional fields (`when`, `where`, ruleset name, ruleset link) SHALL carry a help hint stating what belongs in it.

Subtitle, logo, description, qualification, disciplines (including their schedule and ruleset fields) and titular organizers SHALL be editable in the console Setup phase, disciplines and organizers as row tables with add and remove. The communication language SHALL NOT be editable in Setup: it is assigned when the tournament is created and thereafter governs fencer emails without being offered as a settings field. The Setup section carrying the tournament's own identity fields SHALL NOT be given a section heading of its own, and SHALL present those fields in this order: display name, subtitle, logo, date, location, description, qualification statement, registration opens, registration closes, registration instructions.

#### Scenario: Organizer configures disciplines
- **WHEN** the organizer adds disciplines LS and SAW in the Setup table, each with a capacity and a unit price
- **THEN** registration offers exactly those disciplines under those capacity constraints at those prices

#### Scenario: Discipline schedule and ruleset captured
- **WHEN** the organizer sets a discipline's when to "Saturday", where to "Main Hall — Kurtzstrasse 21", and ruleset to "Right of Way" with an external link
- **THEN** the tournament information presents that discipline with its schedule and a ruleset link, and omits those lines for disciplines that leave them empty

#### Scenario: Optional discipline fields explain themselves
- **WHEN** the organizer reaches the help marker next to a discipline's `when`, `where`, ruleset name, or ruleset link field
- **THEN** a hint appears describing what belongs in that field (for example, for `when`: that it takes a rough time such as "Saturday morning")

#### Scenario: Identity fields in the stated order
- **WHEN** the organizer opens the `TOURNAMENT` tab
- **THEN** the identity fields read top to bottom as display name, subtitle, logo, date, location, description, qualification statement, registration opens, registration closes, registration instructions

#### Scenario: Communication language not offered
- **WHEN** the organizer looks through every Setup tab
- **THEN** no field offers the tournament's communication language, and the language stored at creation is unchanged by any save

#### Scenario: Emails still follow the stored language
- **WHEN** a fencer registers for a tournament created with Czech as its communication language
- **THEN** the confirmation email is Czech, exactly as before the field left Setup

#### Scenario: Subtitle and logo optional
- **WHEN** a tournament is saved with a subtitle and a logo, and another is saved with neither
- **THEN** both render correctly wherever the tournament is presented, the first showing its subtitle and logo and the second showing neither

#### Scenario: Oversized logo rejected
- **WHEN** the organizer uploads a logo larger than the configured cap
- **THEN** the upload is rejected with a clear message and no logo is stored

#### Scenario: Titular organizers edited
- **WHEN** the organizer adds "Duelanti od sv. Rocha" as a titular organizer row
- **THEN** the name appears wherever the tournament presents its organizers, without granting any console access

#### Scenario: Organizer with a link
- **WHEN** a titular organizer row carries a link and another leaves it empty
- **THEN** the first is presented as a link on the organizer's name and the second as plain text, and both are stored with the tournament

#### Scenario: Description written and presented
- **WHEN** the organizer writes a multi-paragraph markdown description in Setup and saves
- **THEN** the markdown source is stored verbatim and presented as formatted content — paragraph breaks intact, headings, lists, emphasis and links rendered, and nothing outside the honored subset rendered as markup

#### Scenario: Description written without markdown
- **WHEN** the organizer writes a plain multi-paragraph description using no markdown markers
- **THEN** it is presented with its paragraph breaks and line breaks intact, exactly as before markdown authoring was introduced

### Requirement: Registration instructions
A tournament SHALL have an optional multiline free-text `registration instructions` field, editable in the Setup phase and distinct from the public description. It is authored in markdown and stored verbatim as its markdown source, and SHALL be presented as formatted content according to `organizer-prose`. It SHALL be presented only on the registration form. It SHALL NOT be part of mandatory setup, and its absence SHALL NOT change any other presentation.

#### Scenario: Instructions shown on the form only
- **WHEN** the organizer fills registration instructions and a fencer opens the tournament
- **THEN** the instructions appear on the registration form and do not appear on the information screen

#### Scenario: Instructions absent
- **WHEN** a tournament has no registration instructions
- **THEN** the registration form renders correctly with no instructions block

#### Scenario: Markdown rendered, line breaks preserved
- **WHEN** the instructions contain several paragraphs, a bullet list and a link
- **THEN** they render with their paragraph and line breaks intact, the list as list items and the link as an `--ink` underlined link, with no markup characters visible

### Requirement: Pricing configuration
The system SHALL compute registration totals from categorized billable items and an ordered discount list.

Items: every billable item SHALL have a name, a price, and a category. In local + EUR mode every billable item SHALL additionally have a EUR price, stored independently of its local price. Disciplines are items of category `discipline`, priced on their Setup rows, with standard and early-bird prices in each configured currency. Extra services SHALL be organizer-defined rows with a free-text name (for example "afterparty saturday", "castle visit sunday", "t-shirt"), a category from a fixed enum, a price per configured currency, an optional per-registration quantity limit (limit 1 renders as a checkbox, higher limits as a quantity selector), and optional descriptive fields `when`, `where`, and `remark` used when the item is presented informationally. These descriptive fields SHALL NOT affect pricing.

The extra-service category enum SHALL be `seminar`, `rental`, `afterparty`, `merch`, `other_action`, and `other_item`, and SHALL divide into two kinds: **action** categories (`seminar`, `afterparty`, `other_action`), which happen at a time and place, and **item** categories (`rental`, `merch`, `other_item`), which are goods. For action categories the console SHALL offer `when` and `where` and SHALL NOT offer a quantity limit; their quantity limit SHALL be stored as 1. For item categories the console SHALL offer the quantity limit and SHALL NOT offer `when` or `where`. `remark` SHALL be available for both kinds. `other_action` SHALL behave in every respect as `afterparty` and `seminar` do, and `other_item` as `merch` does. Existing rows in an action category whose stored quantity limit is greater than 1 SHALL retain that value until the row is next saved, so previously computed totals remain reproducible.

Discounts: an ordered list of rows, each with a name, a condition, an effect, and a category scope. Conditions SHALL be drawn from an extensible enumeration, initially: registered discipline count equals N, and registration date on or before a configured date (early bird). Effects SHALL be a fixed amount or a percentage. A fixed-amount effect SHALL carry an amount per configured currency, since a fixed discount is a price decision like any other; a percentage effect is currency-neutral and SHALL carry a single value. The total SHALL be computed **independently for each configured currency**, in each case by summing that currency's selected item prices, subtracting that currency's applicable fixed discounts from their scoped category subtotals (floored at zero), then applying applicable percentage discounts sequentially to their scoped subtotals, and finally rounding half-up to a whole currency unit exactly once. The category scope SHALL be stored per discount from the start (defaulting to `discipline`), even while the Setup UI does not yet expose a scope picker, and SHALL accept every category in the enum.

The totals produced for the two currencies are independent results of the same computation over different inputs, and SHALL NOT be expected or required to correspond at any exchange ratio.

Tournaments with no extra-service items and no discounts SHALL keep the legacy computation (per-discipline fees, `fee_early`, and the fixed weapon-rental/afterparty parameters) so that historical totals remain reproducible. The fixed weapon-rental and afterparty parameters SHALL remain single-currency; a tournament whose pricing still uses them SHALL NOT be able to enable EUR, and the completeness checklist SHALL name them and direct the organizer to itemized extra services.

#### Scenario: Count discount applied
- **WHEN** disciplines are priced 30 € each and a discount row "−10 € when 2 disciplines" exists, and a fencer registers for two disciplines
- **THEN** the discipline part of the total is 50 €, not 60 €

#### Scenario: Early bird as percentage discount
- **WHEN** a discount row "−15 % when registered before the early-bird date" exists and a fencer registers in time for two disciplines priced 30 € each with the −10 € count discount
- **THEN** the total is (60 − 10) × 0.85 = 42.5, rounded half-up to 43, and remains reproducible for that reservation

#### Scenario: Extra service with quantity
- **WHEN** the organizer defines "weapon rental" (category `rental`, 2 €, limit 4) and a fencer selects quantity 2
- **THEN** 4 € is added to the total

#### Scenario: Each currency totalled independently
- **WHEN** a fencer registers for two disciplines priced 800 Kč / 32 € and 700 Kč / 28 € on a CZK + EUR tournament
- **THEN** the local total is 1500 Kč and the EUR total is 60 €, each summed from its own column

#### Scenario: Fixed discount applied per currency
- **WHEN** a fixed discount of 200 Kč / 8 € applies to a registration
- **THEN** 200 is subtracted from the local total and 8 from the EUR total, each floored at zero within its own computation

#### Scenario: Percentage discount applied to both
- **WHEN** a −15 % discount applies on a CZK + EUR tournament
- **THEN** it is applied to each currency's scoped subtotals, each rounded half-up to a whole unit exactly once

#### Scenario: Totals need not correspond
- **WHEN** a registration's two totals are computed and their implied ratio differs from the recorded exchange ratio
- **THEN** both totals stand as computed and no reconciliation, warning, or adjustment occurs

#### Scenario: Descriptive fields do not change totals
- **WHEN** an extra service carries when/where/remark text
- **THEN** the computed total is identical to the same item without those fields

#### Scenario: Action category offers place and time, not quantity
- **WHEN** the organizer sets an extra service's category to `afterparty`, `seminar`, or `other_action`
- **THEN** the row offers `when` and `where`, offers no quantity limit, and is stored with a quantity limit of 1

#### Scenario: Item category offers quantity, not place and time
- **WHEN** the organizer sets an extra service's category to `merch`, `rental`, or `other_item`
- **THEN** the row offers a quantity limit and offers neither `when` nor `where`

#### Scenario: Generic categories behave like their models
- **WHEN** a tournament defines an `other_action` row priced 15 € and an `other_item` row priced 15 €, and a fencer selects both
- **THEN** 30 € is added to the total, and discounts scoped to those categories apply exactly as they would to `afterparty` and `merch`

#### Scenario: Legacy tournament unaffected
- **WHEN** totals are recomputed for a tournament that has no extra-service items and no discounts
- **THEN** the legacy per-discipline fees and fixed extras produce the same totals as before this change

#### Scenario: Legacy fixed parameters block EUR
- **WHEN** the organizer attempts to enable EUR on a tournament still pricing through the fixed weapon-rental and afterparty parameters
- **THEN** the completeness checklist names those parameters as blocking EUR and directs the organizer to itemized extra services

### Requirement: Tournament currency
A tournament SHALL be priced in one of three currency modes, chosen in Setup above the price tables:

- **local only** — a single local currency drawn from a closed enumeration, initially `CZK` and `EUR`.
- **local + EUR** — a local currency that is not EUR, plus EUR as an accepted second currency.
- **EUR only** — the local currency is EUR and there is no second currency.

The mode SHALL decide how the price tables render: one price column in the single-currency modes, and two in local + EUR. Every configured price SHALL be a whole unit of the currency of its column, and completeness SHALL follow from the form — a rendered price field left empty is an incomplete price, checked by the same rule that already governs single-currency tournaments, with no separate EUR-completeness rule.

In local + EUR mode the local price and the EUR price of any item SHALL both be organizer decisions and SHALL both be stored as entered. Neither SHALL be computed from the other at any point after entry. The two prices of an item, and therefore the two totals of a registration, are NOT required to correspond at any exchange rate, and the system SHALL NOT check, warn about, or reconcile the ratio between them.

The organizer MAY record an exchange ratio, expressed as local-currency units per 1 EUR. It SHALL be used for exactly one purpose: a **recalculate missing** action that fills empty price fields from filled ones, rounding half-up to whole units, in either direction. The action SHALL fill only empty fields and SHALL NOT overwrite any price the organizer has entered. It SHALL run only when explicitly invoked, never on save, on rate change, or automatically. The recorded ratio SHALL NOT be read by price computation, registration totals, payment instructions, QR generation, or payment matching.

Changing the currency mode SHALL retain stored prices rather than clearing them, so that a mode switched away from and back again reveals the same prices unchanged.

The Setup UI SHALL state the ratio's direction explicitly and SHALL warn — without blocking the save — when the entered ratio falls outside a plausible range.

#### Scenario: Czech tournament prices in both currencies
- **WHEN** the organizer selects CZK + EUR and enters 800 Kč and 32 € for a discipline
- **THEN** both prices are stored as entered and neither is recomputed from the other

#### Scenario: Prices need not correspond at the ratio
- **WHEN** the organizer prices one discipline 800 Kč / 32 € and another 700 Kč / 30 € while the recorded ratio is 25
- **THEN** both rows are accepted, no warning is raised about the differing implied ratios, and both totals compute from their own column

#### Scenario: Single-currency mode renders one column
- **WHEN** the organizer selects CZK only, or EUR only
- **THEN** the price tables render a single price column and no EUR figure is presented anywhere

#### Scenario: Recalculate fills only what is empty
- **WHEN** the organizer fills every CZK price, fills the EUR price of one discipline by hand, and invokes recalculate missing at a ratio of 25
- **THEN** the empty EUR prices are filled with the CZK prices divided by 25 rounded to whole units, and the hand-entered EUR price is left exactly as typed

#### Scenario: Recalculate works in either direction
- **WHEN** the organizer fills only EUR prices and invokes recalculate missing
- **THEN** the empty local prices are filled from the EUR prices at the recorded ratio, rounded to whole units

#### Scenario: Ratio never reaches a computed amount
- **WHEN** the organizer changes the recorded ratio after prices are entered
- **THEN** no stored price, no registration total, no payment instruction, and no QR code changes

#### Scenario: Mode switch retains prices
- **WHEN** the organizer switches a fully priced CZK + EUR tournament to CZK only and later switches back
- **THEN** the EUR prices are hidden while in single-currency mode and are present and unchanged on switching back

#### Scenario: Incomplete EUR prices block registration
- **WHEN** a tournament is in CZK + EUR mode with one discipline's EUR price left empty
- **THEN** the completeness checklist reports that price as missing and registration is unavailable

#### Scenario: Implausible ratio warns but saves
- **WHEN** the organizer enters an exchange ratio far outside the plausible range
- **THEN** Setup shows a warning naming the expected direction and the save still succeeds

#### Scenario: Existing tournaments unchanged
- **WHEN** a tournament created before this change is loaded
- **THEN** its local currency and prices are those it already had, and its totals are identical to before

### Requirement: Price changes during open registration
The organizer SHALL be able to change prices at any time, including while registration is open. The system SHALL NOT prevent it.

When a price is changed on a tournament whose registration is open, the organizer SHALL be warned before the change is saved, and the warning SHALL state what actually happens: that fencers already registered keep the amount they were quoted, that a fencer who subsequently amends their registration is repriced at the new prices, and that new registrations use the new prices. The warning SHALL state that changing prices mid-registration is bad practice, and SHALL allow the organizer to proceed.

Registrations already created SHALL retain the total computed when they were created, so a price change SHALL NOT alter what any existing registration owes and SHALL NOT affect the reconciliation of any payment.

#### Scenario: Warning shown on a price change with registration open
- **WHEN** the organizer changes a discipline price on a tournament whose registration is open
- **THEN** a warning states that existing registrations keep their quoted amount, that amending fencers are repriced, and that new registrations use the new price, and the organizer can proceed

#### Scenario: No warning before registration opens
- **WHEN** the organizer changes a price on a tournament whose registration has not opened
- **THEN** the price is saved without the warning

#### Scenario: Existing registrations keep their total
- **WHEN** a discipline's price is raised after fencers have registered for it
- **THEN** every existing registration's total is unchanged and every pending payment reconciles against the amount originally quoted

#### Scenario: New registrations take the new price
- **WHEN** a fencer registers after a price change
- **THEN** their total is computed from the new prices

### Requirement: Extra-service option field
An extra service MAY declare a single option: an option label (for example "size") and an optional list of preset choices. A label with choices SHALL be answered by picking one of the choices; a label without choices SHALL be answered with free text. An extra service with no option label SHALL take no option. Options SHALL be purely descriptive and SHALL NOT affect price computation.

#### Scenario: Option with preset choices configured
- **WHEN** the organizer defines "t-shirt" (category `merch`, 300, limit 5) with option label "size" and choices S, M, L, XL
- **THEN** registration offers that item with a choice of those four sizes

#### Scenario: Free-text option configured
- **WHEN** the organizer defines an option label with no choices
- **THEN** registration offers that item with a free-text field for the option

#### Scenario: Option does not change the total
- **WHEN** totals are computed for a selection with an option answered and for the same selection without the option
- **THEN** both totals are identical

### Requirement: Tournament qualification statement
Each tournament SHALL carry a qualification statement consisting of an openness flag and optional criteria text. The flag SHALL default to open, so a tournament that never sets it presents as open to everyone. When the organizer marks the tournament as requiring qualification, criteria text SHALL be required and SHALL be free text (for example "national championship placement, HR top 500"); the field SHALL carry a help hint offering such examples. Marking the tournament open again SHALL clear the criteria text. The statement SHALL be editable in the Setup phase between the description and the registration dates, and SHALL be presented wherever the tournament is described. The statement is informational: it SHALL NOT restrict, block, or flag any registration.

#### Scenario: Default is open
- **WHEN** a tournament is created and its qualification is never touched
- **THEN** it is stored as open to everyone and presented as such

#### Scenario: Qualification criteria recorded
- **WHEN** the organizer marks the tournament as requiring qualification and enters "mistrovství ČR, HR top 500"
- **THEN** that text is stored and presented as the tournament's qualification criteria

#### Scenario: Criteria required when qualification is required
- **WHEN** the organizer marks the tournament as requiring qualification and saves with empty criteria
- **THEN** the save is rejected with a field-level message and the tournament's stored qualification is unchanged

#### Scenario: Reopening clears criteria
- **WHEN** a tournament with qualification criteria is switched back to open to everyone and saved
- **THEN** the criteria text is cleared and the tournament presents as open to everyone

#### Scenario: Statement sits after the description
- **WHEN** the organizer opens the `TOURNAMENT` tab
- **THEN** the qualification statement appears below the description and above the registration-opens field

#### Scenario: Qualification does not gate registration
- **WHEN** a fencer registers for a tournament that requires qualification
- **THEN** the registration proceeds exactly as it would for an open tournament

### Requirement: Logo upload failure reporting
A failed logo upload SHALL tell the organizer which of the distinguishable causes occurred: the file exceeded the size cap, the file could not be decoded as an image, the account is not authorized, or the upload failed for another reason. A message SHALL NOT attribute a failure to the file's format unless the server actually rejected it as undecodable. The size cap SHALL be generous enough to accept an ordinary photograph produced by a phone or camera, since the server re-encodes every accepted image down to the stored bound regardless of input size, and the server SHALL record the underlying decode failure for diagnosis.

#### Scenario: Ordinary JPEG accepted
- **WHEN** the organizer uploads a multi-megapixel JPEG photograph of a few megabytes
- **THEN** the upload succeeds, the tournament reports having a logo, and the stored image is the re-encoded bounded version

#### Scenario: Oversized file named as oversized
- **WHEN** the uploaded file exceeds the size cap
- **THEN** the message states that the file is too large, and does not claim it is not an image

#### Scenario: Undecodable file named as such
- **WHEN** the uploaded file cannot be decoded as an image
- **THEN** the message states that the file is not a supported image, and the server records the decode failure

#### Scenario: Other failure not blamed on the file
- **WHEN** the upload fails for any other reason, such as an authorization or server error
- **THEN** the message reflects that cause and does not claim the file is not an image

### Requirement: Payment and reservation parameters
Per tournament, the organizer SHALL configure: reservation validity in days, reminder day, amount-matching tolerance in percent, refundable-until date, the bank account used in payment instructions, the public-list treatment of unpaid registrations, and the expiry grace period in hours.

The expiry grace period SHALL define how long after a reservation expires a payment carrying its VS may still reinstate it, subject to capacity. It SHALL default to 48 hours for a new tournament and SHALL accept zero, which disables automatic reinstatement and routes every post-expiry payment to explicit organizer action.

The reminder day MUST fall before the reservation validity period ends. A reminder day at or beyond the validity period SHALL be rejected with a message naming both values, because expiry runs before reminders: such a reservation would always be expired before its reminder was due, and no reminder would ever be sent.

#### Scenario: Parameters applied
- **WHEN** the organizer sets reservation validity to 10 days and the reminder to day 5
- **THEN** new reservations expire after 10 unpaid days and reminder emails go out on day 5

#### Scenario: Grace period default
- **WHEN** the organizer creates a tournament without touching the grace period
- **THEN** it is 48 hours, and a payment arriving within 48 hours of expiry can reinstate the reservation

#### Scenario: Grace period disabled
- **WHEN** the organizer sets the expiry grace period to zero
- **THEN** no payment reinstates a reservation automatically and every post-expiry payment is flagged for organizer action

#### Scenario: Reminder day at or beyond expiry rejected
- **WHEN** the organizer sets the reminder day to 10 with a reservation validity of 10 days
- **THEN** the update is rejected with a message naming both values, and no tournament is left in a state where reminders are silently never sent

#### Scenario: Reminder day shortened below a valid reminder
- **WHEN** the organizer shortens reservation validity to 5 days on a tournament whose reminder day is 7
- **THEN** the update is rejected, since the combination would stop reminders being sent

### Requirement: Variable symbol series
Each tournament SHALL carry a VS year and a VS series, which together form the prefix of every variable symbol it issues. The VS year SHALL be taken from the tournament's date when the series is assigned, so that an event held in January belongs to that January's year even when it is created and sells out during the preceding year. The VS series SHALL be an integer from 1 to 99 and SHALL be unique among the tournaments sharing a VS year.

The series SHALL be assigned automatically when the tournament is created, as the lowest value not already taken for its year. It SHALL NOT be editable by the organizer at any point. The Setup phase SHALL state the assigned series and the resulting variable-symbol prefix so the organizer can see what payers will quote, presented as a fact about the tournament rather than as a field. A change to the tournament's date before its first registration MAY reassign the year and series; once the tournament has its first registration, both SHALL be fixed, a later change to the date SHALL NOT reassign either, and no already-issued variable symbol SHALL be renumbered. A tournament whose date later moves into another year therefore keeps its original prefix, which is correct because nothing routes on the prefix.

Assigning a series SHALL fail with a clear message naming the exhausted year when every value from 1 to 99 is already taken for that year, rather than assigning a duplicate or an out-of-range value.

#### Scenario: Series assigned on creation
- **WHEN** an organizer creates the first tournament dated in 2026
- **THEN** it is assigned VS year 2026 and series 1, and its Setup shows the variable-symbol prefix 2601

#### Scenario: Lowest free series taken
- **WHEN** a new tournament is created for a year in which series 1 and 3 are taken
- **THEN** it is assigned series 2

#### Scenario: Series taken from the tournament date, not the creation date
- **WHEN** an organizer creates a tournament in November 2026 for a date in January 2027
- **THEN** its VS year is 2027 and its series is the lowest free value among 2027 tournaments

#### Scenario: Series presented, not offered for editing
- **WHEN** the organizer opens the `PAYMENTS` tab on a tournament with no registrations
- **THEN** the series and its prefix are stated as read-only text, with no input, and the tab's save control counts no pending change for them

#### Scenario: Date change before registrations reassigns
- **WHEN** a tournament with no registrations has its date moved into another year
- **THEN** it is reassigned the lowest free series for the new year and the stated prefix follows

#### Scenario: Date change after registrations does not renumber
- **WHEN** a tournament with registrations has its date moved from December 2026 into January 2027
- **THEN** its VS year and series are unchanged, every issued variable symbol keeps its value, and newly issued symbols continue on the same prefix

#### Scenario: Year exhausted
- **WHEN** a tournament is created for a year that already holds 99 tournaments
- **THEN** creation is refused with a message naming the exhausted year

### Requirement: Organizer authorization
Each tournament SHALL have exactly one Tournament Owner (initially the creator) and a team of Tournament Organizers. Console access SHALL be restricted to the Tournament Owner and team members. The Tournament Owner SHALL manage the team: adding any existing account by email (no global role required) and removing members. Team membership grants full console access; ownership additionally grants team management, ownership transfer, and delete/cancel.

#### Scenario: Unauthorized user
- **WHEN** a signed-in account that is neither the Tournament Owner nor a team member opens the tournament's console
- **THEN** access is denied

#### Scenario: Owner adds a team member
- **WHEN** the Tournament Owner adds a fencer's account to the team by email
- **THEN** that account gains full console access to the tournament without needing any global role

#### Scenario: Team member cannot manage the team
- **WHEN** a Tournament Organizer who is not the owner attempts to add or remove team members
- **THEN** the request is rejected with an authorization error

### Requirement: In-app tournament creation
An account holding the global Organizer role or higher SHALL be able to create a tournament from the tournament picker via a minimal dialog asking display name and date. The slug SHALL be auto-derived from the name and be editable before submission. Derivation SHALL append the event's year only when the slugified name does not already carry one: a four-digit group between 1900 and 2099 standing as its own token in the slug counts as a year already present, and in that case the slug is the slugified name alone. The creator SHALL become the tournament's Tournament Owner and land in the console's Setup phase. Accounts below the Organizer role SHALL NOT be able to create tournaments.

#### Scenario: Create from picker
- **WHEN** an account with the Organizer role submits the "New tournament" dialog with a name and date
- **THEN** the tournament is created with the derived slug, the account becomes its Tournament Owner, and the console opens on the Setup phase

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
- **THEN** creation is rejected with a clear error and the user can edit the slug

#### Scenario: Fencer cannot create
- **WHEN** an account with only the Fencer role attempts to create a tournament
- **THEN** creation is rejected with an authorization error

### Requirement: Tournament ownership transfer
The Tournament Owner SHALL be able to transfer ownership to a team member; on transfer the previous owner SHALL remain on the team. A global Admin SHALL be able to assign or reassign a tournament's owner as a fallback (for example when the owner's account is gone or the tournament has no owner).

#### Scenario: Owner hands over
- **WHEN** the Tournament Owner transfers ownership to a team member
- **THEN** that member becomes the Tournament Owner and the previous owner remains a Tournament Organizer

#### Scenario: Admin fallback
- **WHEN** a global Admin assigns a new owner to a tournament whose owner account is unavailable
- **THEN** the designated account becomes the Tournament Owner

### Requirement: Tournament deletion and cancellation
The Tournament Owner SHALL be able to hard-delete a tournament only while it has no registrations of any state. Once registrations exist, the owner SHALL instead be able to cancel the tournament: a cancelled tournament is hidden from public listings, rejects new registrations, and retains all data including financial history; its console remains accessible.

#### Scenario: Delete while empty
- **WHEN** the Tournament Owner deletes a tournament with no registrations
- **THEN** the tournament and its configuration are removed

#### Scenario: Delete blocked by registrations
- **WHEN** the Tournament Owner attempts to hard-delete a tournament that has registrations
- **THEN** deletion is rejected and cancellation is offered instead

#### Scenario: Cancelled tournament
- **WHEN** the Tournament Owner cancels a tournament with registrations
- **THEN** the tournament disappears from public listings, new registrations are rejected, and the console and all existing data remain accessible

### Requirement: Registration window
A tournament SHALL have optional registration-opens and registration-closes dates. Registration SHALL be unavailable before the opens date (when set) and after the closes date (when set); with no closes date, registration stays available until the tournament date. With no opens date, registration is available as soon as setup is complete.

A tournament SHALL additionally have an optional amendments-close date, after which fencers may no longer amend their registrations even while registration itself remains open. With no amendments-close date set, amendment SHALL be available on exactly the same window as registration. When both are set, the amendments-close date MUST NOT fall after the registration-closes date, and the combination SHALL be rejected with a clear message — a later value would never be reached.

#### Scenario: Before opening
- **WHEN** a fencer visits registration before the registration-opens date
- **THEN** registration is unavailable and the opening date is shown

#### Scenario: No close date set
- **WHEN** no registration-closes date is set
- **THEN** registration remains available through the tournament date

#### Scenario: Amendments close before registration
- **WHEN** the organizer sets an amendments-close date two weeks before the registration-closes date
- **THEN** fencers may still register in those two weeks but may no longer amend an existing registration

#### Scenario: Amendments follow registration by default
- **WHEN** no amendments-close date is set
- **THEN** amendment is available exactly while registration is available

#### Scenario: Amendments-close after registration-close rejected
- **WHEN** the organizer sets an amendments-close date later than the registration-closes date
- **THEN** the update is rejected with a message naming the conflict

### Requirement: Setup completeness
Mandatory setup SHALL comprise: display name, date, location, at least one titular organizer, at least one discipline with a unit price, and — whenever the tournament prices in EUR as a second currency — every rendered EUR price field: each discipline's EUR price, each extra item's EUR price, and the EUR amount of each fixed discount. A tournament still pricing through the legacy fixed weapon-rental/afterparty parameters SHALL be reported as blocked from enabling EUR, naming those parameters and directing the organizer to itemized extra services. The recorded exchange ratio is a Setup convenience only and is never part of completeness. The Setup phase SHALL show a completeness checklist naming each missing item. A tournament with incomplete mandatory setup SHALL NOT accept registrations.

#### Scenario: Checklist shows gaps
- **WHEN** the organizer opens Setup for a tournament without location and without discipline prices
- **THEN** the checklist lists location and the missing unit prices as blocking registration

#### Scenario: Missing EUR price blocks registration
- **WHEN** a CZK + EUR tournament has a discipline whose EUR price is empty
- **THEN** the checklist lists the missing EUR price and registration is unavailable, with no separate exchange-rate requirement

#### Scenario: Legacy fixed fees block EUR
- **WHEN** the organizer enables EUR on a tournament still pricing through the fixed weapon-rental or afterparty parameters
- **THEN** the checklist names those parameters as blocking EUR and directs the organizer to itemized extra services

#### Scenario: Setup completed
- **WHEN** the last mandatory item is filled
- **THEN** the checklist reports the tournament ready and registration becomes available (subject to the registration window)

### Requirement: Price columns labelled uniformly
Every price column the organizer edits in Setup — on the disciplines table, the
extra-items table, and the fixed-amount rows of the discount list — SHALL be labelled
"unit price", naming its currency where the tournament prices in two. No such column
SHALL be labelled "fee" or "price". The label SHALL be localized like all other
user-facing text.

#### Scenario: Disciplines and extras agree
- **WHEN** the organizer moves between the `DISCIPLINES` and `EXTRA` tabs on a CZK + EUR tournament
- **THEN** both price columns are headed "unit price" with their currency, and neither is headed "fee" or "price"

#### Scenario: Single-currency tournament
- **WHEN** the tournament prices in one currency
- **THEN** each price column is headed "unit price" with that currency and no EUR column is shown

### Requirement: Logo control is a tertiary text action
The logo upload and removal controls on `TOURNAMENT` SHALL be presented as tertiary
underlined text actions, in the same treatment as "add organizer", rather than as
buttons. This keeps them visibly distinct from the tab's save control, which is the
only element on the tab styled as a primary action.

#### Scenario: Upload offered as a text action
- **WHEN** the organizer looks at the logo control
- **THEN** the upload is an underlined text action matching "add organizer", not a button, and choosing a file uploads it as before

#### Scenario: Removal matches the upload
- **WHEN** the tournament has a logo
- **THEN** its removal control is presented in the same tertiary treatment as the upload
