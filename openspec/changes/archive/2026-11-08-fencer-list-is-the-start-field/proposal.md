## Why

The console's fencer list does not list fencers. It lists **registrations** —
contracts carrying money, a seat and an address. On an individual tournament a
contract and a fighter are the same person, which is why nobody noticed. On a
team tournament they come apart: `ttt-2027` holds 18 registrations and 67 people
on rosters, and the tab labelled Fencers shows 18.

Everything downstream inherits that. HR matching, deduplication and the ratings
snapshot all run over sheet rows, so 49 of those 67 fighters are unmatched,
unrated and unknown to the console — and the pools of a team discipline are drawn
from HEMA Ratings. Meanwhile the actions on the list are a mixture: correcting a
discipline and cancelling act on the contract, while matching acts on the person,
and "substitute" hands over the contract rather than replacing a fighter — which
is what an organizer means by the word when a team arrives one fighter short.

The entering fencer is not a captain and need not fight at all: the roster's
prefill is a convenience and "no stored field SHALL mark it as the entrant's"
(`team-disciplines`). So the fencer list is missing the tournament's fighters by
construction, not by accident.

`roster-identity-and-history` gave a roster member an identity that survives a
save. This change spends it.

## What Changes

- **A roster member becomes a row of the console's sheet** — `mem:<id>`, a fourth
  population beside registrations, imported rows and hand-entered rows. It
  carries a name, nationality, club, HEMA Ratings claim and the evidence and
  verdict against it, the team it fights for, and a fixed fencer number. It
  carries no VS, no total, no balance, no seat and no queue place: it is a
  fighter, not a contract.
- **The Fencers phase becomes the tournament's start field**: everyone who will
  fight — the fencers of individual entries, and every roster member. A
  registration that is wholly a team entry, whose holder fights nothing, stops
  appearing there and appears where its agenda is: Teams, Payments, Queue.
- **A row offers the actions its own contract gives it.** A row holding a live
  registration keeps cancelling, correcting its disciplines and rentals, and
  handing over the registration. A member row offers none of those, because it
  holds no registration; what it offers is what a fighter has — identity, and the
  HR binding.
- **Matching and the ratings snapshot reach member rows.** The identifier the
  entrant typed into a roster becomes a *claim*; the index's answer is the
  evidence; the organizer's verdict is a rule, as it is for every other row.
- **A team discipline carries an HR rating category**, which reverses an explicit
  decision (`team-disciplines`: "Team disciplines carry no HR rating category").
  Not to rate a team — a team has no rating — but because its fighters do, and a
  tournament offering only team disciplines maps no taxonomy code today and so
  fetches no rating for anybody. **BREAKING**: the category map stops refusing a
  team discipline's code, and the snapshot stops filtering the codes it fetches by
  the discipline's kind.
- **The Export band gains a tab per team discipline**: its teams in the band's own
  order with each team's fighters beneath, stating each fighter's rating and rank.
  Without it the ratings would be fetched and readable nowhere — rating and rank
  are stated on a discipline tab and on no other. Roster print follows at no cost,
  since it typesets what a tab shows.
- **Deduplication explicitly does not take member rows as candidates.** Two
  rosters naming one person are two fighting places, not a duplicate, and a
  member row beside its own entrant's registration row is one person in two
  roles. Dedup shows candidate groups rather than the fencer list, so this costs
  the phase nothing.
- **The public entrants roster states a team member's identifier from the
  projection**, as it already does for individual rows — so the public stops
  seeing an unverified claim where the console knows the verdict.
- **The Teams phase becomes a table of team entries and moves to sit immediately
  after Fencers**, carrying the team agenda: the roster editor and its log (from
  `roster-identity-and-history`), and cancelling one team of a registration that
  may hold several.
- **BREAKING** for two spec rules, deliberately: the fencer list is no longer one
  population with the phases after it, and the Teams phase is no longer last in
  the fixed phase order.

Out of scope, and named so the gap is not mistaken for an oversight:

- **Seeding a team from its fighters' ratings.** The tab states each fighter's
  rating; how a team is ranked against another from four numbers is a tournament's
  decision and not Squire's, and the organizer seeds with the numbers in hand. The
  seeding tick a discipline tab offers is therefore not offered on a team tab.
- Writing a free-text mail to an entrant, which exists for no population today.
- Linking a person's two rows — an entrant who also fights is matched twice.
- Any change to the **Fencers** tab beyond the rows it inherits: it is the fencer
  list and follows it.

## Capabilities

### Modified Capabilities

- `etl-console`: the fencer list's population is the start field; member rows and
  what they carry; which actions a row offers; the phase order; fixed numbers and
  list order for a population with no registration moment of its own.
- `team-disciplines`: a roster member appears in the console as a fighter; the
  teams view becomes a table carrying the team agenda, including cancelling one
  team.
- `public-entrants`: a team member's identifier is the one the console settled.
- `hr-integration`: the ratings snapshot's population is every row that carries
  an identifier, not every registration; and it fetches a taxonomy code a team
  discipline derives.
- `export-tables`: the band carries a tab per team discipline, and that tab states
  teams with their fighters' ratings.

## Impact

- `backend/app/sheet.py` — a fourth source population and its projection.
- `backend/app/rownumbers.py` and the roster save — a member row is numbered
  where it is born.
- `backend/app/routers/hr_api.py` — the snapshot's identifier set follows the
  projection it already replays.
- `backend/app/hr_sync.py:280` — the snapshot's taxonomy codes stop filtering by
  the discipline's kind.
- `backend/app/routers/tournaments.py:807-815` — the category map stops refusing a
  team discipline's code with `hr_category_map_excludes_team_disciplines`.
- `backend/app/exporttables.py:82` — the band's discipline tabs are no longer
  individual-only; a team discipline's tab states teams and their fighters.
- `backend/app/dedup.py` — member rows are not candidates.
- `backend/app/entrants.py` — a team roster's members read the projection.
- `backend/app/routers/tournaments.py` — the console's teams view becomes a
  table; cancelling one team.
- `frontend/src/Console.tsx`, `SheetArea.tsx` — row actions follow the row;
  phase order; the phase summaries count contracts, not fighters.
- `frontend/src/TeamsPanel.tsx` — the table and the team agenda.
- No migration: `mem:<id>` row ids rest on the member identity the previous
  change made durable.
