## MODIFIED Requirements

### Requirement: Setup settings are navigated by seven tabs
The Setup phase's settings pane SHALL present its tabs in the fixed order `TOURNAMENT`,
`DISCIPLINES`, `EXTRA`, `TIMELINE`, `PAYMENTS`, `OTHER`, `PUBLISH`, and SHALL show the
sections of exactly one tab at a time. `TOURNAMENT` SHALL be selected when the Setup
phase is opened. The tab bar SHALL use the same control treatment as the preview pane's
tabs, and its labels SHALL be localized like all other user-facing text.

`TIMELINE` SHALL stand between `EXTRA` and `PAYMENTS`, so the bar reads in the order the
organizer works: what the tournament is, what it offers, what those cost, when it all
happens, and how it is paid for.

**Which of those tabs are offered SHALL follow the tournament's features**, as fixed by
`tournament-modes`. `EXTRA` SHALL be offered only while the extra services feature is on.
`OTHER` SHALL keep its owner-only restriction. The remaining five SHALL always be
offered, so that a tournament in easy mode is navigated by `TOURNAMENT`, `DISCIPLINES`,
`TIMELINE`, `PAYMENTS`, `OTHER` and `PUBLISH`. Whichever tabs are offered SHALL keep the
fixed order above; the mode removes tabs, it never reorders them.

**The payments tab SHALL be titled `PRICING` while the payments feature is off**, because
what it then holds is the currency the tournament prices in and the discounts it gives,
and a tab titled for payments on a tournament that takes none states something untrue.
The tab's identifier SHALL NOT change with its title: it remains the `payments` tab for
the URL it produces, for the incompleteness marker attributed to it, and for the panel it
controls.

#### Scenario: Seven tabs offered
- **WHEN** the organizer opens the Setup phase of a tournament with every feature enabled
- **THEN** the settings pane offers the seven tabs in that order, with `TOURNAMENT` selected and only its sections shown

#### Scenario: Switching tabs
- **WHEN** the organizer selects `DISCIPLINES`
- **THEN** the discipline table is shown and no other tab's sections are shown

#### Scenario: Selection survives a save
- **WHEN** the organizer has `EXTRA` selected and saves an extra item
- **THEN** `EXTRA` is still the selected tab, with its sections refreshed from the saved state

#### Scenario: Timeline reachable like any other tab
- **WHEN** the organizer selects `TIMELINE`
- **THEN** the tournament's dates are shown and no other tab's sections are shown

#### Scenario: Easy mode offers six tabs
- **WHEN** the tournament owner opens the Setup phase of a tournament in easy mode
- **THEN** the tab bar offers `TOURNAMENT`, `DISCIPLINES`, `TIMELINE`, `PRICING`, `OTHER` and `PUBLISH`, in that order, and no `EXTRA` tab

#### Scenario: Payments tab titled for what it holds
- **WHEN** the organizer turns the payments feature off
- **THEN** the tab is titled `PRICING`, its URL and its incompleteness marker are unchanged, and turning payments back on titles it `PAYMENTS` again

#### Scenario: EXTRA appears with its feature
- **WHEN** the organizer turns the extra services feature on from `OTHER`
- **THEN** `EXTRA` appears in its fixed place between `DISCIPLINES` and `TIMELINE`, without leaving Setup

### Requirement: Section allocation to tabs
Every Setup settings section SHALL belong to exactly one tab, and no section SHALL be
dropped, duplicated, or split by this navigation:

- `TOURNAMENT` — the tournament's identity fields (display name, subtitle, logo, date,
  location, description, qualification statement, registration instructions) and the
  titular organizers.
- `DISCIPLINES` — the disciplines table.
- `EXTRA` — the extra-items table.
- `TIMELINE` — every date that governs the tournament as a whole: when registration
  opens, the seating deadline, when registration closes, and the team composition
  deadline.
- `PAYMENTS` — how fencers pay (the payment mode, the deposit, the payment window and
  the reminder day), the bank account payments are collected into, the currency and
  exchange-rate section, the VS series statement, the discount list, and — only while
  the tournament still carries them — the legacy fixed fees.
- `OTHER` — the tournament mode, console team access, the export sheet address, and the
  danger zone.
- `PUBLISH` — the publication state, the items blocking publication, and the publish
  action, as fixed by `tournament-publication`.

The payment-mode section SHALL stand first on `PAYMENTS`, before the bank account the
money arrives in; the bank account SHALL keep its place ahead of the currency it is
denominated in.

