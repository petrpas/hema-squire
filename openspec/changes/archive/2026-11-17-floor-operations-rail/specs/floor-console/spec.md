## MODIFIED Requirements

### Requirement: Eight tabs in a fixed order
The floor console SHALL offer eight tabs in the rail, and a ninth, "Rozvrh", where a
schedule is planned. They come in this order:

| Tab | Label |
|---|---|
| `setup` | Nastavení |
| `data` | Data |
| `plan` | Plán |
| `schedule` | Rozvrh — only with "Plánovat rozvrh" on |
| `today` | Přehled |
| `checkin` | Prezence |
| `pools` | Skupiny |
| `bracket` | Pavouk |
| `results` | Výsledky |

Labels start with a capital letter, and the rest of the label is lowercase. A label is
the tab's hint and accessible name.

**Which tabs are shown.**
- **The rule.** No tab SHALL be added or removed by a setting, and none reordered. What
  a tournament's settings change is a tab's content.
- **The one exception.** "Rozvrh" exists only while "Plánovat rozvrh" is on
  (`floor-setup`). With the tick off, the rail SHALL NOT offer it. Its address then
  resolves as an address naming a tab that does not exist.
- **Teams.** Sections about teams appear only where the tournament has a team
  discipline.
- **Scope.** What floor Setup's scope hides is hidden inside the tabs (`floor-setup`,
  Scope decides what is planned).

**The default tab.** An address naming no tab, or a tab that does not exist, SHALL
resolve to `today` once a plan has been published, and to `setup` before then.

**Tabs whose change has not landed.** A tab whose change has not been implemented SHALL
state that it is not available yet, in one line. It SHALL NOT be hidden.

#### Scenario: Order does not depend on settings
- **WHEN** a tournament with no team discipline and no schedule planned opens its floor console
- **THEN** the eight tabs other than "Rozvrh" are offered in the rail in the order above

#### Scenario: Rozvrh follows Plán where a schedule is planned
- **WHEN** "Plánovat rozvrh" is on and the organizer opens the floor console
- **THEN** the rail offers nine tabs, with "Rozvrh" fourth, right after "Plán"

#### Scenario: The schedule address without a schedule
- **WHEN** "Plánovat rozvrh" is off and the organizer opens `/organizer/cup/floor/schedule`
- **THEN** the console lands on the default tab

#### Scenario: The default tab follows publication
- **WHEN** the organizer opens `/organizer/cup/floor` before any plan is published
- **THEN** the console lands on `setup`

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

**Narrow screens.** The rail SHALL stay on narrow screens, with the same tabs as on a
wide one. No tab exists only on a narrow screen.

#### Scenario: A name appears only on hover or focus
- **WHEN** the organizer moves the pointer over the rail's fourth icon on a tournament with no schedule planned
- **THEN** a hint reads "Přehled", and no tab name is drawn while nothing is hovered or focused

#### Scenario: A badge is told in words
- **WHEN** the `setup` tab carries a badge
- **THEN** its icon carries the static mark, and its hint and accessible name read "Nastavení" followed by the words for "something is waiting here"

#### Scenario: The rail on a phone
- **WHEN** the floor console of a tournament with a schedule planned is opened below the canonical breakpoint
- **THEN** the rail is drawn on the left with the same nine icons as on a wide screen

## REMOVED Requirements

### Requirement: A schedule panel stands beside the work
**Reason**: The schedule moves to a tab of its own, "Rozvrh". The place beside the work
now holds the current tab's operations panel, as in the office console.
**Migration**: The schedule is read on the `schedule` tab (`floor-plan`, Rozvrh draws
piste × time). Where the panel was, a tab's operations now stand (A tab's operations
stand in a panel on the right).

## ADDED Requirements

### Requirement: A tab's operations stand in a panel on the right
Beside the work, the floor console SHALL draw an operations panel for the current tab,
built as the office console's rail is. Its title reads "Operace · <tab label>".

**What the panel holds.** The panel SHALL hold the actions that act on the tab as a
whole, or on the selected discipline, and the parameters of the operation the tab runs:

| Tab | Its operations panel |
|---|---|
| `data` | the link to the office console's Import phase, where the tournament is kept by the organizer |
| `plan` | the plan's preferences; asking for variants; re-planning; the publish gate with its obstacles; adding a pin; with officials planned, re-running the assignment and printing the rozpisy and piste sheets |
| `checkin` | the selected discipline's counts and its close or reopen gate, or every discipline's under "Všichni" |
| `pools` | drawing, redrawing and announcing the draw; the call list; closing or reopening the pools; the piste screens' links |
| `bracket` | confirming the bracket; printing; reopening |
| `results` | publishing or withdrawing the standing; the CSV export; the PDF print |

**What stays in the work.** An action on one row SHALL stay in that row, as in the
office's fencer table:
- choosing a variant;
- setting an official's seat;
- removing a pin;
- ticking a person, withdrawing an entry, editing a lineup, adding a substitute;
- swapping two fencers in a draw;
- printing one pool's sheet, beside that pool.

