## Context

**Context: floor.** Earlier floor changes produce a closed bracket and a closed pool
ranking per discipline, and a published plan.

**The public surface.** It is the office's: the detail page at `/t/:slug` and its
public API under `/api/tournaments/{slug}`.

**Persons and accounts.** The floor knows persons by roster key. A fencer's account is
an office concept.

## Goals / Non-Goals

**Goals:**
- The final standing, the results tab, export, print, and the publish gate.
- The public program, public results, and the fencer's own itinerary.

**Non-Goals:**
- Submitting results to HEMA Ratings automatically.
- Live bout-by-bout public scoring.
- Results mail.

## Decisions

### D1. The standing in the pure engine
`engine/standing.py` takes the closed bracket's slots and bouts and the closed pool
ranking, and returns the places.

**Ties.** Shared places (semifinal losers without a third-place bout) carry the same
number, and the next place skips accordingly: 1, 2, 3, 3, 5.

### D2. Public endpoints live in the floor and reach the office through the adapter
`app/floor/public.py` is a router under `/api/tournaments/{slug}/floor/public/*`. It is
mounted in `main.py` like `floor/api.py`. Its guard is the office's
`require_public(tournament)`: a published, non-cancelled tournament. The adapter
re-exports it from `app.routers.tournaments`, as it re-exports `TournamentDep`.

**The itinerary.** It needs the signed-in fencer's floor person. The adapter gains
`person_key_for(session, tournament, fencer) -> str | None`. It finds the fencer's live
registration in the tournament, and returns its replay row id (`reg:<id>` or its
`source_row_id`). When that row is joined into a person, it returns the person's anchor
key.

This is the one new office read. It uses `Registration`, through the adapter only, and
it builds no entrant answer. It only maps an account to the key the roster already
issued.

### D3. The detail page renders, the floor decides
The detail page (`TournamentDetail.tsx`) asks the floor's public summary which tabs
exist and renders them. Tab presence, timezone conversion and the slip all come from the
server, as `entrants` D4 argued for rosters.

### D4. Storage
`floor_published_results` holds `tournament_id`, `discipline_id`, `published_at` and
`published_by`. The standing itself is computed, not stored. Its inputs are frozen by
the gates, so it cannot change after publication.

### D5. Imports that cross the floor boundary
- `adapters/office.py` adds:
  - `app.routers.tournaments.require_public`, re-exported;
  - `Registration` from `app.models`, for `person_key_for`.
- The office frontend's detail page calls floor endpoints. This is frontend only, and
  the backend boundary is unchanged.

### D6. Decisions made during implementation (made by me; for the owner's review)
Decided on 2026-11-17 while the owner was away, as asked:
- **Losers of a round are ordered by their bracket seed**, which is their place in the
  closed pool ranking among those who advanced. A team's seed is the team seeding of
  `floor-bracket`.
- **The detail page's tabs are state, not addresses.** "Program" and "Výsledky" sit
  beside the page's other stateful tabs, so `routes.ts` gains nothing (task 4.2 asked
  for addresses). Only Entrants has an address, as before.
- **The itinerary is drawn on the Turnaj tab** above the tournament's face, for a
  signed-in fencer with something to show. It lists their pools and the bracket bouts
  not yet fenced. A bracket bout's time is not shown, because the plan's slot for it
  depends on who advances.
- **A fencer is found by their own registration only.** A fencer who appears only as a
  member of someone else's team has no itinerary yet.
- **The PDF print is the plain table template** of `add-floor-officials`.
- **Retention (task 5.1) is not done.** It waits on the owner's decision, as asked on
  2026-11-16.

## Risks / Trade-offs

- **[The public program could reveal a schedule the organizer is not ready to show.]** →
  Only the published plan is public. Publishing a plan is already a deliberate gate. The
  Plan tab's publish dialog states that the program becomes public.
- **[An itinerary could expose a person's schedule to another account.]** → It is
  served only for the signed-in fencer's own person key, matched server-side.

## Open Questions

- **Retention.** Arrivals, withdrawals, lineups, floor-only persons and piste keys are
  operational data. Bouts and standings are a sporting record. **The owner should
  decide** two things:
  - whether operational floor data is pruned on `data-retention`'s horizon, while
    results are kept as rosters are (owner decision on account deletion: names stay on
    rosters);
  - how long piste keys live after the tournament (proposed: revoked at the end of the
    tournament's last day).
- **HEMA Ratings export format.** The CSV here is Squire's own. Whether to match HEMA
  Ratings' upload format is a question for when it is needed.
