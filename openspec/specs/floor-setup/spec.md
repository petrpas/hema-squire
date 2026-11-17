# floor-setup Specification

## Purpose
TBD - created by archiving change add-floor-console. Update Purpose after archive.
## Requirements
### Requirement: Days are the tournament's working windows
Floor Setup SHALL hold the tournament's days. Each day has a date, a start time, an end
time, and zero or more fixed breaks, each with a start and an end.

**How times are read.** Times are wall-clock times in the tournament's timezone
(`day-boundaries`).

**What is refused.** A day whose start is not before its end SHALL be refused. So SHALL
a break that does not lie inside its day, and two breaks that overlap.

**The default.** A tournament that has stated no day SHALL be offered one day, on the
tournament's date, from 09:00 to 19:00, with no break. The offer is a default to save,
not a stored day.

#### Scenario: A break outside the day is refused
- **WHEN** the organizer saves a day 09:00–18:00 with a break 18:30–19:00
- **THEN** the save is refused and the break's field states why

#### Scenario: The default day
- **WHEN** a tournament held on 2027-03-06 opens floor Setup for the first time
- **THEN** one day is offered: 2027-03-06, 09:00–19:00, no breaks

### Requirement: Pistes and their availability
Floor Setup SHALL hold the pistes. Each piste has:
- a name;
- the days it is available;
- a `reserve` mark;
- an optional free-text tag, for example "finálová".

**Reserve pistes.** A reserve piste SHALL be unavailable to the planner's first plan and
available to re-planning (`floor-plan`).

**Names.** Piste names SHALL be unique within the tournament.

**Order.** The order in which pistes are listed is their display order.

#### Scenario: A reserve piste is kept back
- **WHEN** a tournament has five pistes and the fifth is marked reserve
- **THEN** floor Setup states that the planner uses four, and the fifth is held for re-planning

### Requirement: Every discipline has a format
Floor Setup SHALL hold one format per discipline. The format refers to the discipline by
the discipline's id (`floor-roster`), never by its slug.

**What a format carries:**
- **Pool size range:** a minimum and a maximum. Default 5–7. The minimum is at least 3
  and the maximum at most 10, the largest pool the bout-order tables cover.
- **Advancing count:** how many advance from the pools to the elimination. It is either
  a number or "all". It SHALL always be set, and its default is "all" (owner decision
  2026-11-16).
- **Bracket kind:** single elimination. No other kind is offered in this change.
- **Third-place bout:** yes or no. Default no.
- **Piste staffing template:** how many officials of each role one piste needs while
  this discipline runs, for example one referee alone, or one referee and one judge.
  It has no default. The organizer states it per discipline, because practice differs
  between tournaments and between disciplines (owner decision 2026-11-16). At least
  one referee is required.
- **Slot lengths, in minutes,** as parameters the organizer may change. Their
  defaults are starting values:
  - a pool bout, default 4;
  - an elimination bout, default 6;
  - the changeover overhead per pool, default 5.

  A team discipline also states a team match, default 25.

**What is refused.** A format whose minimum exceeds its maximum SHALL be refused. So
SHALL an advancing count below 2, a slot length that is not a positive whole number
of minutes, and a staffing template without a referee.

**What "incomplete" means.** A discipline with no saved format is incomplete, and so is
one whose staffing template was never stated. It counts
as a waiting condition for the `setup` badge, and it is what the planner refuses to
plan.

**Formats of team disciplines.** A team discipline's pools are individual pools of its
teams' members. Its elimination is a team elimination (owner decision 2026-11-16).
Floor Setup states this beside a team discipline's format and offers no other choice.

#### Scenario: The advancing count is always stated
- **WHEN** the organizer opens a discipline's format that was never saved
- **THEN** the advancing count reads "all" and is saved as such with the format

#### Scenario: Staffing differs by discipline
- **WHEN** the organizer states one referee for Longsword and one referee with one judge for Sabre
- **THEN** both formats save, and the planner and the officials assignment staff each discipline's pistes by its own template

#### Scenario: Staffing is never assumed
- **WHEN** a discipline's format was saved before its staffing template was stated
- **THEN** the discipline is incomplete and the `setup` badge counts it

#### Scenario: A team discipline's format names both stages
- **WHEN** the organizer opens the format of a team discipline
- **THEN** it states individual pools of the members followed by a team elimination, and asks for the team match slot

### Requirement: Officials and their availability
Floor Setup SHALL hold the tournament's officials. Each official has:
- a name;
- an optional link to a person on the floor roster, by person key;
- the roles they can fill, among referee, judge and table official;
- the disciplines they may officiate;
- the days they are available.

**Officials who also fence.** An official who also fences SHALL be linked to their
roster person, not entered twice. The planner and the officials assignment read the
link to keep that person off a piste while they fence (`floor-officials`).

**Links that are no longer valid.** A link whose person has left the floor roster SHALL
be stated as such beside the official. It SHALL NOT be dropped silently.

#### Scenario: An official who fences is one person
- **WHEN** the organizer links the official "Jan Novák" to the roster person Jan Novák
- **THEN** the official's row names the link, and both the roster and the official refer to the one person key

#### Scenario: A link whose person left is stated
- **WHEN** the linked person's registration is cancelled
- **THEN** the official keeps their name and roles, and the row states that the link no longer finds a person

### Requirement: Parameters have a default and one editor
Floor Setup SHALL hold the organizer's parameters, in three kinds:

| Kind | Parameter | Default |
|---|---|---|
| hard rule | pool sizes within a discipline differ by at most 1 | on, not editable |
| hard rule | finals after every non-final activity of their day | on |
| soft preference | prefer larger pools | on |
| soft preference | draw weight of club separation | 10 |
| soft preference | draw weight of nationality spread | 3 |
| estimate constant | minimum rest between a person's activities, minutes | 10 |

**Where parameters are edited.** Every parameter SHALL have its default and SHALL be
editable only in floor Setup. No step panel of the floor console offers a field for one.

**How kinds are labelled.** The kind of each parameter SHALL be stated beside it in
words: "pravidlo", "preference" or "odhad".

#### Scenario: A parameter is not edited from a step
- **WHEN** the organizer is on the `pools` tab
- **THEN** no field there edits a draw weight, and the weights are read from floor Setup

### Requirement: Floor Setup saves as office Setup does
Floor Setup SHALL follow the office Setup's saving rules (`setup-navigation`):
- one save control per section;
- row tables are drafts until saved;
- leaving with unsaved changes is confirmed.

Each save SHALL be refused with field-level messages rather than partially stored.

#### Scenario: Leaving with unsaved pistes
- **WHEN** the organizer has added a piste without saving and follows a link to `data`
- **THEN** the console asks for confirmation before leaving

