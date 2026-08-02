## MODIFIED Requirements

### Requirement: Tournament definition
A tournament SHALL be defined by internal name, display name, an optional subtitle, an optional logo, date, communication language, location (free text), an optional description, a qualification statement, a list of titular organizers, and a set of disciplines. The subtitle is free text that MAY be longer than the display name and is frequently empty; every presentation of the tournament SHALL render correctly whether or not the subtitle is set. The logo is an optional image supplied by the organizer, stored with the tournament and served for display; the system SHALL bound its size on upload (reject oversized uploads and re-encode to a bounded image) so it stays small. The description is optional free-form text of arbitrary length, authored in markdown and stored verbatim as its markdown source; it SHALL be presented as formatted content according to `organizer-prose`, which fixes the honored subset, the sanitizer allowlist, and the presentation rules. Titular organizers are free-text names of clubs or other entities shown publicly as the tournament's organizers, each with an optional link; they are independent of account-based console access.

Each discipline SHALL have a code and human-readable name drawn from the HEMA taxonomy (weapon LS/SA/RA/RD/SB × gender Open/Women/Men × material Steel/Plastic), a **kind** (individual or team), a capacity limit, a unit price, optional schedule fields (`when`, `where`) mainly for multi-day events, and an optional ruleset consisting of a short style name and an optional external link. A **team** discipline SHALL additionally have a minimum and a maximum roster size; for it, the capacity limit counts teams rather than fencers and the unit price is the price of entering one team, as fixed by `team-disciplines`. An **individual** discipline is the default and behaves exactly as disciplines behaved before team disciplines existed. In the console, a discipline SHALL be identified by its name in emphasized text, and each of its optional fields (`when`, `where`, ruleset name, ruleset link) SHALL carry a help hint stating what belongs in it; the capacity and price columns SHALL be labelled according to the row's kind, so that a team row states that its capacity counts teams and its price is charged per team.

Subtitle, logo, description, qualification, disciplines (including their kind, roster bounds, schedule and ruleset fields) and titular organizers SHALL be editable in the console Setup phase, disciplines and organizers as row tables with add and remove. The communication language SHALL NOT be editable in Setup: it is assigned when the tournament is created and thereafter governs fencer emails without being offered as a settings field. The Setup section carrying the tournament's own identity fields SHALL NOT be given a section heading of its own, and SHALL present those fields in this order: display name, subtitle, logo, date, location, description, qualification statement, registration opens, registration closes, registration instructions.

#### Scenario: Organizer configures disciplines
- **WHEN** the organizer adds disciplines LS and SAW in the Setup table, each with a capacity and a unit price
- **THEN** registration offers exactly those disciplines under those capacity constraints at those prices

#### Scenario: Organizer configures a team discipline
- **WHEN** the organizer adds a discipline, sets its kind to team, and gives it capacity 8, roster bounds 3 and 4, and a price
- **THEN** the row offers the roster bounds, its capacity is labelled as counting teams and its price as charged per team, and registration offers it as a team entry

#### Scenario: Roster bounds offered only for team rows
- **WHEN** the organizer sets a discipline row's kind to individual
- **THEN** the row offers no roster bounds, and any previously entered bounds are not required

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

### Requirement: Pricing configuration
The system SHALL compute registration totals from categorized billable items and an ordered discount list.

Items: every billable item SHALL have a name, a price, and a category. In local + EUR mode every billable item SHALL additionally have a EUR price, stored independently of its local price. Disciplines are items of category `discipline`, priced on their Setup rows, with standard and early-bird prices in each configured currency; a team discipline's price is the price of one team entry and enters the `discipline` category subtotal once per team entered, never multiplied by roster size. Extra services SHALL be organizer-defined rows with a free-text name (for example "afterparty saturday", "castle visit sunday", "t-shirt"), a category from a fixed enum, a price per configured currency, an optional per-registration quantity limit (limit 1 renders as a checkbox, higher limits as a quantity selector), and optional descriptive fields `when`, `where`, and `remark` used when the item is presented informationally. These descriptive fields SHALL NOT affect pricing.

The extra-service category enum SHALL be `seminar`, `rental`, `afterparty`, `merch`, `other_action`, and `other_item`, and SHALL divide into two kinds: **action** categories (`seminar`, `afterparty`, `other_action`), which happen at a time and place, and **item** categories (`rental`, `merch`, `other_item`), which are goods. For action categories the console SHALL offer `when` and `where` and SHALL NOT offer a quantity limit; their quantity limit SHALL be stored as 1. For item categories the console SHALL offer the quantity limit and SHALL NOT offer `when` or `where`. `remark` SHALL be available for both kinds. `other_action` SHALL behave in every respect as `afterparty` and `seminar` do, and `other_item` as `merch` does. Existing rows in an action category whose stored quantity limit is greater than 1 SHALL retain that value until the row is next saved, so previously computed totals remain reproducible.

