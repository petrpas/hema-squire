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
A tournament SHALL be defined by internal name, display name, an optional subtitle, an optional logo, date, communication language, location (free text), an optional description, a qualification statement, a list of titular organizers, and a set of disciplines. The subtitle is free text that MAY be longer than the display name and is frequently empty; every presentation of the tournament SHALL render correctly whether or not the subtitle is set. The logo is an optional image supplied by the organizer, stored with the tournament and served for display; the system SHALL bound its size on upload (reject oversized uploads and re-encode to a bounded image) so it stays small. The description is optional free-form plain text of arbitrary length, stored and presented verbatim with its line breaks preserved; it SHALL NOT be interpreted as markup of any kind. Titular organizers are free-text names of clubs or other entities shown publicly as the tournament's organizers, each with an optional link; they are independent of account-based console access. Each discipline SHALL have a code and human-readable name drawn from the HEMA taxonomy (weapon LS/SA/RA/RD/SB × gender Open/Women/Men × material Steel/Plastic), a capacity limit, a unit price, optional schedule fields (`when`, `where`) mainly for multi-day events, and an optional ruleset consisting of a short style name and an optional external link. In the console, a discipline SHALL be identified by its name in emphasized text, and each of its optional fields (`when`, `where`, ruleset name, ruleset link) SHALL carry a help hint stating what belongs in it. Subtitle, logo, description, qualification, disciplines (including their schedule and ruleset fields) and titular organizers SHALL be editable in the console Setup phase, disciplines and organizers as row tables with add and remove. The Setup section carrying the tournament's own identity fields SHALL NOT be given a section heading of its own.

#### Scenario: Organizer configures disciplines
- **WHEN** the organizer adds disciplines LS and SAW in the Setup table, each with a capacity and a unit price
- **THEN** registration offers exactly those disciplines under those capacity constraints at those prices

#### Scenario: Discipline schedule and ruleset captured
- **WHEN** the organizer sets a discipline's when to "Saturday", where to "Main Hall — Kurtzstrasse 21", and ruleset to "Right of Way" with an external link
- **THEN** the tournament information presents that discipline with its schedule and a ruleset link, and omits those lines for disciplines that leave them empty

#### Scenario: Optional discipline fields explain themselves
- **WHEN** the organizer reaches the help marker next to a discipline's `when`, `where`, ruleset name, or ruleset link field
- **THEN** a hint appears describing what belongs in that field (for example, for `when`: that it takes a rough time such as "Saturday morning")

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
- **WHEN** the organizer writes a multi-paragraph description in Setup and saves
- **THEN** the description is stored as plain text and presented with its paragraph breaks intact, with no markup interpreted and no HTML rendered from its content

### Requirement: Registration instructions
A tournament SHALL have an optional multiline free-text `registration instructions` field, editable in the Setup phase and distinct from the public description. It SHALL be presented only on the registration form, with line breaks preserved and no markup interpretation. It SHALL NOT be part of mandatory setup, and its absence SHALL NOT change any other presentation.

#### Scenario: Instructions shown on the form only
- **WHEN** the organizer fills registration instructions and a fencer opens the tournament
- **THEN** the instructions appear on the registration form and do not appear on the information screen

#### Scenario: Instructions absent
- **WHEN** a tournament has no registration instructions
- **THEN** the registration form renders correctly with no instructions block

#### Scenario: Line breaks preserved
- **WHEN** the instructions contain several paragraphs
- **THEN** they render with their line breaks and no markup is interpreted

### Requirement: Pricing configuration
The system SHALL compute registration totals from categorized billable items and an ordered discount list.

Items: every billable item SHALL have a name, a price, and a category. Disciplines are items of category `discipline`, priced on their Setup rows. Extra services SHALL be organizer-defined rows with a free-text name (for example "afterparty saturday", "castle visit sunday", "t-shirt"), a category from a fixed enum, a price, an optional per-registration quantity limit (limit 1 renders as a checkbox, higher limits as a quantity selector), and optional descriptive fields `when`, `where`, and `remark` used when the item is presented informationally. These descriptive fields SHALL NOT affect pricing.

