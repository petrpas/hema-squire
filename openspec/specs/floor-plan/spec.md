# floor-plan Specification

## Purpose
TBD - created by archiving change add-floor-planner. Update Purpose after archive.
## Requirements
### Requirement: A plan is a stored version
A tournament's plan SHALL be stored as versions. Each version records:
- its activities: discipline, kind, pool number or round, piste, start, end;
- its metrics;
- the moment it was made, and by whom.

**How versions relate.** A tournament SHALL have at most one working version and at most
one published version. Publishing makes the working version the published one.

**Old versions.** Earlier published versions SHALL be kept, read-only, as history.

#### Scenario: Publishing replaces the published version
- **WHEN** the organizer publishes a working version while version 3 is published
- **THEN** the new version is published, and version 3 is kept as history

### Requirement: The organizer chooses a variant on the Plan tab
The `plan` tab SHALL present the planner's variants side by side. Each states, per
discipline, k and the pool sizes.
- **With a schedule planned,** each variant also states:
  - per discipline, its day;
  - per day, the last end time;
  - the exclusion-set load;
  - the bracket collisions;
  - the reserve pistes it uses.
- **A discipline that takes over** states its source in place of k.

**The default.** The first variant SHALL be marked as the default.

**Choosing.** Choosing a variant makes it the working version. Each variant carries its
own choice in the work. Asking for variants is an action of the tab's operations panel
(`floor-console`, A tab's operations stand in a panel on the right).

**When there are none.** Where the planner returns no variant, the tab SHALL show the
planner's explanation in place of the variants.

**Without a schedule.** With "Plánovat rozvrh" off, the tab SHALL show none of the
following:
- the sensitivity;
- the "Obsazení" section;
- place and sequence pins.

#### Scenario: Choosing a variant
- **WHEN** the organizer chooses the second variant
- **THEN** it becomes the working version, and the `schedule` tab draws it

#### Scenario: Choosing pool counts only
- **WHEN** "Plánovat rozvrh" is off and the organizer chooses a variant
- **THEN** it becomes the working version, stating k and pool sizes per discipline, with no times

### Requirement: Decisions are pinned and unpinned
The organizer SHALL be able to pin these decisions:
- a discipline's k;
- with a schedule planned, an activity's piste and start;
- with a schedule planned, a fixed sequence of disciplines within a day.

A discipline's day is not pinned. It is set in floor Setup (`floor-setup`).

Each pin is listed with what it fixes and can be removed.

**Pins from gates.** Gates elsewhere in the floor add pins of their own. For example,
closing a discipline's check-in pins its N (`floor-checkin`), and announcing a draw pins
its pools (`floor-pools`). A pin a gate added SHALL be marked with its gate. It can only
be removed by reopening that gate.

**Existing day pins.** A day pin stored before this change SHALL become the
discipline's day in floor Setup, and the pin is removed.

#### Scenario: A pinned k holds
- **WHEN** the organizer pins Longsword Open to k = 4 and asks for variants
- **THEN** every variant gives Longsword Open four pools

#### Scenario: A gate's pin is not removed from the Plan tab
- **WHEN** a pin was added by closing Sabre's check-in
- **THEN** the Plan tab lists it as the check-in gate's, and offers to reopen check-in instead of a remove control

### Requirement: Publishing is a gate with its obstacles listed
The `plan` tab SHALL offer "Publikovat plán" only for the working version.

**Obstacles.** Before confirming, it SHALL list what prevents publication, in the manner
of the office `PUBLISH` tab:
- a discipline without a format;
- with a schedule planned:
  - a discipline without a day;
  - a discipline that no piste serves as regular;
  - an exclusion-set shortage.

Publication SHALL be refused while an obstacle stands.

**After publication.** Once published, the floor console's default tab becomes `today`.

#### Scenario: An obstacle blocks publication
- **WHEN** the working version has an exclusion-set shortage in Longsword Open
- **THEN** "Publikovat plán" lists the shortage, and publication is refused

### Requirement: The working plan is compared with the published one
Where both a working and a published version exist, the floor console SHALL state their
difference:
- activities moved (to another piste or start), with the old and new placement;
- activities added;
- activities removed.

The `plan` tab states the difference in its work. The `schedule` tab, showing the
working version, SHALL mark the moved, added and removed activities without colour
beyond the design tokens. When a schedule hangs printed on the wall, "what changed
since the version on the wall" is the output that matters most.

#### Scenario: A moved pool is stated
- **WHEN** re-planning moves Sabre pool 3 from piste 2 at 10:40 to piste 5 at 10:20
- **THEN** the difference lists that pool with both placements

#### Scenario: The change is marked on Rozvrh
- **WHEN** the organizer opens `schedule` and switches it to the working version after that re-plan
- **THEN** Sabre pool 3 is drawn on piste 5 marked as moved, and its old placement is marked as removed

### Requirement: Re-planning is asked for and never automatic
The floor console SHALL never change the working or published plan on its own.

**What starts it.** "Přeplánovat" SHALL build a new working version from the current
state. It is an action of the `plan` tab's operations panel. The current state is:
- the existing pins;
- every activity that has started, frozen where it stands;
- Setup as it now stands.

Reserve pistes follow the same rule as in a first plan (`floor-planner`). A piste that
serves no discipline stays free. To bring it into a plan, the organizer assigns it to a
discipline in Setup and re-plans.

**Showing it.** The new version is shown with its difference against the published
version. It reaches the floor only when published.

**Slip.** Slip between the published plan and the activities' actual progress SHALL be
shown on the `schedule` tab once activities report progress (`floor-pools`,
`floor-bracket`).

#### Scenario: Re-planning freezes the past
- **WHEN** the organizer re-plans at 11:00
- **THEN** every activity that started before 11:00 keeps its piste and start in the new working version

#### Scenario: A free piste joins by Setup
- **WHEN** piste 6 serves no discipline, and the organizer assigns it to Sabre as regular and re-plans
- **THEN** the new working version may place Sabre's remaining activities on piste 6

### Requirement: The plan's preferences are edited on the Plan tab
The `plan` tab SHALL hold the plan's preferences, above the variants, with one save:

| Kind | Preference | Default |
|---|---|---|
| preference | pool size: "větší skupiny" or "menší skupiny" | větší skupiny |
| preference | draw weight of club separation | 10 |
| preference | draw weight of nationality spread | 3 |

Each preference's kind is stated beside it in words, as in floor Setup.

**What a change does.** The pool-size preference orders the variants
(`floor-planner`). Changing it re-orders them the next time variants are asked for, and
never changes the working or published version by itself. The draw weights are read by
the draw (`floor-draw`). A draw already announced keeps the weights it was drawn with.

**Where else they are edited.** No other tab offers a field for them.

#### Scenario: The preference re-orders the variants
- **WHEN** the organizer switches the preference to "menší skupiny" and asks for variants
- **THEN** the variant with smaller pools comes first among otherwise equal variants, and the working version is unchanged

#### Scenario: Weights are not on the pools tab
- **WHEN** the organizer opens the `pools` tab
- **THEN** it offers no field for a draw weight, and the draw uses the weights saved on the `plan` tab

### Requirement: Rozvrh draws piste × time
With a schedule planned, the `schedule` tab ("Rozvrh") SHALL draw the plan for one
chosen day as piste × time. It is the whole of the tab's work, at the full width, with
no operations panel.

**What is drawn.**
- **The version.** It draws the published version where there is one, otherwise the
  working version.
- **The other version.** Where both exist, a choice at the head of the work switches to
  the working version, with its changes marked against the published one.
- **The day.** Where the plan spans more than one day, a choice of day stands at the
  head of the work, and the first day is chosen until another is.
- **Each activity.** Each activity is labelled with its discipline and pool number or
  round.

**Until a plan exists.** The tab states in one line that no plan has been made.

**Time and pistes.** Times are wall-clock times in the tournament's timezone. The tab
draws every piste that serves a discipline of that day. Its reserve pistes are marked
as reserve.

**Fresh on arrival.** The tab SHALL read the plan again each time it is opened, so a
version chosen or published on `plan` is what it draws.

**Drawing.** The grid SHALL be static markup, with no animation, and SHALL obey the
`design-system` prohibitions.

#### Scenario: The tab shows the day chosen
- **WHEN** the organizer chooses Sunday on the `schedule` tab
- **THEN** only Sunday's activities are drawn, on the pistes serving Sunday's disciplines

#### Scenario: A published plan is drawn on arrival
- **WHEN** the organizer publishes on `plan` and then follows the rail to `schedule`
- **THEN** the published version is drawn, and no operations panel stands beside it