Discounts: an ordered list of rows, each with a name, a condition, an effect, and a category scope. Conditions SHALL be drawn from an extensible enumeration, initially: registered discipline count equals N, and registration date on or before a configured date (early bird). The discipline-count condition SHALL count **individual** discipline entries only; team entries SHALL NOT contribute to it, because the condition asks how many events the fencer themselves entered. A discount scoped to the `discipline` category SHALL nevertheless apply to team fees, since scope asks what the money is for. Effects SHALL be a fixed amount or a percentage. A fixed-amount effect SHALL carry an amount per configured currency, since a fixed discount is a price decision like any other; a percentage effect is currency-neutral and SHALL carry a single value. The total SHALL be computed **independently for each configured currency**, in each case by summing that currency's selected item prices, subtracting that currency's applicable fixed discounts from their scoped category subtotals (floored at zero), then applying applicable percentage discounts sequentially to their scoped subtotals, and finally rounding half-up to a whole currency unit exactly once. The category scope SHALL be stored per discount from the start (defaulting to `discipline`), even while the Setup UI does not yet expose a scope picker, and SHALL accept every category in the enum.

The totals produced for the two currencies are independent results of the same computation over different inputs, and SHALL NOT be expected or required to correspond at any exchange ratio.

Tournaments with no extra-service items and no discounts SHALL keep the legacy computation (per-discipline fees, `fee_early`, and the fixed weapon-rental/afterparty parameters) so that historical totals remain reproducible. The fixed weapon-rental and afterparty parameters SHALL remain single-currency; a tournament whose pricing still uses them SHALL NOT be able to enable EUR, and the completeness checklist SHALL name them and direct the organizer to itemized extra services.

#### Scenario: Count discount applied
- **WHEN** disciplines are priced 30 € each and a discount row "−10 € when 2 disciplines" exists, and a fencer registers for two disciplines
- **THEN** the discipline part of the total is 50 €, not 60 €

#### Scenario: Team entry does not satisfy a count condition
- **WHEN** a discount applies at a discipline count of 2 and a fencer enters one individual discipline and one team
- **THEN** the discount does not apply

#### Scenario: Discipline-scoped discount reaches a team fee
- **WHEN** a percentage discount scoped to `discipline` applies and the registration carries a team fee
- **THEN** the team fee is part of the subtotal the discount reduces

### Requirement: Registration window
A tournament SHALL have optional registration-opens and registration-closes dates. Registration SHALL be unavailable before the opens date (when set) and after the closes date (when set); with no closes date, registration stays available until the tournament date. With no opens date, registration is available as soon as setup is complete.

A tournament SHALL additionally have an optional amendments-close date, after which fencers may no longer amend their registrations even while registration itself remains open. With no amendments-close date set, amendment SHALL be available on exactly the same window as registration. When both are set, the amendments-close date MUST NOT fall after the registration-closes date, and the combination SHALL be rejected with a clear message — a later value would never be reached.

A tournament SHALL additionally have an optional team composition deadline, editable in Setup and constrained only to be a date on or before the tournament date. It SHALL be independent of the registration and amendment windows in both directions: it MAY fall before or after either, and no combination of the three SHALL be rejected on account of their order. It governs nothing but the check and the reminder fixed by `team-disciplines`, and SHALL have no effect on a tournament that offers no team discipline.

#### Scenario: Before opening
- **WHEN** a fencer visits registration before the registration-opens date
- **THEN** registration is unavailable and the opening date is shown

#### Scenario: No close date set
- **WHEN** no registration-closes date is set
- **THEN** registration remains available through the tournament date

#### Scenario: Amendments close before registration
- **WHEN** the organizer sets an amendments-close date two weeks before the registration-closes date
- **THEN** fencers may still register in those two weeks but may no longer amend an existing registration

#### Scenario: Composition deadline after amendments close
- **WHEN** the organizer sets a composition deadline four weeks after the amendments-close date
- **THEN** the combination is accepted, and rosters stay editable after amendments have closed

### Requirement: Setup completeness
Mandatory setup SHALL comprise: display name, date, location, at least one titular organizer, at least one discipline with a unit price, and — whenever the tournament prices in EUR as a second currency — every rendered EUR price field: each discipline's EUR price, each extra item's EUR price, and the EUR amount of each fixed discount. Every team discipline SHALL additionally have valid roster bounds, and a team discipline missing them SHALL be reported as a missing item. The team composition deadline SHALL NOT be part of mandatory setup: a tournament may offer team disciplines without one. A tournament still pricing through the legacy fixed weapon-rental/afterparty parameters SHALL be reported as blocked from enabling EUR, naming those parameters and directing the organizer to itemized extra services. The recorded exchange ratio is a Setup convenience only and is never part of completeness. The Setup phase SHALL show a completeness checklist naming each missing item. A tournament with incomplete mandatory setup SHALL NOT accept registrations.

#### Scenario: Checklist shows gaps
- **WHEN** the organizer opens Setup for a tournament without location and without discipline prices
- **THEN** the checklist lists location and the missing unit prices as blocking registration

#### Scenario: Missing roster bounds block registration
- **WHEN** a tournament has a team discipline with no roster bounds set
- **THEN** the checklist lists that discipline's roster bounds and registration is unavailable

#### Scenario: Composition deadline never blocks
- **WHEN** a tournament offers a fully configured team discipline and no composition deadline
- **THEN** the checklist reports nothing missing on that account and registration is available

#### Scenario: Missing EUR price blocks registration
- **WHEN** a CZK + EUR tournament has a discipline whose EUR price is empty
- **THEN** the checklist lists the missing EUR price and registration is unavailable, with no separate exchange-rate requirement

#### Scenario: Legacy fixed fees block EUR
- **WHEN** the organizer enables EUR on a tournament still pricing through the fixed weapon-rental or afterparty parameters
- **THEN** the checklist names those parameters as blocking EUR and directs the organizer to itemized extra services
