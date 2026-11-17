## ADDED Requirements

### Requirement: Floor Setup has its own tabs
Floor Setup SHALL lay its sections out as small tabs across the top of the work area, as
office Setup does (`setup-navigation`). The tabs are, in this order:

| Tab | Label | Shown |
|---|---|---|
| `scope` | Rozsah | always |
| `schedule` | Rozvrh | with "Plánovat rozvrh" |
| `formats` | Disciplíny | always |
| `officials` | Rozhodčí | with "Plánovat rozhodčí" |
| `pistes` | Planše | with "Plánovat rozvrh" |
| `params` | Parametry | with "Plánovat rozvrh" |

Labels start with a capital letter, and the rest of the label is lowercase.

**Where it opens.** Floor Setup SHALL open on the first tab that holds something
incomplete, and on `scope` when nothing is incomplete.

**Markers.** A tab holding something incomplete SHALL carry the per-tab marker office
Setup uses. A tab holding unsaved edits SHALL carry the unsaved marker.

**Drafts.** Switching between Setup's tabs SHALL NOT discard and SHALL NOT save a
draft.

#### Scenario: Unsaved edits survive a tab switch
- **WHEN** the organizer changes a pool range on Disciplíny, switches to Planše, and comes back
- **THEN** the changed range is still in the field, unsaved, and Disciplíny carries the unsaved marker

#### Scenario: Setup opens where something is missing
- **WHEN** a discipline has no saved format and everything else is complete
- **THEN** floor Setup opens on Disciplíny

### Requirement: Scope decides what is planned
The `scope` tab SHALL hold three ticks:
- **"Plánovat rozvrh"**, default on. Off means the floor plans no schedule. The planner
  plans only the pool structure (`floor-planner`), and the Rozvrh, Planše and Parametry
  tabs are not shown.
- **"Vícedenní turnaj"**, under "Plánovat rozvrh" and available only with it on.
  Default off. Off means the tournament has exactly one day.
- **"Plánovat rozhodčí"**, default off. It is available only with "Plánovat rozvrh" on.
  Without the schedule it is greyed out and reads off, because officials are assigned
  to the schedule's blocks (`floor-officials`). Off means:
  - the Rozhodčí tab is not shown;
  - formats ask for no referee counts;
  - the planner counts no officials;
  - no assignment is made.

**Hiding keeps what is stored.** A tick turned off SHALL hide what it governs and SHALL
NOT delete it. Turning the tick back on shows it again as it was. While a tick is off,
nothing it hides counts as incomplete, and the planner reads none of it.

**Leaving several days.** Turning "Vícedenní turnaj" off SHALL be refused while more
than one day is stated. The refusal says to remove the other days first.

#### Scenario: No schedule, only pools
- **WHEN** the organizer turns "Plánovat rozvrh" off
- **THEN** Setup offers Rozsah and Disciplíny only, "Plánovat rozhodčí" is greyed out, and the `plan` tab plans pool counts without times

#### Scenario: Officials hidden, not deleted
- **WHEN** the organizer has stated six officials and turns "Plánovat rozhodčí" off and on again
- **THEN** the six officials are listed again as they were

#### Scenario: Two days cannot become one by a tick
- **WHEN** two days are stated and the organizer turns "Vícedenní turnaj" off
- **THEN** the change is refused, saying to remove the second day first

### Requirement: A discipline may take over another discipline's pool results
A discipline's format SHALL offer "Převzít skupinové výsledky z". It names another
discipline of the same weapon, or none. The default is none.

**What it means.** A discipline that takes over (the target) fences no pools of its
own. Its elimination is seeded from the source's closed overall pool ranking
(`floor-bracket`).
- A team target ranks its teams by their members' places in the source's ranking.
- An individual target ranks its fencers by their places in a team source's member
  pools.

**What is offered.** The choice SHALL list only disciplines other than this one:
- of the same weapon, compared without regard to case;
- that do not take over themselves.

