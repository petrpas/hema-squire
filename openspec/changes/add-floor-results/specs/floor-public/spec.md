## ADDED Requirements

### Requirement: The public program is the published plan by discipline
For a published tournament with a published floor plan, the public SHALL be able to read
a program per discipline:
- the day;
- the planned times of its pools and elimination rounds, in the tournament's timezone;
- once the day runs, the slip `today` states.

**What it never shows:**
- the working plan;
- officials;
- check-in state;
- anything about payments.

#### Scenario: The working plan stays private
- **WHEN** the organizer has a working version that differs from the published one
- **THEN** the public program shows the published version only

### Requirement: Published results are public
The public SHALL be able to read the published standing of each discipline whose results
are published, with name, club and nationality. That is on the same terms as the public
roster names entrants (`public-entrants`).

#### Scenario: Only published disciplines
- **WHEN** Longsword's results are published and Sabre's are not
- **THEN** the public results list Longsword only

### Requirement: A fencer sees their own itinerary
A signed-in fencer who is a person on the tournament's floor SHALL see their itinerary
on the tournament's detail page:
- each pool they are drawn into, with piste and planned time;
- each bracket bout they are seeded or advanced into, with piste and planned time.

**How the fencer is found.** The fencer is matched to their floor person by their
registration's row id, through the office adapter.

**Nobody else's.** The itinerary is visible to that fencer only.

#### Scenario: An itinerary after the draw
- **WHEN** a signed-in fencer drawn into Sabre pool 3 on piste 2 at 10:00 opens the tournament
- **THEN** their itinerary lists Sabre pool 3, piste 2, 10:00

### Requirement: The detail page carries the tournament day once there is one
A published tournament's detail page SHALL offer two tabs from the floor:
- **"Program",** once a floor plan is published;
- **"Výsledky",** once any discipline's results are published.

Neither tab SHALL be shown before then.

**Where the content comes from.** The content is the floor's public answer
(`floor-public`). The detail page renders it and restates none of its rules.

#### Scenario: No program before publication
- **WHEN** a published tournament has no published floor plan
- **THEN** its detail page offers no "Program" tab