The extra-service category enum SHALL be `seminar`, `rental`, `afterparty`, `merch`, `other_action`, and `other_item`, and SHALL divide into two kinds: **action** categories (`seminar`, `afterparty`, `other_action`), which happen at a time and place, and **item** categories (`rental`, `merch`, `other_item`), which are goods. For action categories the console SHALL offer `when` and `where` and SHALL NOT offer a quantity limit; their quantity limit SHALL be stored as 1. For item categories the console SHALL offer the quantity limit and SHALL NOT offer `when` or `where`. `remark` SHALL be available for both kinds. `other_action` SHALL behave in every respect as `afterparty` and `seminar` do, and `other_item` as `merch` does. Existing rows in an action category whose stored quantity limit is greater than 1 SHALL retain that value until the row is next saved, so previously computed totals remain reproducible.

Discounts: an ordered list of rows, each with a name, a condition, an effect, and a category scope. Conditions SHALL be drawn from an extensible enumeration, initially: registered discipline count equals N, and registration date on or before a configured date (early bird). Effects SHALL be a fixed amount or a percentage. The total SHALL be computed by summing selected item prices, subtracting applicable fixed discounts from their scoped category subtotals (floored at zero), then applying applicable percentage discounts sequentially to their scoped subtotals, and finally rounding half-up to a whole currency unit exactly once. The category scope SHALL be stored per discount from the start (defaulting to `discipline`), even while the Setup UI does not yet expose a scope picker, and SHALL accept every category in the enum.

Tournaments with no extra-service items and no discounts SHALL keep the legacy computation (per-discipline fees, `fee_early`, and the fixed weapon-rental/afterparty parameters) so that historical totals remain reproducible.

#### Scenario: Count discount applied
- **WHEN** disciplines are priced 30 € each and a discount row "−10 € when 2 disciplines" exists, and a fencer registers for two disciplines
- **THEN** the discipline part of the total is 50 €, not 60 €

#### Scenario: Early bird as percentage discount
- **WHEN** a discount row "−15 % when registered before the early-bird date" exists and a fencer registers in time for two disciplines priced 30 € each with the −10 € count discount
- **THEN** the total is (60 − 10) × 0.85 = 42.5, rounded half-up to 43, and remains reproducible for that reservation

#### Scenario: Extra service with quantity
- **WHEN** the organizer defines "weapon rental" (category `rental`, 2 €, limit 4) and a fencer selects quantity 2
- **THEN** 4 € is added to the total

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

### Requirement: Tournament currency
A tournament SHALL have a primary currency drawn from a closed enumeration, initially `CZK` and `EUR`, defaulting to `CZK`. Every price the organizer configures — discipline unit prices, extra-service prices, fixed discount amounts, legacy fee parameters — and every computed total SHALL be expressed in whole units of that primary currency.

When the primary currency is not `EUR`, the organizer MAY enable EUR payments. Enabling them SHALL require an exchange rate expressed as primary-currency units per 1 EUR, which MUST be greater than zero. Disabling EUR payments SHALL clear the stored rate. When the primary currency is `EUR`, EUR payments SHALL be treated as enabled and no exchange rate SHALL be stored.

The Setup UI SHALL state the rate's direction explicitly and SHALL warn — without blocking the save — when the entered rate falls outside a plausible range.

#### Scenario: Czech tournament enables EUR payments
- **WHEN** the organizer sets the primary currency to CZK, enables EUR payments, and enters 25.5
- **THEN** the tournament stores CZK as its primary currency with EUR payments enabled at 25.5 CZK per EUR

