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
A tournament SHALL be defined by internal name, display name, an optional subtitle, an optional logo, date, communication language, location (free text), a list of titular organizers, and a set of disciplines. The subtitle is free text that MAY be longer than the display name and is frequently empty; every presentation of the tournament SHALL render correctly whether or not the subtitle is set. The logo is an optional image supplied by the organizer, stored with the tournament and served for display; the system SHALL bound its size on upload (reject oversized uploads and re-encode to a bounded image) so it stays small. Titular organizers are free-text names of clubs or other entities shown publicly as the tournament's organizers; they are independent of account-based console access. Each discipline SHALL have a code and human-readable name drawn from the HEMA taxonomy (weapon LS/SA/RA/RD/SB × gender Open/Women/Men × material Steel/Plastic), a capacity limit, a unit price, optional schedule fields (`when`, `where`) mainly for multi-day events, and an optional ruleset consisting of a short style name and an optional external link. Subtitle, logo, disciplines (including their schedule and ruleset fields) and titular organizers SHALL be editable in the console Setup phase, disciplines and organizers as row tables with add and remove.

#### Scenario: Organizer configures disciplines
- **WHEN** the organizer adds disciplines LS and SAW in the Setup table, each with a capacity and a unit price
- **THEN** registration offers exactly those disciplines under those capacity constraints at those prices

#### Scenario: Discipline schedule and ruleset captured
- **WHEN** the organizer sets a discipline's when to "Saturday", where to "Main Hall — Kurtzstrasse 21", and ruleset to "Right of Way" with an external link
- **THEN** the tournament information presents that discipline with its schedule and a ruleset link, and omits those lines for disciplines that leave them empty

#### Scenario: Subtitle and logo optional
- **WHEN** a tournament is saved with a subtitle and a logo, and another is saved with neither
- **THEN** both render correctly wherever the tournament is presented, the first showing its subtitle and logo and the second showing neither

#### Scenario: Oversized logo rejected
- **WHEN** the organizer uploads a logo larger than the configured cap
- **THEN** the upload is rejected with a clear message and no logo is stored

#### Scenario: Titular organizers edited
- **WHEN** the organizer adds "Duelanti od sv. Rocha" as a titular organizer row
- **THEN** the name appears wherever the tournament presents its organizers, without granting any console access

### Requirement: Pricing configuration
The system SHALL compute registration totals from categorized billable items and an ordered discount list.

Items: every billable item SHALL have a name, a price, and a category. Disciplines are items of category `discipline`, priced on their Setup rows. Extra services SHALL be organizer-defined rows with a free-text name (for example "afterparty saturday", "castle visit sunday", "t-shirt"), a category from a fixed enum (`seminar`, `rental`, `afterparty`, `merch`), a price, an optional per-registration quantity limit (limit 1 renders as a checkbox, higher limits as a quantity selector), and optional descriptive fields `when`, `where`, and `remark` used when the item is presented informationally. These descriptive fields SHALL NOT affect pricing.

Discounts: an ordered list of rows, each with a name, a condition, an effect, and a category scope. Conditions SHALL be drawn from an extensible enumeration, initially: registered discipline count equals N, and registration date on or before a configured date (early bird). Effects SHALL be a fixed amount or a percentage. The total SHALL be computed by summing selected item prices, subtracting applicable fixed discounts from their scoped category subtotals (floored at zero), then applying applicable percentage discounts sequentially to their scoped subtotals, and finally rounding half-up to a whole currency unit exactly once. The category scope SHALL be stored per discount from the start (defaulting to `discipline`), even while the Setup UI does not yet expose a scope picker.

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

#### Scenario: Legacy tournament unaffected
- **WHEN** totals are recomputed for a tournament that has no extra-service items and no discounts
- **THEN** the legacy per-discipline fees and fixed extras produce the same totals as before this change

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
Mandatory setup SHALL comprise: display name, date, location, at least one titular organizer, and at least one discipline with a unit price. The Setup phase SHALL show a completeness checklist naming each missing item. A tournament with incomplete mandatory setup SHALL NOT accept registrations.

#### Scenario: Checklist shows gaps
- **WHEN** the organizer opens Setup for a tournament without location and without discipline prices
- **THEN** the checklist lists location and the missing unit prices as blocking registration

#### Scenario: Setup completed
- **WHEN** the last mandatory item is filled
- **THEN** the checklist reports the tournament ready and registration becomes available (subject to the registration window)
