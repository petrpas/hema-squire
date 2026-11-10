## Context

See proposal.md — Why. The ground this stands on:

- **This change requires `roster-identity-and-history` to have landed.** A member
  row is `mem:<member_id>`, and before that change every roster save deleted and
  recreated its members, so the id — and every rule, verdict and number hanging
  off it — would not survive the entrant's next edit. The team-disciplines delta
  here is written against that change's requirements, including the renamed
  **Organizer's teams view**.
- **The projection already carries three populations** keyed by stable row ids
  (`sheet.py`: `reg:`, `imp:<fingerprint>`, `man:`), and the rule machinery is
  keyed on `target` = row id and knows nothing about which population a row came
  from (`rules.py:39-93`). A fourth population needs no new machinery.
- **Row actions are already a function of the row**, not of the tab:
  `rowAction(row, phase)` asks `holdsLiveRegistration(row)`, and `onResendLink`
  is offered only on a guest's row.
- **Numbers are allocated where a row is born, never while the sheet is read**
  (`rownumbers.py`), and a deleted row keeps its number so a restore returns it.
- **Public entrants already read individual identifiers from the projection**
  (`entrants.py:258,385`) and team members from the stored roster (`:317`) — so
  the public roster shows a verdict for one population and an unverified claim
  for the other. One source settles it.
- **The ratings snapshot replays the projection** and takes its identifiers from
  the rows (`routers/hr_api.py:52-62`), so it follows the population by itself.
- **Three places enforce "no category for a team discipline"**, and all three must
  move together: the category map *refuses* a team code with a 422
  (`routers/tournaments.py:807-815`), the snapshot filters its taxonomy codes to
  individual disciplines (`hr_sync.py:280`), and the export band builds its
  discipline tabs from individual disciplines alone (`exporttables.py:82`).
- **A taxonomy code is already shared** between an individual and a team
  discipline classified alike (`taxonomy.py`, and the map is keyed by code). So on
  a tournament offering sabre both ways, the entry already exists and the fetch is
  already made — the broken case is the tournament that offers team disciplines
  only, which is the shape that prompted this.
- **Rating and rank are stated on a discipline tab and nowhere else**
  (`export-tables`, Each tab states its own columns and order). The Fencers tab has
  no rating column, so a fetched rating with no team tab to show it would be
  unreadable.

## Goals / Non-Goals

**Goals:**

- The fencer list answers "who is coming to fight", for every tournament shape.
- A team discipline's fighters carry ratings the organizer can read and seed with,
  which is the purpose the whole line of work exists for.
- A fighter who holds no registration is nevertheless a first-class row: matched,
  numbered, correctable.
- Each row offers exactly the actions its own registration gives it, with no tab
  deciding on its behalf.

**Non-Goals:**

- Seeding a team from its fighters' ratings. The tab hands the organizer four
  numbers; which team that puts first is the tournament's decision.
- Linking a person's two rows into one identity.
- Free-text mail; any change to pricing, capacity, or the queue's rules.

## Decisions

**D1 — A member row carries a fighter's facts and states a contract's as absent.**
Name, nationality, club, claimed identifier, evidence, verdict, the team and its
discipline, a number. For VS, total, outstanding, expiry, paid-at and payment
state it carries nothing — and the table already draws nothing for a row that has
none, because an imported row has none either. No new empty-cell idiom is
invented. *Alternative:* a member row inheriting its team's registration's money
— rejected outright: it would state one debt on five rows and every sum over the
column would be wrong.

**D2 — A member row's moment is its team's, with roster order breaking ties.**
The list is ordered by registration moment (`etl-console`, Order of the fencer
list); a member has no moment of its own that means anything, and using the
instant it was typed in would scatter a team across the list. Taking the team's
moment stands the team together where the team entered. *Alternative:* the
member's own `created_at` — rejected: it makes the list's order a record of
typing, which is exactly what the requirement's "no substitute moment SHALL be
invented" is protecting against.

**D3 — A member is numbered where it is born: in the roster save.** The previous
change made that save a diff, so "a member was added" is a fact the handler
already computes. Removal retires the number and a restore returns it, which is
what `rownumbers` already does for a deleted and restored row — no special case.

**D4 — Deduplication excludes member rows, and this breaks no rule.** The phase
shows candidate groups, not the fencer list (`PHASE_COLUMNS.dedup` is empty by
design), so "one and the same set of fencers" was never about it. The exclusion
is in the candidate query, stated once. *Alternative:* a second verdict — "link,
do not merge" — rejected for this change: it is a new concept with its own
surface, and nothing here needs it. It is the right door to open if matching the
same person twice becomes the complaint.

**D5 — Actions stay a function of the row; only the answer grows.**
`rowAction` gains one more case before its existing ones: a row with no
registration behind it and no source row of its own offers nothing. Deletion is
not offered either — a member row is not a row somebody typed by mistake; it is a
person on a roster, and the way to take them off it is the roster editor, which
has one home.

