## ADDED Requirements

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

## MODIFIED Requirements

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

**Choosing.** Choosing a variant makes it the working version.

**When there are none.** Where the planner returns no variant, the tab SHALL show the
planner's explanation in place of the variants.

**Without a schedule.** With "Plánovat rozvrh" off, the tab SHALL show none of the
following:
- the sensitivity;
- the "Obsazení" section;
- place and sequence pins.

#### Scenario: Choosing a variant
- **WHEN** the organizer chooses the second variant
- **THEN** it becomes the working version, and the schedule panel draws it

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

### Requirement: Re-planning is asked for and never automatic
The floor console SHALL never change the working or published plan on its own.

**What starts it.** "Přeplánovat" SHALL build a new working version from the current
state. The current state is:
- the existing pins;
- every activity that has started, frozen where it stands;
- Setup as it now stands.

Reserve pistes follow the same rule as in a first plan (`floor-planner`). A piste that
serves no discipline stays free. To bring it into a plan, the organizer assigns it to a
discipline in Setup and re-plans.

**Showing it.** The new version is shown with its difference against the published
version. It reaches the floor only when published.

**Slip.** Slip between the published plan and the activities' actual progress SHALL be
shown in the schedule panel once activities report progress (`floor-pools`,
`floor-bracket`).

#### Scenario: Re-planning freezes the past
- **WHEN** the organizer re-plans at 11:00
- **THEN** every activity that started before 11:00 keeps its piste and start in the new working version

#### Scenario: A free piste joins by Setup
- **WHEN** piste 6 serves no discipline, and the organizer assigns it to Sabre as regular and re-plans
- **THEN** the new working version may place Sabre's remaining activities on piste 6

### Requirement: The schedule panel draws piste × time
With a schedule planned, the schedule panel SHALL draw the plan for one chosen day as
piste × time:
- the published version where there is one, otherwise the working version;
- each activity labelled with its discipline and pool number or round.

**Time and pistes.** Times are wall-clock times in the tournament's timezone. The panel
draws every piste that serves a discipline of that day. Its reserve pistes are marked
as reserve.

**Drawing.** The panel SHALL be static markup, with no animation, and SHALL obey the
`design-system` prohibitions.

#### Scenario: The panel shows the day chosen
- **WHEN** the organizer chooses Sunday in the schedule panel
- **THEN** only Sunday's activities are drawn, on the pistes serving Sunday's disciplines
