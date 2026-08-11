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
A tournament SHALL be defined by internal name, display name, an optional subtitle, an optional logo, date, communication language, location (free text), an optional description, a qualification statement, a list of titular organizers, and a set of disciplines. The subtitle is free text that MAY be longer than the display name and is frequently empty; every presentation of the tournament SHALL render correctly whether or not the subtitle is set. The logo is an optional image supplied by the organizer, stored with the tournament and served for display; the system SHALL bound its size on upload (reject oversized uploads and re-encode to a bounded image) so it stays small. The description is optional free-form text of arbitrary length, authored in markdown and stored verbatim as its markdown source; it SHALL be presented as formatted content according to `organizer-prose`, which fixes the honored subset, the sanitizer allowlist, and the presentation rules. Titular organizers are free-text names of clubs or other entities shown publicly as the tournament's organizers, each with an optional link; they are independent of account-based console access.

Each discipline SHALL have a slug identifying it within the tournament, a human-readable name, a classification of weapon × gender × material, a **kind** (individual or team), a capacity limit, a unit price, optional schedule fields (`when`, `where`) mainly for multi-day events, and an optional ruleset consisting of a short style name and an optional external link. Slug, classification, and the derived taxonomy code are fixed by `discipline-identity`, which also fixes that a tournament MAY offer several disciplines classified alike and that a weapon outside the HEMA taxonomy is accepted. A **team** discipline SHALL additionally have a minimum and a maximum roster size; for it, the capacity limit counts teams rather than fencers and the unit price is the price of entering one team, as fixed by `team-disciplines`. An **individual** discipline is the default and behaves exactly as disciplines behaved before team disciplines existed. In the console, a discipline SHALL be identified by its name in emphasized text with its slug alongside it in faded ink, and each of its optional fields (`when`, `where`, ruleset name, ruleset link) SHALL carry a help hint stating what belongs in it; the capacity and price columns SHALL be labelled according to the row's kind, so that a team row states that its capacity counts teams and its price is charged per team.

A discipline's identity — its kind, material, weapon, gender, name, and slug — SHALL be entered in a dialog and SHALL NOT be offered as controls in the discipline row. The dialog SHALL open when the organizer adds a discipline, with kind defaulting to individual, material to steel, and gender to open, so that the ordinary discipline is settled by choosing a weapon alone. Its weapon field SHALL offer the taxonomy weapons and SHALL also accept a weapon they do not name. Confirming the dialog SHALL add or update the row in the tab's draft; cancelling it SHALL change nothing. The dialog SHALL prefill the name and the slug from the kind and classification chosen above them, SHALL keep each in step as those choices change, and SHALL stop prefilling either one once the organizer has typed into that field, independently of the other. The slug field SHALL carry a help hint stating that the slug names the discipline in exports and spreadsheets and is not shown to fencers. The dialog SHALL warn when the name it holds is already used by another discipline of that tournament, whether saved or merely drafted, and SHALL allow the organizer to confirm anyway.

The discipline row SHALL present the name and the slug as text rather than as controls, and SHALL offer as editable controls only the capacity, the unit prices, and the row's own optional fields. A discipline whose identity is not frozen (`discipline-identity`) SHALL offer a control that reopens the dialog on it. A discipline whose identity is frozen SHALL offer no such control, and the console SHALL determine which case applies from the discipline's reported frozen state rather than by attempting an edit. Editing a discipline's slug SHALL be counted among the tab's unsaved changes and SHALL be written to the discipline it was made on, notwithstanding that the slug is what identifies the discipline to the server.

Subtitle, logo, description, qualification, disciplines (including their slug, classification, kind, roster bounds, schedule and ruleset fields) and titular organizers SHALL be editable in the console Setup phase, disciplines and organizers as row tables with add and remove. The communication language SHALL NOT be editable in Setup: it is assigned when the tournament is created and thereafter governs fencer emails without being offered as a settings field. The Setup section carrying the tournament's own identity fields SHALL NOT be given a section heading of its own, and SHALL present those fields in this order: display name, subtitle, logo, date, location, description, qualification statement, registration opens, registration closes, registration instructions.