**A section whose feature is off SHALL NOT be shown**, as fixed by `tournament-modes`,
and its stored values SHALL be retained rather than cleared. On `PAYMENTS` this SHALL
divide the tab: while payments are off, the tab — then titled `PRICING` — SHALL hold the
currency and exchange-rate section, the discount list, and any legacy fixed fees the
tournament still carries, and SHALL NOT hold the payment mode, the deposit, the payment
window, the reminder day, the bank account or the VS series statement. On `TIMELINE` the
seating deadline SHALL be offered only while payments are on, since nothing settles
against it when no money is owed. The mode section on `OTHER` SHALL be shown in every
mode, because it is the way back.

**One field, one editor.** A field that governs whether a tournament may be published
SHALL be offered in exactly one place, so that an organizer reading it in Setup is
reading the value the publication check reads. This SHALL hold for the bank account, the
deposit amount, and the legacy fixed fees alike. No tournament parameter SHALL be offered
in the console's phase panels. A feature turned off SHALL NOT move a field to a second
editor: it removes the one editor there is, and the item it governs is reported on
`PUBLISH` naming the feature that restores it.

The team composition deadline SHALL sit on `TIMELINE` in its chronological place, and
SHALL be offered only while the team disciplines feature is on and at least one
discipline row is of the team kind, including a row added in the current unsaved draft on
`DISCIPLINES`. A deadline already stored on a tournament whose team disciplines have all
been removed, or whose team feature has been turned off, SHALL be retained rather than
cleared.

The registration window — when registration opens and closes — SHALL sit on `TIMELINE`
in every mode. The tournament's own date SHALL remain editable on `TOURNAMENT` and SHALL
appear on `TIMELINE` read-only, as the anchor the other dates run towards.

Within a tab, sections SHALL keep their existing relative order, except on
`TOURNAMENT`, where the identity fields follow the order fixed by `tournament-admin`.
Sections that are shown only to the tournament owner SHALL keep that restriction; when
a non-owner opens `OTHER` and it would therefore be empty, the tab SHALL NOT be
offered at all rather than opening onto nothing. `PUBLISH` SHALL be offered to every
account with console access.

#### Scenario: Every section reachable
- **WHEN** the organizer of a tournament with every feature enabled visits all seven tabs
- **THEN** every settings section that existed before this change is present on exactly one of them, and every tournament parameter formerly offered in a console phase panel is present on one of them

#### Scenario: Deadline appears with the first team row
- **WHEN** the organizer of a tournament with the team feature on sets a discipline row's kind to team in an unsaved draft on `DISCIPLINES`
- **THEN** the composition deadline field appears in its place on `TIMELINE`

#### Scenario: Deadline hidden without team disciplines
- **WHEN** the tournament offers only individual disciplines
- **THEN** no composition deadline field is shown on `TIMELINE`

#### Scenario: Stored deadline survives removing the team discipline
- **WHEN** the organizer removes the last team discipline from a tournament that had a composition deadline set
- **THEN** the field stops being shown and the stored deadline is not cleared

#### Scenario: Money settings together
- **WHEN** the organizer of a payments-enabled tournament opens `PAYMENTS`
- **THEN** how fencers pay, the bank account, the currency and exchange rate, the VS series statement, and the discount list are shown together, with the payment mode first and the bank account ahead of the currency

#### Scenario: Pricing tab holds only what survives payments being off
- **WHEN** the organizer of a payments-off tournament opens `PRICING`
- **THEN** it holds the currency and exchange-rate section and the discount list, and offers no payment mode, deposit, payment window, reminder day, bank account or VS series statement

#### Scenario: Seating deadline follows the payments feature
- **WHEN** the organizer turns payments off on a tournament with a seating deadline set
- **THEN** `TIMELINE` stops offering the seating deadline, the stored date is unchanged, and registration opens and closes are still offered

#### Scenario: Mode section always on OTHER
- **WHEN** the tournament owner opens `OTHER` in easy mode
- **THEN** the tournament mode section is present alongside the console team, the export sheet address and the danger zone

#### Scenario: Bank account has one editor
- **WHEN** the organizer looks for the bank account in the console's payments-phase panels
- **THEN** it is not offered there, and `PAYMENTS` in Setup is the only place it can be edited

#### Scenario: Deposit has one editor
- **WHEN** the organizer looks for the deposit amount in the console's payments-phase panels
- **THEN** it is not offered there, and `PAYMENTS` in Setup is the only place it can be edited

#### Scenario: Tournament date is shown but not edited on the timeline
- **WHEN** the organizer opens `TIMELINE`
- **THEN** the tournament date is shown as the timeline's anchor with no field to change it, and `TOURNAMENT` remains the only place it can be edited

#### Scenario: Non-owner sees no empty tab
- **WHEN** a console team member who is not the tournament owner opens Setup
- **THEN** the `OTHER` tab is not offered, and the remaining tabs its mode allows — including `PUBLISH` — behave as usual