Search and the discipline strip stay at the head of the work.

**A tab with nothing to act on.** A tab whose content offers no tab-level action SHALL
show no operations panel, never an empty one. Its work SHALL take the full width. This
holds for `today` and `schedule`. `setup` saves through its own tabs (`floor-setup`) and
shows no operations panel either, as office Setup shows none.

**A state with nothing to act on.** Where the tab has a panel but its current state
offers no action, the panel SHALL say so in one line. An example is the pools of a
discipline whose check-in is still open. The panel keeps its place, so the work does
not shift as states change.

#### Scenario: The publish gate stands beside the variants
- **WHEN** the organizer opens `plan` on a wide screen
- **THEN** the variants and the working version's difference fill the work, and the publish gate stands in the panel titled "Operace · Plán"

#### Scenario: A row keeps its action
- **WHEN** the organizer opens `plan` with three variants
- **THEN** each variant offers its own "Vybrat" in the work, and the panel offers no choice of variant

#### Scenario: Přehled has no panel
- **WHEN** the organizer opens `today`
- **THEN** no operations panel is drawn and the matrix takes the full width

#### Scenario: A state with nothing to do
- **WHEN** the organizer opens `pools` at a discipline whose check-in is open
- **THEN** the operations panel states in one line that nothing can be done until check-in closes

### Requirement: The operations panel is a drawer on a narrow screen
Below the canonical breakpoint (`responsive-layout`), the operations panel SHALL NOT
stand beside the work. It SHALL become a drawer.

**The control.** The head of the work SHALL carry a control that opens the drawer. The
control names the panel ("Operace"). A tab with no operations panel has no control.

**How it is drawn.**
- **Its place.** The drawer lies over the work, above it in the z-axis, against the
  right edge, at the full height of the screen.
- **Its edge.** It is drawn with the panel's own paper and a rule on its open edge,
  with no shadow.
- **Behind it.** The work behind it is dimmed by the dialog backdrop the design system
  already uses.
- **The element.** It is the console's dialog element (`Modal`), opened modally. Focus
  moves into it and returns to the control when it closes.

**Opening and closing.**
- **No motion.** It appears and disappears at once, with no slide and no fade, as
  `design-system` restricts transitions to colour.
- **Closing.** It closes on Escape, on a click outside it, and by its own close control.
- **After an action.** An action taken inside it leaves the drawer open, so its result
  line can be read.

#### Scenario: Closing check-in on a phone
- **WHEN** the desk opens `checkin` at Sabre on a phone and follows "Operace"
- **THEN** a drawer opens over the list at once, holding Sabre's counts and its close gate, and Escape closes it with focus back on "Operace"

#### Scenario: No control where there is no panel
- **WHEN** the organizer opens `today` below the breakpoint
- **THEN** the head of the work offers no "Operace" control

### Requirement: Step tabs choose their discipline by tabs, kept across the console
On `checkin`, `pools`, `bracket` and `results`, the discipline SHALL be chosen from a
strip of discipline tabs at the head of the work. A drop-down SHALL NOT be used.

**The strip.**
- **Order and names.** It lists the tournament's disciplines in the order floor Setup
  lists them, each by its name.
- **The current one.** It is marked with design-system tokens and never by colour alone.
- **Keyboard.** It is a horizontal tab list, and the left and right arrows move along it.
- **Overflow.** Where the names do not fit the width, the strip scrolls sideways within
  itself and the page does not.

**Prezence alone starts with "Všichni".** It lists every person on the floor roster
(`floor-checkin`, The desk ticks persons, once). It is that tab's address without a
discipline.

**Kept across the console.** The discipline last chosen on any step tab SHALL be
carried to the next step tab the organizer opens from the rail. It is carried in that
tab's address, `floorPath(slug, tab, discipline)`.
- **Survives a detour.** Moving through a tab without disciplines (`plan`, `schedule`,
  `today`, `data`, `setup`) keeps the choice for the next step tab.
- **"Všichni".** Choosing "Všichni" on `checkin` keeps the choice made before it for
  the other step tabs.
- **Session only.** The choice lives as long as the console is open. It is not stored.
- **Before any choice.** An address without a discipline, with no discipline chosen
  yet, opens the strip's first discipline, or "Všichni" on `checkin`.

#### Scenario: Sabre stays chosen
- **WHEN** the organizer chooses Sabre on `pools`, opens `today`, and then follows the rail to `bracket`
- **THEN** `bracket` opens at Sabre, at `/organizer/cup/floor/bracket/SB`

#### Scenario: Everybody at the desk
- **WHEN** the organizer opens `checkin` with no discipline chosen yet
- **THEN** "Všichni" is the current tab of the strip and every person is listed

#### Scenario: Many disciplines on a phone
- **WHEN** a tournament with seven disciplines opens `pools` on a phone
- **THEN** the discipline strip scrolls sideways within itself and the page does not scroll horizontally