#### Scenario: Organizer configures disciplines
- **WHEN** the organizer adds an open longsword and a women's sabre through the discipline dialog, giving each a capacity and a unit price in its row
- **THEN** registration offers exactly those disciplines under those capacity constraints at those prices, each with a generated slug

#### Scenario: Adding a discipline opens the dialog
- **WHEN** the organizer adds a discipline
- **THEN** a dialog opens offering kind, material, weapon, gender, name and slug, with individual, steel and open already chosen

#### Scenario: Dialog cancelled changes nothing
- **WHEN** the organizer opens the discipline dialog, fills it, and cancels
- **THEN** no row is added, and the tab reports no further unsaved changes than before

#### Scenario: Name and slug prefill from the choices above them
- **WHEN** the organizer chooses longsword and then women in the dialog
- **THEN** the name and the slug both update to match the classification as each choice is made, without the organizer typing in either field

#### Scenario: Prefill stops at the field the organizer typed in
- **WHEN** the organizer types a name of their own and then changes the weapon
- **THEN** the typed name is left as typed and the slug still follows the new weapon

#### Scenario: Duplicate name warned, not refused
- **WHEN** the dialog holds a name that another discipline of the same tournament already uses, including one added in the same unsaved session
- **THEN** a warning states that the name is already in use, and the organizer can still confirm the dialog

#### Scenario: Row carries no identity controls
- **WHEN** the organizer looks at a saved discipline row
- **THEN** its name and slug are text, no weapon, gender, material or kind control appears in it, and the editable controls are its capacity, its prices and its optional fields

#### Scenario: Organizer configures two tiers of one weapon
- **WHEN** the organizer adds two longsword disciplines, names them for the top and open brackets, and gives each its own capacity and price
- **THEN** both rows are accepted with distinct slugs, and registration offers them as two separate entries

#### Scenario: Organizer configures a team discipline
- **WHEN** the organizer adds a discipline, sets its kind to team in the dialog, and gives it capacity 8, roster bounds 3 and 4, and a price
- **THEN** the row offers the roster bounds, its capacity is labelled as counting teams and its price as charged per team, and registration offers it as a team entry

#### Scenario: Organizer configures a team discipline alongside its individual counterpart
- **WHEN** the organizer adds an individual longsword discipline and a team longsword discipline with roster bounds 3 and 4
- **THEN** both are accepted, the team row's capacity is labelled as counting teams and its price as charged per team, and neither is rejected as a duplicate

#### Scenario: Organizer enters a weapon the taxonomy does not name
- **WHEN** the organizer adds a discipline whose weapon is Messer and gives it a name
- **THEN** the row is accepted and the discipline is offered like any other

#### Scenario: Identity reopened while unreferenced
- **WHEN** the organizer reopens the dialog on a discipline no fencer has entered, changes its weapon and its slug, and saves the tab
- **THEN** both changes are written to that discipline, and the row shows the new name and slug

#### Scenario: A changed slug is not lost
- **WHEN** the organizer changes an unreferenced discipline's slug and saves the tab
- **THEN** the change is counted among the tab's unsaved changes before the save and is written to the discipline it was made on, rather than being dropped as though nothing had changed

#### Scenario: No edit control once frozen
- **WHEN** a fencer has entered a discipline
- **THEN** that row offers no control reopening its dialog, while a row nobody has entered still offers one

#### Scenario: Someone registers while the dialog's changes are still drafted
- **WHEN** the organizer changes a discipline's slug in the dialog, a fencer enters that discipline before the tab is saved, and the organizer then saves
- **THEN** the save reports against that row that the discipline can no longer be changed because it has been entered, the change stays pending, and the tournament's other pending changes are unaffected

#### Scenario: Slug explains itself
- **WHEN** the organizer reaches the help marker next to the slug field in the discipline dialog
- **THEN** a hint appears stating that the slug names the discipline in exports and spreadsheets and is not shown to fencers