**D6 — The phase summaries and paid counts read contracts.** `paidCount` and the
phase summary lines count what has a payment state; a member row has none and is
not counted or totalled. Stated here because the count is what a reader checks a
list against, and a count that silently included rows that can never be paid
would read as a permanent shortfall.

**D7 — Teams moves to immediately after Fencers in the fixed order.** The order
is a constant list (`PHASES`), and the rule "a setting removes phases, it never
reorders them" is unaffected: this moves the constant, not the filtering. On an
automatic tournament, which is offered no Import phase, Teams is then the third
tab — which is how the organizer described wanting it.

**D8 — The Export band's Fencers tab follows the fencer list**, because
`etl-console` already says it "remains the fencer table in every respect". It
therefore gains member rows, whose money columns read as absent, and loses the
row of a registration that bought nothing but team entries. Per-discipline tabs
are D11's. *Risk and alternative under Risks.*

**D9 — Cancelling one team is an amendment.** The machinery exists: entering,
renaming and removing a team is already an amendment of the registration, and
`amendment.py` reprices on frozen prices and states the result. The organizer's
cancellation differs from the entrant's amendment only in who asks and in that it
speaks: money moves, so it is not the silent correction a roster edit is.

**D10 — The category is for the fighters, and a team carries no rating.** The
reversed requirement rested on a true premise — a team has no rating — and drew
the wrong conclusion from it. What the map keys is a taxonomy code, which a team
discipline derives like any other, and what a snapshot fetches is a fighter's
page. So the map simply stops refusing the code. Nothing computes a team's rating
from its members': any formula would be Squire inventing a seeding rule, and
tournaments do not agree on one. *Alternative:* a team rating as the mean or sum
of its roster — rejected, and rejected visibly in the spec, so the next reader
does not take its absence for an oversight.

**D11 — A team discipline's export tab is a list of teams with their fighters
beneath.** It numbers teams, not fighters, because the tab is read as the
discipline's field; the paid cell belongs to the team, because a team is paid for
once; and the seeding tick is not offered, per D10. Its capacity line is in teams,
as the public team roster already draws it. Roster print needs nothing: it
"typesets them exactly as the Export tab shows them". *Alternative:* a flat list
of fighters with a team column — rejected: the thing being seeded is a team, and a
flat list would hide which four numbers belong together.

## Risks / Trade-offs

- **Matching's workload grows from registrations to fighters** — eighteen rows
  become sixty-seven on a tournament like `ttt-2027` → name-assisted matching
  already proposes a profile per row (`nameranking.py`); the organizer ratifies
  rather than searches. The phase's own summary states how many rows still owe a
  verdict, so the work is visible rather than discovered.
- **A person who fights individually and on a roster is matched twice** → stated
  in the spec rather than hidden, and the second verdict is one click on a row
  whose evidence is identical. D4's door is there if it grates.
- **`base_rows` grows and does a proposal per row** → the projection is already
  rebuilt per request for every phase; sixty-seven rows is not a different order
  of magnitude from the imported batches the console already carries. Worth a
  measurement before the first large team tournament rather than an assumption.
  **Measured** (2026-11-08, task 7.3, SQLite through the test client, warm):
  `GET /sheet` over a `ttt-2027`-shaped tournament — 18 team registrations, 67
  fighters, 85 rows — ran min 62 ms, median 64 ms over five reads. So the
  fourth population costs tens of milliseconds, not a redesign; the next change
  has a number rather than an assumption. Re-read over HTTP against the running
  app once a snapshot was stored (task 7.5, 67 ratings and ranks joined onto the
  rows): 118 ms, which is the figure to compare future reads against, since a
  tournament that has taken a snapshot is the normal case.
- **Downstream consumers of the Fencers export see rows with no money** — the
  sheets export writes that table to a worksheet → acceptable and arguably
  right: a start list is what a tournament needs. If it proves wrong, the
  narrower alternative is an export tab of its own for fighters, leaving the
  Fencers tab as contracts; that is a bigger change than it sounds, because the
  two tabs would then have to be told apart by every reader.
- **A member row has no e-mail**, so anything that writes to a row's address must
  skip it → there is nothing that does so today; it becomes a real constraint
  when free-text mail is built, and that change will have to say whose address a
  fighter's row uses.
- **An organizer who had no category to configure for a team discipline now has
  one, and may not notice** → the setup checklist already states where a
  discipline will carry no ratings; a team discipline joins that statement rather
  than getting a new one. Worth a look at the checklist's wording while in there.
- **A team tab on a tournament with large rosters is a long table** — six teams of
  four is thirty rows, and the band's other tabs are one row per fencer → that is
  what the discipline's field is; the alternative of collapsing rosters would hide
  the numbers the tab exists to show.
- **Two unarchived changes touch `team-disciplines`'s teams view** → this one
  assumes the other has landed; applying them out of order would leave the
  requirement half-rewritten. Named in Context and in the first task.