**What is refused.** The following SHALL be refused:
- naming a source that itself takes over;
- a source that another discipline's take-over makes impossible, such as two
  disciplines naming each other;
- with the schedule planned, a target whose day is before its source's day.

**What the format then asks.** A target's format asks for no pool range, no
pool-bout points and no pause between pools. It states the source in their place.

#### Scenario: Team takes over the individual pools
- **WHEN** Longsword Teams takes over the pool results of Longsword Open
- **THEN** Longsword Teams has no pools, and its format states "Skupiny převzaty z Longsword Open"

#### Scenario: Only the same weapon is offered
- **WHEN** a tournament has Longsword Open, Longsword Women and Sabre Open
- **THEN** Longsword Women is offered Longsword Open as a source, and Sabre Open is not offered

## MODIFIED Requirements

### Requirement: Days are the tournament's working windows
With "Plánovat rozvrh" on, floor Setup's `schedule` tab SHALL hold the tournament's
days as a table. Each row has these columns:
- a date;
- a start time (od);
- an end time (do);
- the disciplines held that day;
- the day's breaks (přestávka), zero or more, each with a start and an end.

**Editing disciplines and breaks.** The disciplines and the breaks SHALL be edited in a
dialog (`Modal`) opened from the row. The row shows them as text: the disciplines'
names, and each break as its start and end.

**One day per discipline.** Every discipline SHALL belong to exactly one day. The
dialog offers every discipline. A discipline already ticked on another day is shown
with that day's date, and ticking it here moves it.

**One-day tournaments.** With "Vícedenní turnaj" off, the table has exactly one row and
offers no "add day". Every discipline belongs to that day. The disciplines cell reads
"všechny", and the dialog edits only breaks.

**How times are read.** Times are wall-clock times in the tournament's timezone
(`day-boundaries`).

**What is refused.** The following SHALL be refused:
- a day whose start is not before its end;
- a break that does not lie inside its day;
- two breaks that overlap.

**What is incomplete.** With "Vícedenní turnaj" on, a discipline that belongs to no day
is incomplete.

**The default.** A tournament that has stated no day SHALL be offered one day, on the
tournament's date, from 09:00 to 19:00, with no break. The offer is a default to save,
not a stored day.

#### Scenario: A break outside the day is refused
- **WHEN** the organizer saves a day 09:00–18:00 with a break 18:30–19:00
- **THEN** the save is refused and the break states why

#### Scenario: The default day
- **WHEN** a tournament held on 2027-03-06 opens floor Setup for the first time
- **THEN** one day is offered: 2027-03-06, 09:00–19:00, no breaks

#### Scenario: Ticking a discipline moves it
- **WHEN** Sabre Open belongs to Saturday and the organizer ticks it in Sunday's dialog
- **THEN** Sabre Open belongs to Sunday and no longer to Saturday

#### Scenario: A discipline without a day is incomplete
- **WHEN** a two-day tournament has Rapier ticked on neither day
- **THEN** the Rozvrh tab carries the incomplete marker and names Rapier

### Requirement: Pistes and their availability
With "Plánovat rozvrh" on, floor Setup's `pistes` tab SHALL hold the pistes. Each piste
has:
- a name;
- the disciplines it serves, each either **regular** or **reserve**.

**Editing the disciplines.** The disciplines SHALL be edited in a dialog, as a day's
disciplines are. Each discipline is one of "ne", "běžně" or "rezerva".

**Days.** A piste has no days of its own. It is available on the days its disciplines
are held.

**Reserve.** A piste serving a discipline as reserve is planned on for that discipline
with lower priority (`floor-planner`): only where the discipline's day cannot be planned
on its regular pistes.

**Free pistes.** A piste that serves no discipline SHALL never be planned on. The Planše
tab states that it stays free for use on the spot.

**Names.** Piste names SHALL be unique within the tournament.

**Order.** The order in which pistes are listed is their display order.

**What is incomplete.** A discipline that no piste serves as regular is incomplete.