#### Scenario: Roster bounds offered only for team rows
- **WHEN** the organizer sets a discipline's kind to individual in the dialog
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

#### Scenario: Organizer with a link
- **WHEN** a titular organizer row carries a link and another leaves it empty
- **THEN** the first is presented as a link on the organizer's name and the second as plain text, and both are stored with the tournament

#### Scenario: Description written and presented
- **WHEN** the organizer writes a multi-paragraph markdown description in Setup and saves
- **THEN** the markdown source is stored verbatim and presented as formatted content — paragraph breaks intact, headings, lists, emphasis and links rendered, and nothing outside the honored subset rendered as markup

#### Scenario: Description written without markdown
- **WHEN** the organizer writes a plain multi-paragraph description using no markdown markers
- **THEN** it is presented with its paragraph breaks and line breaks intact, exactly as before markdown authoring was introduced

### Requirement: Discipline dialog reopens on the discipline's own values
WHEN the discipline dialog is reopened on an existing discipline, it SHALL show that discipline's stored name and stored slug as they are, and SHALL NOT replace either with a value derived from its classification. Derivation governs a discipline being added, not one being reopened: on a reopened discipline it SHALL resume only for a field the organizer has since cleared or for a field that changes because the organizer alters the kind or the classification in this dialog session.

Confirming a reopened dialog without touching its name or slug SHALL therefore leave both exactly as they were stored, and the tab SHALL count no unsaved change on their account.

#### Scenario: Reopened dialog states the stored values
- **WHEN** the organizer reopens the dialog on a discipline whose name and slug they had overridden as "Top bracket" and `LS-A`
- **THEN** the dialog shows "Top bracket" and `LS-A`, not the name and slug its classification would generate

#### Scenario: Reopening and confirming changes nothing
- **WHEN** the organizer reopens a discipline's dialog and confirms it without editing a field
- **THEN** the row's name and slug are unchanged and the tab reports no further unsaved changes than before

#### Scenario: Classification change still moves the derived fields
- **WHEN** the organizer reopens a discipline that carries generated identity and changes its weapon
- **THEN** the name and the slug follow the new weapon, exactly as they do while adding a discipline

#### Scenario: An overridden field is not recaptured by derivation
- **WHEN** the organizer reopens a discipline whose slug they had overridden and changes its gender
- **THEN** the name follows the new classification and the overridden slug is left as stored

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

### Requirement: Seating deadline
The organizer SHALL be able to set a **seating deadline**: the date on which the tournament's seating settles. It is distinct from the registration close, and the difference SHALL be stated where it is configured:

- **registration close** — the hard boundary; after it no registration is accepted at all;
- **seating deadline** — a soft boundary inside it; after it registration is still accepted but grants only a place in the substitute queue, and any money still owed on a seated registration has become overdue.

The seating deadline SHALL be optional. Unset, it SHALL resolve to the registration close, which itself resolves to the tournament date — so a tournament with no explicit deadline settles its seating when registration closes and has no organizer-managed tail.

A seating deadline later than the registration close SHALL be rejected, since it could never be reached.

The seating deadline SHALL apply to the whole tournament, never to an individual discipline.

#### Scenario: Deadline set within the registration window
- **WHEN** the organizer sets a seating deadline four weeks before the registration close
- **THEN** it is accepted, and registrations submitted after it join the substitute queue

#### Scenario: Deadline after registration close rejected
- **WHEN** the organizer sets a seating deadline later than the registration close
- **THEN** the update is rejected with a message naming both dates

#### Scenario: Deadline left unset
- **WHEN** the organizer saves a tournament with no seating deadline
- **THEN** seating settles at the registration close, and no separate deadline is presented to fencers

#### Scenario: Deadline distinguished from registration close in setup
- **WHEN** the organizer views the payment and reservation parameters
- **THEN** the seating deadline is labelled and explained so it cannot be mistaken for the registration close

