## ADDED Requirements

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
discipline, k and the pool sizes and its day. Per day it states the last end time, and
it also states the exclusion-set load and the bracket collisions.

**The default.** The first variant SHALL be marked as the default.

**Choosing.** Choosing a variant makes it the working version.

**When there are none.** Where the planner returns no variant, the tab SHALL show the
planner's explanation in place of the variants.

#### Scenario: Choosing a variant
- **WHEN** the organizer chooses the second variant
- **THEN** it becomes the working version, and the schedule panel draws it

### Requirement: Decisions are pinned and unpinned
The organizer SHALL be able to pin these decisions:
- a discipline's day;
- a discipline's k;
- an activity's piste and start;
- a fixed sequence of disciplines within a day.

Each pin is listed with what it fixes and can be removed.

**Pins from gates.** Gates elsewhere in the floor add pins of their own. For example,
closing a discipline's check-in pins its N (`floor-checkin`), and announcing a draw pins
its pools (`floor-pools`). A pin a gate added SHALL be marked with its gate. It can only
be removed by reopening that gate.

#### Scenario: A pinned day holds
- **WHEN** the organizer pins Longsword Open to Saturday and asks for variants
- **THEN** every variant places Longsword Open on Saturday

#### Scenario: A gate's pin is not removed from the Plan tab
- **WHEN** a pin was added by closing Sabre's check-in
- **THEN** the Plan tab lists it as the check-in gate's, and offers to reopen check-in instead of a remove control

### Requirement: Publishing is a gate with its obstacles listed
The `plan` tab SHALL offer "Publikovat plán" only for the working version.

**Obstacles.** Before confirming, it SHALL list what prevents publication, in the manner
of the office `PUBLISH` tab:
- a discipline without a format;
- no piste available on a day that holds a discipline;
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

The schedule panel SHALL mark the moved, added and removed activities without colour
beyond the design tokens. When a schedule hangs printed on the wall, "what changed since
the version on the wall" is the output that matters most.

#### Scenario: A moved pool is stated
- **WHEN** re-planning moves Sabre pool 3 from piste 2 at 10:40 to piste 5 at 10:20
- **THEN** the difference lists that pool with both placements

### Requirement: Re-planning is asked for and never automatic
The floor console SHALL never change the working or published plan on its own.

**What starts it.** "Přeplánovat" SHALL build a new working version from the current
state. The current state is:
- the existing pins;
- every activity that has started, frozen where it stands;
- reserve pistes made available.

**Showing it.** The new version is shown with its difference against the published
version. It reaches the floor only when published.

**Slip.** Slip between the published plan and the activities' actual progress SHALL be
shown in the schedule panel once activities report progress (`floor-pools`,
`floor-bracket`).

#### Scenario: Re-planning freezes the past
- **WHEN** the organizer re-plans at 11:00
- **THEN** every activity that started before 11:00 keeps its piste and start in the new working version

### Requirement: The schedule panel draws piste × time
The schedule panel SHALL draw the plan for one chosen day as piste × time:
- the published version where there is one, otherwise the working version;
- each activity labelled with its discipline and pool number or round.

**Time and pistes.** Times are wall-clock times in the tournament's timezone. Reserve
pistes are drawn and marked as reserve.

**Drawing.** The panel SHALL be static markup, with no animation, and SHALL obey the
`design-system` prohibitions.

#### Scenario: The panel shows the day chosen
- **WHEN** the organizer chooses Sunday in the schedule panel
- **THEN** only Sunday's activities are drawn, on Sunday's pistes
