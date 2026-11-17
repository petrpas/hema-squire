## ADDED Requirements

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

## MODIFIED Requirements

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