### Requirement: Per-tab incompleteness markers
Each tab that contains at least one unconfigured mandatory item SHALL carry a marker in
the tab bar, drawn in `--stamp` with a localized accessible label, so that an item read
on `PUBLISH` can be traced to the tab that resolves it.

**Every item the publication check can report SHALL be attributed to a tab, and that tab
SHALL hold a section that resolves it.** Location and organizers attribute to
`TOURNAMENT`; missing disciplines, missing discipline prices and missing team bounds to
`DISCIPLINES`; missing extra-item prices to `EXTRA`; and the missing bank account, missing
discount amounts, the missing deposit amount, and the currency-mode conflicts — including
legacy fixed fees that cannot be priced in EUR — to `PAYMENTS`.

**A marker SHALL only ever be raised on a tab the mode offers.** An item whose editor the
tournament's features conceal — an extra item's price while extra services are off, a
team discipline's roster bounds while team disciplines are off — SHALL mark `PUBLISH`
alone, and `PUBLISH` SHALL name the feature that restores its editor alongside the item.
No marker SHALL be raised on a tab that is not in the bar, and no item SHALL be left
unreachable: either its tab is offered and marked, or `PUBLISH` says which feature to turn
on. Items that cannot arise in a mode — the bank account and the deposit while payments
are off — SHALL simply not be reported.

An item the client does not recognize SHALL mark no tab and SHALL NOT break the tab bar.
That fallback exists for a backend reporting something a deployed client has never heard
of; it SHALL NOT be the resting state of an item this client is expected to resolve.
`PUBLISH` SHALL carry a marker whenever any other tab does, since that is where the items
are listed.

The settings pane header SHALL consist of the tab bar alone. No list of unconfigured
items SHALL appear outside the `PUBLISH` tab. The header SHALL stay in place while the
selected tab's sections scroll beneath it, and no part of a scrolling section SHALL
ever be visible above it or through its background, at any scroll position and on any
tab.

#### Scenario: Marker points at the responsible tab
- **WHEN** the tournament has a discipline with no price and no other missing item
- **THEN** the `DISCIPLINES` tab carries the marker, `PUBLISH` carries one, and no other tab does

#### Scenario: Missing bank account marks PAYMENTS
- **WHEN** a payments-enabled tournament that charges has no bank account recorded and no other missing item
- **THEN** the `PAYMENTS` tab carries the marker, `PUBLISH` carries one, and no other tab does

#### Scenario: Missing deposit marks the payments tab
- **WHEN** a deposit-mode tournament has no deposit amount
- **THEN** `PAYMENTS` carries the marker, `PUBLISH` carries one, and the deposit field is on `PAYMENTS`

#### Scenario: No bank account item while payments are off
- **WHEN** a priced tournament with payments off has no bank account recorded
- **THEN** nothing is reported about a bank account, no tab is marked on its account, and publication is not blocked by it

#### Scenario: Hidden editor reported on PUBLISH alone
- **WHEN** a tournament with extra services off holds an extra item whose EUR price is empty
- **THEN** `PUBLISH` reports the missing price and names the extra services feature as what restores its editor, `PUBLISH` carries the marker, and no other tab does

#### Scenario: Legacy fees blocking EUR mark the tab that clears them
- **WHEN** a EUR-priced tournament still carries legacy fixed fees
- **THEN** the payments tab carries the marker and holds the section that clears them, whether it is titled `PAYMENTS` or `PRICING`

#### Scenario: Every reported item marks a tab
- **WHEN** the publication check reports any item this client knows whose tab the mode offers
- **THEN** that tab carries a marker, and `PUBLISH` carries one — no such item leaves the tab bar unmarked

#### Scenario: Marker appears when a price is set on another tab
- **WHEN** the organizer sets the first nonzero discipline price on `DISCIPLINES` for a payments-enabled tournament with no bank account
- **THEN** the `PAYMENTS` tab gains the marker, without the organizer having visited it

#### Scenario: Markers clear on publication
- **WHEN** the tournament is published
- **THEN** no tab carries a marker, and none can appear again

#### Scenario: Nothing listed outside PUBLISH
- **WHEN** the organizer moves through the tabs of an incomplete draft
- **THEN** no tab except `PUBLISH` lists the missing items, and the header above the sections is the tab bar alone

#### Scenario: Nothing shows above the tab bar
- **WHEN** the organizer scrolls a long tab such as `TOURNAMENT` to its bottom
- **THEN** the band above the tab bar stays empty and opaque, with no field, table row or table header visible in it

#### Scenario: Sticky table header stays below the pane header
- **WHEN** the organizer scrolls the `DISCIPLINES` table far enough for its column headers to stick
- **THEN** those headers stick below the tab bar, and never over it

#### Scenario: Unrecognized item key
- **WHEN** the setup state reports an item the client has no tab mapping for
- **THEN** no tab is marked because of it and the tab bar renders normally
