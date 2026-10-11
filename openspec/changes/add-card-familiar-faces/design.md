## Context

`add-fencer-night-skin` gives the card a footer with public counts and adds a
club normalizer. This change fills the footer's left side for signed-in callers.
Brief: `openspec/night-skin-brief.md` §2.

Facts from the code: an account is a `Fencer` with its own `club` and
`nationality` and an optional `hr_id`; `HRFighter` (the global hemaratings index)
holds `club` and `nationality` per `hr_id`; ratings live only in per-tournament
`HRRatingSnapshot`s, taken by the organizer — most upcoming tournaments have none.

## Goals / Non-Goals

**Goals:** a cheap, batched selection; nothing exposed beyond the public rosters;
no change for anonymous visitors.

**Non-Goals:** fuzzy club identity, a club table, live rating lookups against
hemaratings.com, friends or follows.

## Decisions

### D1. Caller identity: HR profile first, account fields as fallback
The brief takes the club from the HR identity only. Many accounts have no bound
profile but did type a club when registering, so the account's own `club` /
`nationality` is the fallback. Without it the feature would be silent for most
first-season fencers.

### D2. Ordering without a snapshot is by name
Rating order uses the tournament's latest snapshot when one exists (max over the
tournament's individual disciplines). Where none exists the order is by name.
Fetching ratings for the list is not worth a cross-tournament snapshot or a live
call; the note never claims "top-rated" on the club basis, and on the country
basis without a snapshot it reads the same — accepted as a known imprecision,
see Open Questions.

### D3. Batched selection
One query loads, for all tournament ids of the response, the seated, listed
entrants with `(tournament_id, fencer_id, name, club, nationality, hr_id)`.
Grouping, normalization, the club→country fallback and the top-three cut run in
Python. Snapshots are loaded once for the tournaments that have them. The cost is
proportional to seated entrants across the listed tournaments, which is small.

### D4. Seated predicate shared with the roster
The same predicate the public roster and `entrant_count` use, so a face never
appears for someone the roster does not list.

## Risks / Trade-offs

- [Club text is free-form; `SK Brno` and `Šermířský klub Brno` differ] →
  Loose normalization only; documented limitation, no fuzzy match.
- [Organizer-enrolled entrants with sparse data] → They match on whatever club
  and nationality their row carries; absent fields simply do not match.
- [A user may find it surprising to see names on cards] → The names are public
  on the rosters already and shown only to signed-in fencers.

## Migration Plan

Additive field; deploy backend before or after frontend. Rollback is a revert.

## Open Questions

- Should the country note avoid "nejvýš hodnocení" when no snapshot exists and
  the order is by name? Proposed: say `{total} z {country}` in that case.
