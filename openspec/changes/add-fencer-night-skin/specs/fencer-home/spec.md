## MODIFIED Requirements

### Requirement: Fencer Home landing
Every visitor SHALL land on the tournament list, whether or not they hold an account and whatever role they hold. The page SHALL be a full-screen view with a top bar and a grid of tournament cards, filtered by four tabs: Vyhlášené turnaje (Announced — published, non-cancelled, upcoming tournaments whose registration is not open: not yet opened or already closed), Otevřené turnaje (Open — published, non-cancelled, upcoming tournaments whose registration is open right now), Proběhlé turnaje (Past — every published, non-cancelled tournament dated before today, whoever was involved), and Moje turnaje (Mine — the account's own, per its own requirement). The first three SHALL be disjoint and SHALL together hold every published, non-cancelled tournament; Mine overlaps them by design. "Published" means the tournament carries a publication record, not that its setup happens to be complete. Upcoming tournaments SHALL be ordered by date ascending, tournaments already held by date descending.

**The list SHALL hold the same tournaments for every visitor.** No role, and no absence of one, SHALL add or remove an entry. An organizer's extra power over a tournament they may manage SHALL be a control on that tournament's card and nothing more (see `Managing a tournament from its card`). Drafts and cancelled tournaments SHALL remain absent from every tab, for their own organizer too; the tournament picker remains the one place those are listed.

**Mine SHALL be offered only to an account.** An anonymous visitor SHALL be shown the three public tabs; the fourth is an account's own list and there is no account to list.

The filter tabs SHALL stand at the top of the main field, centred above the list, and SHALL NOT stand in the top bar (see `Fencer identity header`). They SHALL be drawn as one segmented control: a container on `--paper-raised` with a 1px `--hairline` border at `--radius-pill`, holding the tabs as pills at least 40px high; the active tab SHALL invert, `--ink` ground and `--paper` text. A tab's count SHALL be in `--font-data` 12px, `--ink-faded`, and `--ink-soft` on the active tab. Below 480px the control SHALL span the full width with the tabs sharing it equally.

The cards SHALL be laid out in a grid of columns at least 320px wide, filling a column at most 1240px wide, with 20px between cards.

**A card** SHALL be a container on `--paper-raised` with a 1px `--hairline` border at `--radius-card`, made of a cover and a body, and SHALL present:

- **The cover**, a band whose ground is one of the three pastel tints (file-blue, seal-green, form-yellow), chosen deterministically from the tournament's slug by the same hash that tilts the Paid stamp, so the same tournament always wears the same tint. The choice SHALL be carried as a data attribute and resolved in CSS, so no color lives in a component.
- **The plate**, centred in the cover at `--radius-plate`: the tournament's logo on `--plate` when one is set, filling the plate and cropped on its longer side; otherwise its monogram (see `A tournament without a logo shows its monogram`) on `--paper` in the tint's `-ink` color. The plate SHALL be ringed in `--stamp` while registration is open, and in `--hairline-strong` otherwise. The ring is drawn by an outline, not a border or a shadow.
- **The ordinal**, at the cover's top right in `--font-data` 12px `--ink-faded`: the card's position in the list as shown, zero-padded (`001`).
- **The status block**, at the cover's top left, never reaching the plate: three short lines at `--radius-chip` stating registration's state. Open: `registrace` / `otevřena` / `do {closing date}`, on `--stamp-tint` in `--stamp-on-tint`, led by a small `--stamp` dot. Opens on a date: `registrace` / `od {date}` / `v {time}` when an hour is set. Held elsewhere: `registrace` / `jinde`. Closed: `registrace` / `uzavřena`. The last three stand on `--paper` in `--ink`, `--ink-soft` and `--ink-faded` respectively. A line whose value is absent SHALL be omitted. On the Mine and Past tabs the block SHALL state the account's own bond instead, as those tabs require.
- **The body**: the tournament's name in `--font-display` at `--weight-display`; the subtitle beneath it when one is set, in `--ink-soft`; the date and the city together on their own line in `--font-data`; the organizer names as plain `--ink-soft` text, with no links in them; then one row per offered discipline, its name at the left and its figure at the right over a capacity meter (`design-system`); and at the foot, below a hairline and aligned across a row of cards, the count of seated fencers and of their clubs at the right in `--font-data` 12px `--ink-faded`.

The date and city line SHALL separate its parts with the spaced middle dot and SHALL wrap rather than overflow on a narrow screen. The card layout SHALL render correctly whether or not a logo, subtitle, city, or organizer is present.

The card's whole body SHALL be one link to the tournament's detail, and the card SHALL carry no Register or Manage registration action of its own: registration's state is stated by the status block and acted on from the detail page. A card SHALL carry no link inside its body link; the organizer names are text for that reason. **A tournament in manual mode SHALL state in its status block that its registration is held elsewhere** (`tournament-mode`, `external-registration`); the way out itself SHALL be offered on the tournament detail page the card opens, where the registration form would otherwise be. The card SHALL NOT state that such a tournament's registration is closed, which would be untrue of a window that never existed here. Each tab SHALL show its own empty-state message when it lists nothing.

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
- **THEN** its status block reads `registrace` / `jinde`, the card offers no Register action, does not describe registration as closed, and opens the detail where the way out is offered

#### Scenario: Hovering a card
- **WHEN** a visitor with a mouse hovers a card
- **THEN** only its border and its ground change; nothing moves, and no shadow appears

#### Scenario: A card on a phone
- **WHEN** the list is opened on a 390px-wide viewport
- **THEN** each card is a compact row with a 56px plate at its left, no cover band, the status as a single line of text, and the meters unchanged below

### Requirement: Past tournaments tab
The Proběhlé turnaje tab SHALL list every published, non-cancelled tournament dated before today, ordered by date descending, whether or not the account was involved with it. Cards SHALL carry the same parts as an upcoming card — cover, name, subtitle, date and place, organizers, per-discipline counts, the fencer and club counts — and SHALL state the account's own registration state when it held one, or an organizer mark when it only organized. A paid registration SHALL additionally show the Paid stamp on the cover's bottom left; the list carries no other wink, so the stamp is the screen's one. Selecting a past tournament SHALL open its detail in read-only mode.

The "today" that splits upcoming from held SHALL be **one global boundary, the UTC day**, and SHALL NOT be evaluated per tournament in that tournament's own zone. This list mixes tournaments from many zones and is answered by one comparison over all of them; the cost of an honest per-row boundary is a worse query, and its only effect is that a tournament held today stays under the upcoming tabs for the first hours of a morning east of UTC. This is a decision, not an oversight, and it is stated here so it is not read as one.

#### Scenario: Participated tournament listed
- **WHEN** a fencer opens the Past tab having had a paid registration for a tournament held last month
- **THEN** that tournament is listed with its data, its paid state and the Paid stamp on its cover, and opens in read-only detail when selected

#### Scenario: Unrelated past tournament listed too
- **WHEN** a past tournament exists where the fencer had no registration and is not its organizer
- **THEN** it is listed in the Past tab, with no registration state and no organizer mark

#### Scenario: Organized tournament marked
- **WHEN** an organizer opens the Past tab for a tournament they organized but did not fence in
- **THEN** the tournament is listed with an organizer mark and no registration state

#### Scenario: Never-published past tournament hidden
- **WHEN** a past tournament was never published
- **THEN** it does not appear in the Past tab for anyone, including its organizer

#### Scenario: The split is the same for every tournament
- **WHEN** two published tournaments held in different timezones share a date, and that date is yesterday in UTC
- **THEN** both appear in the Past tab, neither having waited for its own local midnight

#### Scenario: The split does not follow the deployment
- **WHEN** the Past tab is listed on a deployment whose process timezone is not UTC
- **THEN** the same tournaments are listed as on any other deployment

## ADDED Requirements

### Requirement: A tournament without a logo shows its monogram
Where a tournament has no logo, its plate SHALL show a monogram derived from its display name: the name is split on whitespace and punctuation; tokens made only of digits and the function words `a, i, v, ve, na, z, ze, do, of, the, and, &` are dropped; the first letter of each of the first two remaining tokens is taken, uppercased, diacritics kept. One remaining token gives its first two letters; none gives the first two visible characters of the raw name. A monogram SHALL never be empty and never longer than three characters.

#### Scenario: Two words
- **WHEN** a tournament named `Brněnská šavle 2027` has no logo
- **THEN** its plate reads `BŠ`

#### Scenario: One word
- **WHEN** a tournament named `Bohemia` has no logo
- **THEN** its plate reads `BO`

#### Scenario: Function words skipped
- **WHEN** a tournament named `Memoriál v Praze` has no logo
- **THEN** its plate reads `MP`

#### Scenario: Nothing left after dropping
- **WHEN** a tournament is named `2027`
- **THEN** its plate reads `20`

### Requirement: The list announces the next registration opening
The tournament list SHALL show, above the tab band, a strip naming the announced tournament whose registration opens soonest, when that opening is no more than 7 days away; otherwise the strip SHALL NOT be rendered. The strip SHALL carry the tournament's logo or monogram (unringed), the label `příští otevření registrace` / `next registration opening`, the tournament's name, a countdown to the opening, and a secondary control `Ukázat turnaj` / `Show tournament` linking to its detail.

Inside the last day before the opening the strip SHALL show a live countdown; before that it SHALL state the opening day and, where one is set, the hour, in the same place — the rule the detail page's wait follows (`Waiting for registration to open`). The countdown SHALL obey `A live figure is text, not an animation` (`design-system`) in full: `--font-data` with tabular numerals at a fixed width, at most one update per second, no motion, measured against the server's clock as the detail page measures it, and stopped at the moment. At the moment the strip SHALL be replaced: the tournament now open leaves the strip for the Open tab, and the next opening within 7 days, if any, takes its place.

Below 480px the countdown SHALL stand under the name.

#### Scenario: An opening within the week
- **WHEN** a visitor opens the list three days before an announced tournament's registration opens, and no other opens sooner
- **THEN** the strip names that tournament and states its opening day and hour

#### Scenario: The last day
- **WHEN** the soonest opening is four hours away
- **THEN** the strip counts down to it once a second

#### Scenario: Nothing within the week
- **WHEN** the soonest registration opening is ten days away
- **THEN** no strip is rendered

#### Scenario: The moment passes on screen
- **WHEN** the visitor keeps the list open as that opening moment passes
- **THEN** the countdown stops without showing a negative figure, the strip no longer names that tournament, and no ring, bar or fill was drawn beside the figure