### Requirement: Bank account entry and storage
The bank account SHALL be accepted in either of two forms: an IBAN, or the Czech domestic form `[prefix-]number/bankcode` with a prefix of up to six digits that MAY be omitted, an account number of two to ten digits, and a four-digit bank code. An organizer SHALL NOT be required to look up an IBAN to configure a Czech tournament, because the domestic form is the one printed on statements and used in domestic transfers, while the IBAN appears in neither.

A Czech account entered in domestic form SHALL be converted to its IBAN and stored as that IBAN, so that the stored value is always canonical and every consumer of the account sees exactly one format. The conversion SHALL be the standard mapping — bank code, then the prefix padded to six digits, then the account number padded to ten — with check digits computed rather than supplied. No second form SHALL be stored, since the domestic form is recoverable from a Czech IBAN whenever it is needed.

The account SHALL be validated, not merely shape-checked. An IBAN SHALL satisfy its mod-97 check digits. A Czech account entered in domestic form SHALL satisfy the weighted modulo-11 checksum on its prefix and on its account number independently, both of which every genuine Czech account satisfies. An account failing either check SHALL be refused with a message naming the check that failed, rather than being stored, printed into payment emails, and encoded into a QR code that fails at the payer's bank. The bank code SHALL be checked for shape only and SHALL NOT be validated against a registry of live codes, which would rot.

Only the Czech domestic form SHALL be accepted alongside IBAN. An account in any other country SHALL be entered as its IBAN.

An account stored before this validation existed SHALL NOT be re-validated or rejected on read, and SHALL continue to be used exactly as it is.

#### Scenario: Domestic account accepted and stored as IBAN
- **WHEN** the organizer saves the bank account as `19-2000145399/0800`
- **THEN** the save succeeds and the stored value is the corresponding IBAN

#### Scenario: Domestic account without a prefix
- **WHEN** the organizer saves an account with no prefix, as `2000145399/0800`
- **THEN** it is accepted and converted with a zero prefix

#### Scenario: IBAN accepted unchanged
- **WHEN** the organizer saves a valid IBAN
- **THEN** it is stored as given, normalized only for spacing and case

#### Scenario: Both forms of one account are the same account
- **WHEN** the organizer saves an account in domestic form, and later saves the IBAN that account converts to
- **THEN** the stored value is identical in both cases

#### Scenario: Mistyped IBAN refused
- **WHEN** the organizer saves an IBAN whose check digits do not agree with the rest of the value
- **THEN** the save is refused, naming the failed check, and nothing is stored

#### Scenario: Mistyped domestic account refused
- **WHEN** the organizer saves a domestic account whose account number fails the modulo-11 checksum
- **THEN** the save is refused, naming the failed check, and nothing is stored

#### Scenario: Foreign account entered as IBAN
- **WHEN** the organizer of a tournament banking outside Czechia saves that account as an IBAN
- **THEN** it is accepted, and no domestic form is required or derived

#### Scenario: Existing account is left alone
- **WHEN** a tournament whose account was stored before this validation is loaded and used to build payment instructions
- **THEN** the account is used as stored and no validation refuses it

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
Each tournament SHALL have exactly one Tournament Owner (initially the creator) and a team of Tournament Organizers. Console access SHALL be restricted to the Tournament Owner and team members. The Tournament Owner SHALL manage the team: adding any existing account by email (no global role required) and removing members. Team membership grants full console access, including publishing the tournament; ownership additionally grants team management, ownership transfer, and delete/cancel.

#### Scenario: Unauthorized user
- **WHEN** a signed-in account that is neither the Tournament Owner nor a team member opens the tournament's console
- **THEN** access is denied

#### Scenario: Owner adds a team member
- **WHEN** the Tournament Owner adds a fencer's account to the team by email
- **THEN** that account gains full console access to the tournament without needing any global role

#### Scenario: Team member cannot manage the team
- **WHEN** a Tournament Organizer who is not the owner attempts to add or remove team members
- **THEN** the request is rejected with an authorization error

#### Scenario: Team member may publish
- **WHEN** a Tournament Organizer who is not the owner publishes a setup-complete tournament
- **THEN** the tournament is published and the publication record names that account

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