#### Scenario: A reserve piste is held back
- **WHEN** Longsword Open is served by pistes 1–4 as regular and piste 5 as reserve, and its day fits on pistes 1–4
- **THEN** the plan uses pistes 1–4 for Longsword Open and leaves piste 5 empty

#### Scenario: A free piste is stated
- **WHEN** piste 6 serves no discipline
- **THEN** the Planše tab states that piste 6 stays free for use on the spot, and no plan places an activity on it

### Requirement: Every discipline has a format
Floor Setup's `formats` tab SHALL hold one format per discipline. The format refers to
the discipline by the discipline's id (`floor-roster`), never by its slug.

**What a format carries:**
- **Pool size range:** a minimum and a maximum. Default 5–7. The minimum is at least 3
  and the maximum at most 10, the largest pool the bout-order tables cover.
- **Advancing count:** a choice between "všichni" and a fixed number. It SHALL always
  be set, and its default is "všichni" (owner decision 2026-11-16).
- **Bracket kind:** single elimination. No other kind is offered in this change.
- **Third-place bout:** yes or no. Default yes.
- **Referees per bout**, asked only with "Plánovat rozhodčí" on:
  - one number for pools;
  - one number for the elimination.

  Each defaults to 1 and is at least 1. No other official role is asked for (owner
  decision 2026-11-17).
- **Point targets**, each optional:
  - a pool bout;
  - an individual discipline's elimination bout;
  - a team discipline's team bout.

  A team discipline asks for points per bout, and states the match total beside it:
  "Počet bodů na střet: [5], celkem do 45 bodů". The total is the points times k²,
  where k is the discipline's minimum team size. In a 3-on-3 match, that is nine bouts.
  An individual discipline is not asked for team points, and a team discipline is not
  asked for an elimination bout target.
- **Take-over:** "Převzít skupinové výsledky z" (see A discipline may take over another
  discipline's pool results).
- **Lengths in minutes**, asked only with "Plánovat rozvrh" on. The organizer may change
  them, and their defaults are starting values:
  - a pool bout, default 4;
  - an elimination bout, default 6;
  - "Pauza mezi skupinami", the pause a piste keeps after each pool, default 10.

  A team discipline also states a team match, default 25.

**What is refused.** The following SHALL be refused:
- a minimum pool size above the maximum;
- an advancing count below 2;
- a length that is not a positive whole number of minutes;
- a referee count below 1;
- a point target that is not a positive whole number.

**What "incomplete" means.** A discipline with no saved format is incomplete. It counts
as a waiting condition for the `setup` badge, and it is what the planner refuses to
plan.

**Formats of team disciplines.** A team discipline's pools are individual pools of its
teams' members, unless it takes over. Its elimination is a team elimination (owner
decision 2026-11-16). Floor Setup states this beside a team discipline's format and
offers no other choice.

#### Scenario: The advancing count is always stated
- **WHEN** the organizer opens a discipline's format that was never saved
- **THEN** the advancing count reads "všichni", the third-place bout reads yes, and both are saved with the format

#### Scenario: Referees differ by stage
- **WHEN** "Plánovat rozhodčí" is on and the organizer states one referee for pools and two for the elimination of Sabre
- **THEN** the format saves, and Sabre's pool blocks are staffed by one referee and its elimination blocks by two

#### Scenario: Team points state their total
- **WHEN** a team discipline with team sizes 3–5 states 5 points per bout
- **THEN** the format reads "Počet bodů na střet: 5, celkem do 45 bodů"

#### Scenario: A team discipline's format names both stages
- **WHEN** the organizer opens the format of a team discipline that takes over nothing
- **THEN** it states individual pools of the members followed by a team elimination, and asks for the team match length

### Requirement: Officials and their availability
With "Plánovat rozhodčí" on, floor Setup's `officials` tab SHALL hold the tournament's
officials. Every official is a referee. Each official has:
- **"Šermuje jako"**, an optional link to a person on the floor roster, by person key.
  It is the row's first field.
- **A name.** While "Šermuje jako" names a person, the name field is greyed out and
  shows that person's name, which is the name used. Without a link, the name is typed.
