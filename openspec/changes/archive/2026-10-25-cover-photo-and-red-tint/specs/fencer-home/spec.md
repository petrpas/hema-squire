## MODIFIED Requirements

### Requirement: Fencer Home landing
Every visitor SHALL land on the tournament list, whether or not they hold an account and whatever role they hold. The page SHALL be a full-screen view with a top bar and a grid of tournament cards, filtered by four tabs: Vyhlášené turnaje (Announced — published, non-cancelled, upcoming tournaments whose registration is not open: not yet opened or already closed), Otevřené turnaje (Open — published, non-cancelled, upcoming tournaments whose registration is open right now), Proběhlé turnaje (Past — every published, non-cancelled tournament dated before today, whoever was involved), and Moje turnaje (Mine — the account's own, per its own requirement). The first three SHALL be disjoint and SHALL together hold every published, non-cancelled tournament; Mine overlaps them by design. "Published" means the tournament carries a publication record, not that its setup happens to be complete. Upcoming tournaments SHALL be ordered by date ascending, tournaments already held by date descending.

**The list SHALL hold the same tournaments for every visitor.** No role, and no absence of one, SHALL add or remove an entry. An organizer's extra power over a tournament they may manage SHALL be a control on that tournament's card and nothing more (see `Managing a tournament from its card`). Drafts and cancelled tournaments SHALL remain absent from every tab, for their own organizer too; the tournament picker remains the one place those are listed.

**Mine SHALL be offered only to an account.** An anonymous visitor SHALL be shown the three public tabs; the fourth is an account's own list and there is no account to list.

The filter tabs SHALL stand at the top of the main field, centred above the list, and SHALL NOT stand in the top bar (see `Fencer identity header`). They SHALL be drawn as one segmented control: a container on `--paper-raised` with a 1px `--hairline` border at `--radius-pill`, holding the tabs as pills at least 40px high; the active tab SHALL invert, `--ink` ground and `--paper` text. A tab's count SHALL be in `--font-data` 12px, `--ink-faded`, and `--ink-soft` on the active tab. Below 480px the control SHALL span the full width with the tabs sharing it equally.

The cards SHALL be laid out in a grid of columns at least 320px wide, filling a column at most 1240px wide, with 20px between cards.

**A card** SHALL be a container on `--paper-raised` with a 1px `--hairline` border at `--radius-card`, made of a cover and a body, and SHALL present:

- **The cover**, a band whose ground is either the organizer's cover photo (`A cover may wear a photo`) or one of the four pastel tints (file-blue, seal-green, form-yellow, ledger-red), chosen as `A card's cover tint follows its logo` states: by the organizer's choice where they made one, else by the logo's hue band where it has one, and otherwise deterministically from the tournament's slug by the same hash that tilts the Paid stamp, so the same tournament always wears the same tint. The tint SHALL be carried as a data attribute and resolved in CSS, so no color lives in a component.
- **The plate**, centred in the cover at `--radius-plate`: the tournament's logo on `--plate` when one is set, filling the plate and cropped on its longer side; otherwise its monogram (see `A tournament without a logo shows its monogram`) on `--paper` in the tint's `-ink` color. The plate SHALL be ringed in `--stamp` while registration is open, and in `--hairline-strong` otherwise. The ring is drawn by an outline, not a border or a shadow.
- **The ordinal**, at the cover's top right in `--font-data` 12px `--ink-faded`: the card's position in the list as shown, zero-padded (`001`).
- **The status block**, at the cover's top left, never reaching the plate: three short lines at `--radius-chip` stating registration's state. Open: `registrace` / `otevřena` / `do {closing date}`, on `--stamp-tint` in `--stamp-on-tint`, led by a small `--stamp` dot. Opens on a date: `registrace` / `od {date}` / `v {time}` when an hour is set. Closed: `registrace` / `uzavřena`. The last two stand on `--paper` in `--ink` and `--ink-faded` respectively. A tournament whose registrations its organizer keeps SHALL carry no status block at all. A line whose value is absent SHALL be omitted. On the Mine and Past tabs the block SHALL state the account's own bond instead, as those tabs require.
- **The body**: the tournament's name in `--font-display` at `--weight-display`; the subtitle beneath it when one is set, in `--ink-soft`; the date and the city together on their own line in `--font-data`; the organizer names as plain `--ink-soft` text, with no links in them; then one row per offered discipline, its name at the left and its figure at the right over a capacity meter (`design-system`); and at the foot, below a hairline and aligned across a row of cards, the count of seated fencers and of their clubs at the right in `--font-data` 12px `--ink-faded`.

The date and city line SHALL separate its parts with the spaced middle dot and SHALL wrap rather than overflow on a narrow screen. The card layout SHALL render correctly whether or not a logo, subtitle, city, or organizer is present.

The card's whole body SHALL be one link to the tournament's detail, and the card SHALL carry no Register or Manage registration action of its own: registration's state is stated by the status block, where it has one, and acted on from the detail page. A card SHALL carry no link inside its body link; the organizer names are text for that reason. **A tournament in manual mode SHALL state nothing about its registration on its card** (`tournament-mode`, `external-registration`); the way out SHALL be offered on the tournament detail page the card opens, where the registration form would otherwise be. The card SHALL NOT state that such a tournament's registration is closed, which would be untrue of a window that never existed here. Each tab SHALL show its own empty-state message when it lists nothing.

Hovering a card, where the pointer can hover, SHALL change only its border to `--hairline-strong` and its ground to `--paper-shade`, within the transition limits of `design-system`; no transform is applied.

A discipline on a card SHALL be labelled by its name, never by its slug (`discipline-identity`). Names are longer than the codes they replace and a tournament MAY offer several disciplines whose names differ only in a trailing qualifier, so a discipline's name SHALL wrap across lines rather than truncate, overflow, or force the card wider, and SHALL remain legible on the narrowest supported screen.

Below 480px a card SHALL become a compact row: no cover band; the plate at 56px at its left, ring kept; then the name, the date and city line, and the status as one line of text in the status block's colors without its block; the discipline rows and meters below, unchanged.

#### Scenario: Open tournament listed with counts
- **WHEN** a visitor opens the tournament list while a published upcoming tournament with two disciplines (18 of 25 entered, and 16 of 16 with 9 waiting) is open for registration and closes on 28 February
- **THEN** the tournament appears in the Open tab as a card whose plate is ringed in `--stamp`, whose status block reads `registrace` / `otevřena` / `do 28. 2.`, and whose disciplines read `18/25` and `plno · +9 čeká` over their meters

#### Scenario: Card lines in order
- **WHEN** a card renders a tournament with a subtitle, a city and two organizers
- **THEN** the name, the subtitle, the date and place line, and the organizers line appear in that order beneath the cover, and no organizer name is a link

#### Scenario: Disciplines named, not coded
- **WHEN** a card lists a tournament's disciplines
- **THEN** each is labelled by its name, and no slug appears on the card

#### Scenario: Many long discipline names wrap
- **WHEN** a card lists six disciplines whose names include trailing qualifiers, on a narrow screen
- **THEN** each name wraps, stays legible and untruncated, and the card does not widen or overflow

#### Scenario: Card shows logo and subtitle when set
- **WHEN** a listed tournament has a logo and a subtitle
- **THEN** its card shows the logo on the light plate in the cover and the subtitle beneath the name

#### Scenario: Card degrades without logo, subtitle, or city
- **WHEN** a listed tournament has no logo, no subtitle, and no city
- **THEN** its plate shows the monogram, and the card renders without empty gaps for the missing subtitle or city line

#### Scenario: The same tint every time
- **WHEN** the same tournament's card is rendered on two page loads, and in two different tabs
- **THEN** its cover wears the same tint each time

#### Scenario: A card with a cover photo
- **WHEN** a listed tournament's organizer chose a cover photo
- **THEN** its card's cover band shows the photo, cropped to fill the band, with the plate at its centre and the status block at its top left as on a tinted cover

#### Scenario: Ordinal follows the list as shown
- **WHEN** the Open tab lists three tournaments
- **THEN** their cards read `001`, `002` and `003` in list order

#### Scenario: A card is one link
- **WHEN** a visitor selects anywhere in a card's body
- **THEN** the tournament's detail opens, the card having offered no separate Register control

#### Scenario: Tabs are disjoint
- **WHEN** a published upcoming tournament's registration has not yet opened or has already closed
- **THEN** it appears in the Announced tab with its status block and not in the Open tab

#### Scenario: Held tournament leaves the upcoming tabs
- **WHEN** a published tournament's date passes
- **THEN** it appears in the Past tab and in neither Announced nor Open

#### Scenario: Login lands on the Open tab
- **WHEN** an account with no tournament of its own logs in while registration is open somewhere
- **THEN** the tournament list opens with the Open tab selected, as the default-tab rule resolves it

#### Scenario: One list for every role
- **WHEN** an organizer, a plain fencer and an anonymous visitor each open the Open tab at the same moment
- **THEN** all three see the same tournaments, in the same order, with the same cards

#### Scenario: Tabs above the list, not in the bar
- **WHEN** the tournament list renders
- **THEN** the filter tabs stand centred at the top of the main field as one segmented control, the active tab inverted, and the top bar carries none of them

#### Scenario: Anonymous visitor has three tabs
- **WHEN** a visitor with no account opens the tournament list
- **THEN** Announced, Open and Past are offered and Mine is not

#### Scenario: Draft hidden from fencers
- **WHEN** a tournament has not been published
- **THEN** it does not appear in any tab of the tournament list, even when its mandatory setup is complete, and even for the organizer who owns it

#### Scenario: An organizer-kept tournament points outward
- **WHEN** a visitor opens the tournament list while a published upcoming tournament whose registrations the organizer keeps is listed
- **THEN** its card carries no status block, offers no Register action, does not describe registration as closed, and opens the detail where the way out is offered

#### Scenario: An organizer-kept tournament with no address recorded
- **WHEN** such a tournament records no external registration address
- **THEN** the card carries no status block and offers no action

#### Scenario: Existing registration changes the action
- **WHEN** the fencer already has an active (reserved or paid) registration for a listed upcoming tournament
- **THEN** the card in the Open or Announced tab still offers no action of its own and opens the detail, where the registration is managed, and the Mine tab's card states the registration's state in its block

#### Scenario: Hovering a card
- **WHEN** a visitor with a mouse hovers a card
- **THEN** only its border and its ground change; nothing moves, and no shadow appears

#### Scenario: A card on a phone
- **WHEN** the list is opened on a 390px-wide viewport
- **THEN** each card is a compact row with a 56px plate at its left, no cover band, the status as a single line of text, and the meters unchanged below

### Requirement: A card's cover tint follows its logo
Where the organizer chose a cover tint (`tournament-admin`, The organizer chooses the cover ground), the cover SHALL wear it, whatever the logo or the slug would give. Otherwise, where a listed tournament's logo has a hue band, its card's cover SHALL wear the pastel tint of that band: `blue` the file-blue tint, `green` the seal-green tint, `warm` the form-yellow tint. Where the tournament has no logo, or its logo has no band, the cover SHALL wear the tint chosen from the slug among file-blue, seal-green and form-yellow, as before. The ledger-red tint SHALL be worn only where the organizer chose it: neither the band nor the slug chooses it, so no cover changes for its arrival. No color taken from the logo itself SHALL be rendered: the band only chooses among the tint tokens.

Where the cover wears a photo, the tint the rules above would give SHALL still color the plate's monogram, which reads in the tint's `-ink`.

#### Scenario: Green logo, green cover
- **WHEN** a tournament whose logo band is `green` is listed
- **THEN** its cover wears the seal-green tint, whatever its slug would choose

#### Scenario: Achromatic logo
- **WHEN** a tournament's logo has no band
- **THEN** its cover wears the tint its slug chooses, the same on every render

#### Scenario: Logo replaced
- **WHEN** the organizer replaces a blue logo with a red one
- **THEN** the card's cover changes from the file-blue tint to the form-yellow tint

#### Scenario: Red only by choice
- **WHEN** a tournament whose organizer chose no tint is listed, whatever its logo band and its slug
- **THEN** its cover does not wear the ledger-red tint

#### Scenario: Red chosen
- **WHEN** the organizer chose the ledger-red tint
- **THEN** the card's cover wears the ledger-red tint

### Requirement: Tournament detail opens on its cover
The detail's information block SHALL open with the same cover its card wears: a band in the tint the card would choose (`A card's cover tint follows its logo`), or showing the same cover photo where the card shows one (`A cover may wear a photo`), the plate at its centre — the whole logo on `--plate`, the plate taking the logo's own proportions at a fixed height so nothing of it is cut away, or the short code or monogram on a square plate — ringed in `--stamp` while registration is open and in `--hairline-strong` otherwise, and at its top left the status block stating registration's state as the card states it — none where the organizer keeps the registrations, as on the card. The status is the one the page itself computes against the server's clock, so the block changes in place when registration opens. The title, subtitle and facts follow beneath the cover. On a phone, where the plate and the status block do not fit side by side, the status block stands beneath the plate within the cover. The card on the list keeps its square plate, the logo cropped to fill it.

#### Scenario: An open tournament with a logo
- **WHEN** the detail of a tournament whose registration is open and whose logo is green is opened
- **THEN** it opens on a seal-green band with the logo filling a plate ringed in `--stamp`, and the status block reads `registrace` / `otevřena` / `do {date}`

#### Scenario: Registration opens while the page is open
- **WHEN** the opening moment passes with the detail open
- **THEN** the status block reads open and the plate's ring turns `--stamp`, without a reload

#### Scenario: An organizer-kept tournament's detail
- **WHEN** the detail of a tournament whose registrations its organizer keeps is opened
- **THEN** its cover carries no status block, and the way out to the organizer's registration stands where the form would be

#### Scenario: A detail with a cover photo
- **WHEN** the detail of a tournament whose organizer chose a cover photo is opened
- **THEN** its cover band shows the same photo its card shows, cropped to fill the band, with the plate and the status block standing on it

#### Scenario: A wide logo on the detail
- **WHEN** the detail of a tournament whose logo is three times as wide as it is tall is opened
- **THEN** the whole logo is shown on a plate of the same proportions, and its card on the list shows it cropped to a square

### Requirement: Managing a tournament from its card
A card in any tab, and the tournament's detail, SHALL carry a **Spravovat** control when, and only when, the account reading it may manage that tournament — as its Tournament Owner or as a member of its console team. The control SHALL open that tournament's console. It SHALL be the only difference between what an organizer sees on the list or the detail and what anyone else sees.

The control SHALL be a quiet secondary button: a small pill outlined in `--hairline-strong` with `--ink-soft` text, never filled, so it stays apart from the screen's one primary action. It SHALL stand in the bottom right corner of the cover band, on the card and on the detail alike. On a cover photo it SHALL stand on a `--paper-raised` ground so it stays legible over any picture; that ground is the paper it would otherwise stand on, not a fill, and the outline and text are unchanged. On a phone, where the card has no cover band, it SHALL stand at the card's trailing edge below the foot.

The control SHALL be a link carrying the console's URL, so middle-click and modifier-click open it in a new browser tab, and SHALL be reachable without opening the card: activating it SHALL open the console and SHALL NOT also open the fencer-facing detail the card links to.

It SHALL appear on a past tournament's card as it does on an upcoming one — a held tournament's console is still where its records are read — and SHALL be absent for an anonymous visitor, who may manage nothing.

#### Scenario: Owner sees the control
- **WHEN** a Tournament Owner opens the tournament list and their tournament is listed
- **THEN** that card carries a Spravovat control and no other card does

#### Scenario: Console team member sees the control
- **WHEN** a console team member who is not the owner opens the same list
- **THEN** the card carries the same control

#### Scenario: Plain fencer sees no control
- **WHEN** a fencer who neither owns nor staffs any tournament opens the list
- **THEN** no card carries a Spravovat control

#### Scenario: The control opens the console, not the detail
- **WHEN** an organizer activates Spravovat on a card
- **THEN** that tournament's console opens and the fencer-facing detail does not

#### Scenario: The control is a link
- **WHEN** an organizer middle-clicks Spravovat
- **THEN** the console opens in a new browser tab at that tournament's console URL

#### Scenario: A held tournament can still be managed
- **WHEN** an organizer finds a tournament they ran last month in the Past tab
- **THEN** its card carries the Spravovat control

#### Scenario: Anonymous visitor sees no control
- **WHEN** a visitor with no account opens the list
- **THEN** no card carries a Spravovat control

#### Scenario: The control on the detail
- **WHEN** a Tournament Owner opens their tournament's detail
- **THEN** the cover's bottom right corner carries a Spravovat button leading to the console, and a plain fencer opening the same detail sees none

#### Scenario: A quiet button, not a link
- **WHEN** an organizer's card or detail shows the control
- **THEN** it is drawn as a small outlined pill, not as underlined text and not filled

#### Scenario: In the cover's corner
- **WHEN** an organizer's card is shown on a desktop width
- **THEN** its Spravovat button stands in the bottom right corner of the cover band, clear of the plate and the status block, and activating it opens the console, not the detail


## ADDED Requirements

### Requirement: A cover may wear a photo
Where the organizer chose a cover photo (`tournament-admin`, The organizer chooses the cover ground) and one is stored, the card's cover band and the detail's cover band SHALL show it as their ground in place of a tint, scaled to cover the whole band and cropped around its centre, never stretched. The photo SHALL be served from the tournament's own address beside its logo, and the list entry and the detail SHALL carry whether the cover wears one.

Nothing SHALL be laid over the photo to tame it: no scrim, gradient, blur or shadow (`design-system`, Global prohibitions). Instead every part of the cover that stood on the bare tint SHALL stand on paper: the ordinal on a `--paper` chip at `--radius-chip`, the Spravovat control on `--paper-raised`, and the Paid stamp on `--paper-raised`. The plate and the status block already stand on their own grounds and SHALL be unchanged.

The compact phone row, which has no cover band, SHALL show no photo. The photo SHALL be shown as stored in both skins.

#### Scenario: Parts stay legible on a photo
- **WHEN** a card whose cover wears a dark, busy photograph is listed with its ordinal and, for its organizer, a Spravovat control
- **THEN** the ordinal stands on a paper chip and the Spravovat control on paper, and no veil or gradient covers the photo

#### Scenario: A paid past tournament with a photo
- **WHEN** the Past tab lists a tournament with a cover photo for which the account's registration was paid
- **THEN** the Paid stamp stands on paper at the cover's bottom left

#### Scenario: A phone shows no photo
- **WHEN** the list is opened on a 390px-wide viewport and a tournament wears a cover photo
- **THEN** its compact row shows the plate with no band and no photo

#### Scenario: Photo removed
- **WHEN** the organizer removes the cover photo
- **THEN** the card and the detail wear the tint the logo or the slug gives
