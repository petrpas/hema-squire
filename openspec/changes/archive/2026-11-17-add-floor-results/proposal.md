## Why

A tournament day ends with a final standing per discipline. That standing is printed,
announced, exported for HEMA Ratings and published.

During the day, fencers and spectators also want to know what runs when, and fencers
want to know where they fence next. The owner's planner document lists these as
projections of the one plan:
- by discipline: a public timeline;
- by person: a fencer's itinerary;
- by activity: printed sheets.

This change closes the loop.

**Context:** floor. It touches the office's public surface. The tournament detail page
gains "Program" and "Výsledky" tabs, and a signed-in fencer's view gains an itinerary.
The data comes from public floor endpoints. The office page renders them, and nothing in
the office backend imports `app.floor`.

## What Changes

- **Final standing per discipline:**
  - **From the bracket:** 1 and 2 from the final. 3 and 4 from the third-place bout
    where there is one, otherwise both semifinal losers share 3. The losers of each
    earlier round are ranked among themselves by the closed pool ranking.
  - **Below them,** those who did not advance, by pool ranking.
  - **Team disciplines** rank teams the same way.
- **Výsledky (`results`):**
  - the final standing;
  - export as CSV: the standing, and every bout with the pool or round;
  - a PDF print.
- **"Zveřejnit výsledky"** is a gate per discipline. It is offered once the bracket is
  closed, and it publishes that discipline's standing.
- **Public.** For a published tournament, its detail page gains:
  - **"Program":** the published plan's timeline per discipline. It shows the day, the
    pools' and rounds' planned times, and the slip once the day runs.
  - **"Výsledky":** the published standings.

  Both appear only once there is something to show. Names are public on the same terms
  as the public roster (`public-entrants`).
- **Itinerary.** A signed-in fencer sees, on the tournament's detail page, their own
  itinerary: their pools with piste and time, and their bracket bouts as they are
  seeded. The fencer is matched to the floor person through the office adapter.
- **On `today`,** the Výsledky column states "čeká" or "zveřejněny".

## Capabilities

### New Capabilities
- `floor-results`: the final standing, the results tab, export, print, and the publish
  gate.
- `floor-public`: the public Program and Výsledky tabs on the detail page, and the
  fencer's itinerary.

### Modified Capabilities
None. The detail page's two new tabs are stated in `floor-public`, which owns what they
show and when. `public-browsing` is not modified, because a floor change modifies only
`floor-*` capabilities.

## Impact

- **Backend:**
  - `app/floor/results.py`;
  - `app/floor/public.py` (public router);
  - the adapter gains `person_key_for(fencer)` and re-exports the public-read guard
    `require_public`;
  - table `floor_published_results`, migration `floor_0007`.
- **Frontend:**
  - `frontend/src/floor/results/`;
  - the detail page (`TournamentDetail.tsx`) gains two tabs, rendered from the public
    floor endpoints;
  - `routes.ts` gains their addresses.
- **Office:**
  - `retention.py` and `account_deletion.py` gain floor classifications (see the
    design's open question on retention).
