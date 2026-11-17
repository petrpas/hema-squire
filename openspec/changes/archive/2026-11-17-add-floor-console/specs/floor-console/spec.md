## ADDED Requirements

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
The floor console SHALL offer eight tabs in this order:

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

Labels start with a capital letter, and the rest of the label is lowercase.

**Which tabs are shown.** No tab SHALL be added or removed by a setting, and none
reordered. What a tournament's settings change is a tab's content: sections about teams
appear only where the tournament has a team discipline.

**The default tab.** An address naming no tab, or a tab that does not exist, SHALL
resolve to `today` once a plan has been published, and to `setup` before then.

**Tabs whose change has not landed.** A tab whose change has not been implemented SHALL
state that it is not available yet, in one line. It SHALL NOT be hidden.

#### Scenario: Order does not depend on settings
- **WHEN** a tournament with no team discipline opens its floor console
- **THEN** all eight tabs are offered in the order above

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
On a wide screen the floor console SHALL reserve a panel beside every tab except
`setup`, for the schedule. The live schedule is drawn there once `floor-plan` exists;
until then the panel states that no plan has been made.

On a narrow screen the panel SHALL become a ninth, last tab named "Rozvrh". It works
the same way the Setup preview does (`setup-preview`, Setup shows the preview beside the
settings, or as their last tab).

The breakpoint SHALL be the canonical one (`responsive-layout`).

#### Scenario: The panel becomes a tab on a phone
- **WHEN** the floor console is opened below the canonical breakpoint
- **THEN** "Rozvrh" is offered as the last tab and no side panel is drawn
