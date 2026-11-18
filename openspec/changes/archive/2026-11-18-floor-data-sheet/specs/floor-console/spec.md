## MODIFIED Requirements

### Requirement: Step tabs choose their discipline by tabs, kept across the console
On `data`, `checkin`, `pools`, `bracket` and `results`, the discipline SHALL be chosen
from a strip of discipline tabs at the head of the work. A drop-down SHALL NOT be used.

**The strip.**
- **Order and names.** It lists the tournament's disciplines in the order floor Setup
  lists them, each by its name.
- **The current one.** It is marked with design-system tokens and never by colour alone.
- **Keyboard.** It is a horizontal tab list, and the left and right arrows move along it.
- **Overflow.** Where the names do not fit the width, the strip scrolls sideways within
  itself and the page does not.

**Prezence alone starts with "Všichni".** It lists every person on the floor roster
(`floor-checkin`, The desk ticks persons, once). It is that tab's address without a
discipline. `data` has no "Všichni".

**Kept across the console.** The discipline last chosen on any step tab SHALL be
carried to the next step tab the organizer opens from the rail. It is carried in that
tab's address, `floorPath(slug, tab, discipline)`.
- **Survives a detour.** Moving through a tab without disciplines (`plan`, `schedule`,
  `today`, `setup`) keeps the choice for the next step tab.
- **"Všichni".** Choosing "Všichni" on `checkin` keeps the choice made before it for
  the other step tabs.
- **Session only.** The choice lives as long as the console is open. It is not stored.
- **Before any choice.** An address without a discipline, with no discipline chosen
  yet, opens the strip's first discipline, or "Všichni" on `checkin`.

#### Scenario: Sabre stays chosen
- **WHEN** the organizer chooses Sabre on `pools`, opens `today`, and then follows the rail to `bracket`
- **THEN** `bracket` opens at Sabre, at `/organizer/cup/floor/bracket/SB`

#### Scenario: Data carries the choice
- **WHEN** the organizer chooses Sabre on `data` and then follows the rail to `checkin`
- **THEN** `checkin` opens at Sabre, at `/organizer/cup/floor/checkin/SB`

#### Scenario: Everybody at the desk
- **WHEN** the organizer opens `checkin` with no discipline chosen yet
- **THEN** "Všichni" is the current tab of the strip and every person is listed

#### Scenario: Many disciplines on a phone
- **WHEN** a tournament with seven disciplines opens `pools` on a phone
- **THEN** the discipline strip scrolls sideways within itself and the page does not scroll horizontally

### Requirement: A tab's operations stand in a panel on the right
Beside the work, the floor console SHALL draw an operations panel for the current tab,
built as the office console's rail is. Its title reads "Operace · <tab label>".

**What the panel holds.** The panel SHALL hold the actions that act on the tab as a
whole, or on the selected discipline, and the parameters of the operation the tab runs:

| Tab | Its operations panel |
|---|---|
| `data` | adding an entrant, or a team on a team discipline; the selected discipline's ratings refresh with its state line; the line saying the discipline's check-in is closed; the link to the office console's Import phase, where the tournament is kept by the organizer |
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
- correcting a cell of the Data sheet, removing an entrant or undoing the removal;
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

#### Scenario: The ratings refresh stands in Data's panel
- **WHEN** the organizer opens `data` at Sabre with Sabre's check-in open
- **THEN** the panel titled "Operace · Data" offers "Přidat účastníka" and "Obnovit ratingy" with Sabre's state line, and each row of the sheet offers its own "Odebrat"

#### Scenario: Přehled has no panel
- **WHEN** the organizer opens `today`
- **THEN** no operations panel is drawn and the matrix takes the full width

#### Scenario: A state with nothing to do
- **WHEN** the organizer opens `pools` at a discipline whose check-in is open
- **THEN** the operations panel states in one line that nothing can be done until check-in closes