#### Scenario: EUR payments without a rate rejected
- **WHEN** the organizer enables EUR payments on a CZK tournament and leaves the exchange rate empty
- **THEN** the save is rejected with a field-level validation error and no change is stored

#### Scenario: Non-positive rate rejected
- **WHEN** the organizer submits an exchange rate of 0 or a negative number
- **THEN** the save is rejected with a field-level validation error

#### Scenario: EUR-priced tournament stores no rate
- **WHEN** the organizer sets the primary currency to EUR
- **THEN** EUR payments are enabled, no exchange rate is stored, and no second currency figure is presented anywhere

#### Scenario: Disabling EUR payments clears the rate
- **WHEN** the organizer turns EUR payments off on a tournament that had a rate
- **THEN** the rate is cleared and EUR figures stop being presented

#### Scenario: Implausible rate warns but saves
- **WHEN** the organizer enters an exchange rate far outside the plausible range
- **THEN** Setup shows a warning naming the expected direction and the save still succeeds

#### Scenario: Existing tournaments unchanged
- **WHEN** a tournament created before this change is loaded
- **THEN** its primary currency is CZK with EUR payments disabled, and its prices and totals are identical to before

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
Each tournament SHALL carry a qualification statement consisting of an openness flag and optional criteria text. The flag SHALL default to open, so a tournament that never sets it presents as open to everyone. When the organizer marks the tournament as requiring qualification, criteria text SHALL be required and SHALL be free text (for example "national championship placement, HR top 500"); the field SHALL carry a help hint offering such examples. Marking the tournament open again SHALL clear the criteria text. The statement SHALL be editable in the Setup phase between the registration dates and the logo, and SHALL be presented wherever the tournament is described. The statement is informational: it SHALL NOT restrict, block, or flag any registration.

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
Per tournament, the organizer SHALL configure: reservation validity in days, reminder day, amount-matching tolerance in percent, refundable-until date, the bank account used in payment instructions, and the public-list treatment of unpaid registrations.

#### Scenario: Parameters applied
- **WHEN** the organizer sets reservation validity to 10 days and the reminder to day 5
- **THEN** new reservations expire after 10 unpaid days and reminder emails go out on day 5

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
An account holding the global Organizer role or higher SHALL be able to create a tournament from the tournament picker via a minimal dialog asking display name and date. The slug SHALL be auto-derived from name and date and be editable before submission. The creator SHALL become the tournament's Tournament Owner and land in the console's Setup phase. Accounts below the Organizer role SHALL NOT be able to create tournaments.

#### Scenario: Create from picker
- **WHEN** an account with the Organizer role submits the "New tournament" dialog with a name and date
- **THEN** the tournament is created with the derived slug, the account becomes its Tournament Owner, and the console opens on the Setup phase

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

#### Scenario: Before opening
- **WHEN** a fencer visits registration before the registration-opens date
- **THEN** registration is unavailable and the opening date is shown

#### Scenario: No close date set
- **WHEN** no registration-closes date is set
- **THEN** registration remains available through the tournament date

### Requirement: Setup completeness
Mandatory setup SHALL comprise: display name, date, location, at least one titular organizer, at least one discipline with a unit price, and — whenever EUR payments are enabled on a tournament whose primary currency is not EUR — a positive exchange rate. The Setup phase SHALL show a completeness checklist naming each missing item. A tournament with incomplete mandatory setup SHALL NOT accept registrations.

#### Scenario: Checklist shows gaps
- **WHEN** the organizer opens Setup for a tournament without location and without discipline prices
- **THEN** the checklist lists location and the missing unit prices as blocking registration

#### Scenario: Missing exchange rate blocks registration
- **WHEN** a CZK tournament has EUR payments enabled with no exchange rate
- **THEN** the checklist lists the missing exchange rate and registration is unavailable

#### Scenario: Setup completed
- **WHEN** the last mandatory item is filled
- **THEN** the checklist reports the tournament ready and registration becomes available (subject to the registration window)
