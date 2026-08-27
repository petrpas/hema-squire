## MODIFIED Requirements

### Requirement: Tournament definition
A tournament SHALL be defined by internal name, display name, an optional subtitle, an optional logo, date, communication language, location (free text), an optional description, a qualification statement, a list of titular organizers, and a set of disciplines. The subtitle is free text that MAY be longer than the display name and is frequently empty; every presentation of the tournament SHALL render correctly whether or not the subtitle is set. The logo is an optional image supplied by the organizer, stored with the tournament and served for display; the system SHALL bound its size on upload (reject oversized uploads and re-encode to a bounded image) so it stays small. The description is optional free-form text of arbitrary length, authored in markdown and stored verbatim as its markdown source; it SHALL be presented as formatted content according to `organizer-prose`, which fixes the honored subset, the sanitizer allowlist, and the presentation rules. Titular organizers are free-text names of clubs or other entities shown publicly as the tournament's organizers, each with an optional link; they are independent of account-based console access.

Each discipline SHALL have a slug identifying it within the tournament, a human-readable name, a classification of weapon × gender × material, a **kind** (individual or team), a capacity limit, a unit price, optional schedule fields (`when`, `where`) mainly for multi-day events, and an optional ruleset. The ruleset is a single inline-markdown field (`organizer-prose`), not a name-and-link pair: because it MAY carry more than one link, rules published in several languages are each reachable from it. Slug, classification, and the derived taxonomy code are fixed by `discipline-identity`, which also fixes that a tournament MAY offer several disciplines classified alike and that a weapon outside the HEMA taxonomy is accepted. A **team** discipline SHALL additionally have a minimum and a maximum roster size; for it, the capacity limit counts teams rather than fencers and the unit price is the price of entering one team, as fixed by `team-disciplines`. An **individual** discipline is the default and behaves exactly as disciplines behaved before team disciplines existed. In the console, a discipline SHALL be identified by its name in emphasized text with its slug alongside it in faded ink, and each of its optional fields (`when`, `where`, ruleset) SHALL carry a help hint stating what belongs in it; the capacity and price columns SHALL be labelled according to the row's kind, so that a team row states that its capacity counts teams and its price is charged per team.

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
- **WHEN** the organizer sets a discipline's when to "Saturday", where to "Main Hall — Kurtzstrasse 21", and its ruleset to `[Barbasetti Right of Way](https://example.com/cz.pdf) (CZ) · [EN](https://example.com/en.pdf)`
- **THEN** the tournament information presents that discipline with its schedule and both ruleset links, and omits those lines for disciplines that leave them empty

#### Scenario: One field, no separate link column
- **WHEN** the organizer looks at a discipline row in Setup
- **THEN** it offers one ruleset field and no separate ruleset-link field, and a ruleset saved before this change is shown as the markdown source it was folded into

#### Scenario: Optional discipline fields explain themselves
- **WHEN** the organizer reaches the help marker next to a discipline's `when`, `where`, or ruleset field
- **THEN** a hint appears describing what belongs in that field (for example, for `when`: that it takes a rough time such as "Saturday morning"), and the ruleset's hint states the link form so an organizer knows a link can be written into it

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