- **"Hlavní rozhodčí"**, a tick, default yes. It marks a referee who can lead a piste
  (`floor-officials`, A block has one main referee).
- **Disciplines.** Each is one of "ne", "běžně" or "rezerva", edited in a dialog as a
  piste's disciplines are.
- **Days available.** These are asked only with "Vícedenní turnaj" on. On a one-day
  tournament every official is available on the day.

**Reserve officials.** An official who serves a discipline as reserve SHALL be assigned
to that discipline only where no regular official can fill the role (`floor-officials`).

**Officials who also fence.** An official who also fences SHALL be linked to their
roster person, not entered twice. The planner and the officials assignment read the
link to keep that person off a piste while they fence (`floor-officials`).

**Links that are no longer valid.** A link whose person has left the floor roster SHALL
be stated as such beside the official. The official keeps the last name the link gave.
The link SHALL NOT be dropped silently.

#### Scenario: Choosing the fencer greys out the name
- **WHEN** the organizer chooses Jan Novák in "Šermuje jako"
- **THEN** the name field is greyed out and reads Jan Novák, and the roster and the official refer to the one person key

#### Scenario: A link whose person left is stated
- **WHEN** the linked person's registration is cancelled
- **THEN** the official keeps the name Jan Novák and their disciplines, and the row states that the link no longer finds a person

#### Scenario: A new referee is a main referee
- **WHEN** the organizer adds an official
- **THEN** "Hlavní rozhodčí" is ticked, and the organizer may untick it

#### Scenario: Reserve is per discipline
- **WHEN** Eva serves Longsword Open as regular and Sabre Open as reserve
- **THEN** Eva is assigned in Sabre only where no regular Sabre referee can fill the role

### Requirement: Parameters have a default and one editor
Floor Setup's `params` tab SHALL hold these parameters:

| Kind | Parameter | Default |
|---|---|---|
| hard rule | finals: "v rámci eliminace", "na konci dne" or "na konci turnaje" | v rámci eliminace |
| estimate constant | minimum rest between a person's activities, minutes | 10 |

**Rules that are not choices.** A rule that is not a choice SHALL NOT be shown as a
parameter. Pool sizes within a discipline differ by at most one, always
(`floor-planner`), and nothing in Setup states it as a setting.

**The plan's own preferences.** The pool-size preference and the draw weights are the
`plan` tab's (`floor-plan`). Floor Setup offers no field for them.

**Where parameters are edited.** Every parameter SHALL have its default. Each SHALL be
editable in one place only: those above in floor Setup, and the plan's preferences on
the `plan` tab. No other step panel offers a field for one.

**How kinds are labelled.** The kind of each parameter SHALL be stated beside it in
words: "pravidlo", "preference" or "odhad".

#### Scenario: A weight is not edited from a step
- **WHEN** the organizer is on the `pools` tab
- **THEN** no field there edits a draw weight, and the weights are read from the `plan` tab's preferences

#### Scenario: Finals default to the elimination's own order
- **WHEN** the organizer opens Parametry for the first time
- **THEN** finals read "v rámci eliminace" and the minimum rest reads 10

### Requirement: Floor Setup saves as office Setup does
Floor Setup SHALL follow the office Setup's saving rules (`setup-navigation`):
- one save control per tab;
- row tables and dialogs are drafts until the tab is saved;
- leaving the console's Setup with unsaved changes is confirmed.

Each save SHALL be refused with field-level messages rather than partially stored. A
dialog's choices are part of its tab's draft. Closing the dialog keeps them in the
draft and saves nothing.

#### Scenario: Leaving with unsaved pistes
- **WHEN** the organizer has added a piste without saving and follows the rail to `data`
- **THEN** the console asks for confirmation before leaving

#### Scenario: A dialog does not save
- **WHEN** the organizer ticks Sabre in Saturday's dialog and closes it
- **THEN** Saturday's row names Sabre, Rozvrh carries the unsaved marker, and nothing is stored until Rozvrh is saved
