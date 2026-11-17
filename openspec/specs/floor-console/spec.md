# floor-console Specification

## Purpose
TBD - created by archiving change add-floor-console. Update Purpose after archive.
## Requirements
### Requirement: The tournament day has a console of its own
A tournament with at least one discipline SHALL have a tournament-day console at
`/organizer/:slug/floor/:phase`, beside the office console at
`/organizer/:slug/console/:phase`.

**Who may open it.** The floor console is open to whoever may open the office console:
the tournament's owner and its team (`user-roles`). Everyone else SHALL be refused as the
office console refuses them.

**What has no floor.** A discipline-less event has no floor. Its floor address SHALL end
at the not-found screen (`routing`).

**The link from the office console.** The office console's header already names three
stages: "Před turnajem", "Turnaj" and "Po turnaji". Wherever the floor exists, "Turnaj"
SHALL be a link to the floor console. In the floor console, "Před turnajem" SHALL lead
back to the office console, and "Turnaj" is the current stage.

**Addresses.** Every floor address SHALL be built from `floorPath` in `routes.ts`.

#### Scenario: An organizer opens the floor
- **WHEN** a team member follows "Turnaj" in the office console's header of a tournament with disciplines
- **THEN** the floor console opens on its default tab

#### Scenario: An event has no floor
- **WHEN** someone opens the floor address of a discipline-less event
- **THEN** the not-found screen is shown

#### Scenario: A stranger is refused
- **WHEN** a signed-in fencer outside the tournament's team opens a floor address
- **THEN** they are refused as at the office console

### Requirement: Eight tabs in a fixed order
The floor console SHALL offer eight tabs in the rail, in this order:

| Tab | Label |
|---|---|
| `setup` | Nastavení |
| `data` | Data |
| `plan` | Plán |
| `today` | Přehled |
| `checkin` | Prezence |
| `pools` | Skupiny |
| `bracket` | Pavouk |
| `results` | Výsledky |

Labels start with a capital letter, and the rest of the label is lowercase. A label is
the tab's hint and accessible name.

**Which tabs are shown.** No tab SHALL be added or removed by a setting, and none
reordered. What a tournament's settings change is a tab's content. Sections about teams
appear only where the tournament has a team discipline. What floor Setup's scope hides
is hidden inside the tabs (`floor-setup`, Scope decides what is planned).

**The default tab.** An address naming no tab, or a tab that does not exist, SHALL
resolve to `today` once a plan has been published, and to `setup` before then.

**Tabs whose change has not landed.** A tab whose change has not been implemented SHALL
state that it is not available yet, in one line. It SHALL NOT be hidden.

#### Scenario: Order does not depend on settings
- **WHEN** a tournament with no team discipline and no schedule planned opens its floor console
- **THEN** all eight tabs are offered in the rail in the order above

#### Scenario: The default tab follows publication
- **WHEN** the organizer opens `/organizer/cup/floor` before any plan is published
- **THEN** the console lands on `setup`

### Requirement: A badge means something here is waiting for you
A floor tab SHALL carry a badge when it holds something that waits on the organizer.

Each tab's waiting conditions are defined by the capability that owns the tab. This
change defines Setup's: a discipline without a format, or no day or no piste stated.
Floor Setup's waiting conditions are what `floor-setup` names incomplete.

**What a badge is.** A badge SHALL be a static mark drawn with the design-system tokens.
It is never animated and never a count that ticks (`design-system`, A live figure is text,
not an animation).

**How to tell badged tabs apart.** A tab with no badge SHALL NOT be told apart from
another unbadged tab by colour.

#### Scenario: Missing setup is badged
- **WHEN** a discipline has no format
- **THEN** the `setup` tab carries a badge, and the setup section for that discipline names what is missing

### Requirement: A schedule panel stands beside the work
With "Plánovat rozvrh" on (`floor-setup`), on a wide screen the floor console SHALL
reserve a panel beside every tab except `setup`, for the schedule. The live schedule is
drawn there. Until a plan exists, the panel states that no plan has been made.

On a narrow screen the panel SHALL become a ninth, last tab of the rail named "Rozvrh".
It works the same way the Setup preview does (`setup-preview`, Setup shows the preview
beside the settings, or as their last tab).

**Without a schedule.** With "Plánovat rozvrh" off there is no schedule panel and no
"Rozvrh" tab, and the work takes the full width.

The breakpoint SHALL be the canonical one (`responsive-layout`).

#### Scenario: The panel becomes a tab on a phone
- **WHEN** the floor console is opened below the canonical breakpoint
- **THEN** "Rozvrh" is offered as the rail's last tab and no side panel is drawn

#### Scenario: No schedule, no panel
- **WHEN** "Plánovat rozvrh" is off and the organizer opens `today` on a wide screen
- **THEN** no schedule panel is drawn and the matrix takes the full width

### Requirement: The tabs are a rail of icons on the left
The floor console SHALL keep the office console's top bar across the full width. That
bar holds the logo, the stage control, the tournament's name and date, and the account
menu. Below it, the floor's tabs SHALL be a narrow rail down the left edge, and the
work takes the rest of the width. There is no second band of tabs across the top.

**What a rail tab is.** Each tab is an outline icon from the icon set the frontend
already uses. A filled icon is never used (`design-system`).
- **Its name.** The name is not drawn beside the icon. It appears in a floating hint on
  hover and on keyboard focus, and is the tab's accessible name.
- **Size.** Each tab is a touch target of the size `responsive-layout` requires.
- **The current tab.** It is marked with design-system tokens and never by colour alone.

**Badges and the unsaved mark.** A tab's badge and its unsaved mark SHALL sit on the
icon, as static marks. Each SHALL also be stated in words in the hint and to assistive
technology.

**Keyboard.** The rail is a vertical tab list. The up and down arrows move between its
tabs.

**Narrow screens.** The rail SHALL stay on narrow screens. Below the canonical
breakpoint, "Rozvrh" is its last icon (see A schedule panel stands beside the work).

#### Scenario: A name appears only on hover or focus
- **WHEN** the organizer moves the pointer over the rail's fourth icon
- **THEN** a hint reads "Přehled", and no tab name is drawn while nothing is hovered or focused

#### Scenario: A badge is told in words
- **WHEN** the `setup` tab carries a badge
- **THEN** its icon carries the static mark, and its hint and accessible name read "Nastavení" followed by the words for "something is waiting here"

#### Scenario: The rail on a phone
- **WHEN** the floor console is opened below the canonical breakpoint
- **THEN** the rail is drawn on the left with nine icons, the last being "Rozvrh"
