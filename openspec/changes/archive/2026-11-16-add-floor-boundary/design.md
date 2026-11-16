## Context

**Context: floor.** This change belongs to the floor, the tournament-day context. It
touches the office in three small, additive edits, listed under D6. Without them the
floor would have to rebuild what the public roster already answers.

**How the office answers "who is entered".** `backend/app` is a flat package of about
65 office modules. The office answers the question in one way:
1. `sheet.base_rows` projects registrations, imported rows, hand-entered rows and team
   member rows into one keyed table.
2. `rules.replay` applies the organizer's corrections, deletions and merges, and the
   ratings lookup.
3. `entrants.rosters()` narrows that to the public roster.

**Individual rosters.** `rosters()` reads `exporttables.table_rows` for the discipline's
tab. It keeps rows whose `registration_id` is in the live set, and splits them into
seated (`disciplines`) and queued (`substitute_for`).

**Team rosters.** `rosters()` queries `Team` directly and drops a team whose entering
registration is in `removed_registration_ids`. The export band reads the same teams
through `exporttables.team_entries`. Its `TeamEntry` carries `team_id`, `paid` and
`member_row_ids`, but not the entering registration.

**What `rosters()` returns.** Neither `EntrantRow` nor `TeamRow` carries a row id, a
registration id or a team id. They are built for public display.

**The gate on `/export/tables`.** It is `require_console_access` plus
`require_published`, both in `app.auth`. The tournament is resolved from the slug by
`routers.tournaments.get_tournament`, behind `TournamentDep`.

## Goals / Non-Goals

**Goals:**
- A package `app/floor/` with a boundary that a test enforces.
- One port, `app.floor.roster`, holding what the floor knows about entrants.
- One adapter, `app/floor/adapters/office.py`, that builds the port from the replay and
  is the only floor file that reads office modules.
- One read-only endpoint, which proves that the router mounts, the gate applies and the
  schema serializes.
- Instructions in `CLAUDE.md` and `openspec/config.yaml` that keep the boundary in place
  for later changes.

**Non-Goals:**
- Check-in, pools, brackets, scheduling, the planner.
- Any floor table or migration.
- Any frontend.
- Any change to how the office builds or stores entrants.
- Joining two persons by hand. That belongs to a later check-in change.

## Decisions

### D1. The adapter reads the replay beside `rosters()`, not through it
The adapter builds the replay the way `rosters()` does: `base_rows`, then `replay` over
`active_rules` with `rating_lookup`. It narrows with the same public building blocks:
- `exporttables.table_rows` with a discipline tab, followed by the live-registration
  filter, then `disciplines` membership for the seated rows.
- For teams, `exporttables.team_entries`, keeping the seated entries and dropping any
  whose `registration_id` is in `entrants.removed_registration_ids`.

**Alternative: call `rosters()` and map its output.** Rejected. Its rows carry no keys,
so persons and teams could only be matched by name, and names repeat. The other way to
get keys was to add them to `EntrantRow` and `TeamRow`. That meant a wider office edit,
and the public payload would carry fields only the floor needs.

**The cost:** two code paths could drift. The contract test (D7) pins them together. It
compares, per discipline, the floor roster's entrants with `rosters()`'s seated entrants
over the seeded tournament and over fixtures covering both modes, queued entrants,
corrections and a removed registration's team.

### D2. Person identity (design question 1)
**Rows of one person.** One replay row is one person. A fencer seated in several
individual disciplines is already a single row, so they are one person with several
entries.

**Joining rows across populations.** Rows from different populations are joined only on
a confirmed HEMA Ratings identity. These are a registration-backed row (`reg:`, `imp:`,
`man:`) and member rows (`mem:`), or several member rows. They are joined when all of
them carry the same `hr_id` with `match_verdict == "confirmed"`.

**The anchor.** The anchor gives the person its key, name, club and nationality. It is
the registration-backed row, or, where there is none, the member row with the lowest
member id. The registration-backed row is the one the organizer amends, and it is what
the public individual roster shows.

**Where it cannot decide, rows stay apart.** A row with no `hr_id` stays its own
person, and so does a row whose `hr_id` is only proposed. Neither is joined to anything.

Two registration-backed rows that share one confirmed `hr_id` are also left apart, and
so is every member row carrying that `hr_id`. Two registrations of one human are a
duplicate the office's dedup resolves. If the floor joined them, the person could hold
two entries in one discipline, and the duplicate would be hidden from the organizer.

Nothing is joined by name.

**Alternatives considered:**
- **Never join.** Rejected: the planner could not see that one human fences in an
  individual and a team event.
- **Key a joined person as `hr:<id>`.** Rejected: an organizer's correction of the
  identifier would rename the person.
- **Use the dedup result.** Not available: dedup does not look at member rows
  (`dedup.py` selects `imp:` and `man:` only), and `TeamMember` identity is local to its
  roster by design (team-disciplines D4).

The owner decided this rule on 2026-11-16.

### D3. The person key is the anchor's replay row id (design question 2)
Every seated individual row stands for a live registration. Its id is one of these:
- `reg:<registration id>`;
- the `source_row_id` frozen into the registration when it was issued (`imp:<fp>` or
  `man:<id>`). `uq_registrations_tournament_id_source_row_id` keeps it unique.

An imported row is never renamed. A corrected upload brings a new `ImportedRow` with a
new key, and the issued one keeps its own. `mem:<member id>` survives every save of the
roster (`TeamMember`, roster-identity-and-history D1).

So the row id is stable enough to be stored on floor tables later. Two things make a
key disappear:
- A cancelled registration drops out of the live set.
- Clearing the tournament's imported content (`importclear`) deletes issued
  registrations together with their rows.

Floor tables written later must read a missing key as "this entrant left". They must
not read it as an error.

A joined person's key can change from `mem:<id>` to the registration row's id if that
registration is entered later. Floor storage, when it comes, records per entry rather
than per person, which keeps that change contained. The note stands here so that the
first storing change addresses it.

### D4. Paid is the settled fact
An individual entry is paid when `row["paid"]` is true, which is the registration's
settled state as the replay states it. A team is paid when `TeamEntry.paid` is true,
which is its entering registration's settled state.

This is not the public Paid cell. The public cell is empty where nothing is yet owed or
where the account was deleted, because it is a claim made to the public. The floor
needs the fact the organizer acts on. The owner decided this on 2026-11-16.

### D5. The port's shape
`app/floor/roster.py` imports nothing from `app`. It holds frozen dataclasses with
tuples, not lists:
- `FloorDiscipline(slug, name, kind)`. `kind` is `"individual"` or `"team"`.
- `Person(key, name, club, nationality, hr_id)`.
- `IndividualEntry(person, discipline, rating, rank, paid)`. `rating` and `rank` are
  `None` where the replay states none.
- `TeamEntry(key, discipline, name, members, paid)`. `key` is `team:<team id>`, the id
  the export band already uses for a team row. `members` is a tuple of person keys in
  roster order.
- `Roster(disciplines, persons, individuals, teams)`.

The disciplines are stated because an empty discipline would otherwise be invisible.
Side events are left out: nothing is fenced at them.

The port's `TeamEntry` and `exporttables.TeamEntry` share a name. The port never
imports the office one, and the adapter imports the office module as `exporttables`,
never the class by name.

### D6. Boundary crossings and office edits
The design rule asks for every import that crosses the floor boundary to be listed.
Here they are.

**`app/floor/adapters/office.py`** imports:
- `app.sheet` (`base_rows`, `rating_lookup`);
- `app.rules` (`replay`, `active_rules`);
- `app.exporttables` (`table_rows`, `team_entries`, `Tab`, `DISCIPLINE`);
- `app.entrants` (`live_registration_ids`, `removed_registration_ids`);
- `app.models` (`Tournament`, `DisciplineKind`);
- `app.routers.tournaments` (`SessionDep`, `FencerDep`, `TournamentDep`). These are
  re-exported for `api.py`.

**`app/floor/api.py`** imports:
- `app.auth` (`require_console_access`, `require_published`). This is the gate itself.
- `app.floor.adapters.office` (the dependencies, and the function that builds the
  roster).

Rule 1 allows both.

**The access gate lives in `app.auth`, which is on the allow-list.** No module is added
to the list.

The slug-to-tournament lookup lives in `routers.tournaments`. It reaches `api.py` only
through the adapter, which re-exports `TournamentDep` and the other dependencies.

**Alternative: have `api.py` resolve the tournament itself.** Rejected. That would need
`app.models` in `api.py`, and would put a second copy of the lookup in the repo.

**`app/main.py`** imports `app.floor.api` to mount the router. This is the one
exception to rule 2.

**Office edits:**
- `entrants._live_registration_ids` → `live_registration_ids`. This is a rename of a
  private helper the adapter needs for the same answer. `rosters()` is updated as its
  caller. The brief allows it.
- `exporttables.TeamEntry` gains `registration_id: int`, filled in `team_entries` from
  `team.registration_id`. **This edit is outside the brief's allow-list. The owner
  approved it on 2026-11-16.** Without it, the adapter could only drop a removed
  registration's team by querying `Team`, which the boundary forbids. Every existing
  reader of `TeamEntry` ignores the new field.
- `app/main.py`: one `include_router`.

### D7. Tests
`tests/floor/` is the suite's first subdirectory. The suite has no `__init__.py` files,
so every basename there starts with `test_floor_` to stay unique.

`conftest.py` lives at `tests/`, so its fixtures and the Hypothesis profile reach the
subdirectory unchanged. `contract_seed` is imported as `tests.contract_seed`, as the
contract suite does now.

- **`test_floor_boundary.py`.** The checker is `violations(paths, root) -> list[str]`,
  built on `ast`. It resolves relative imports against the file's package. It treats
  `from app import x` as an import of `app.x`. One test runs it over the real tree and
  expects no violations. Others feed it synthetic files in `tmp_path` that break each
  of the four rules, including in the relative and `from app import x` forms, and
  expect each to be reported.
- **`test_floor_roster.py`.** Builds the floor roster and `rosters()` over:
  - the `contract_seed` tournament;
  - fixtures for organizer-kept mode, queued entrants, a correction, an unpaid seated
    entrant, a cross-population person, a proposed `hr_id`, two registrations sharing
    one `hr_id`, and a removed registration's team.

  It asserts per discipline that the entrants are equal, matched by name and club (the
  public roster carries no key), with multiplicity. A write-nothing check compares the
  rule, registration and row-number counts before and after.
- **`test_floor_api.py`.** Covers 200 for an organizer, 403 for a stranger, 404 for an
  unknown slug and 409 for a draft.

The schemathesis contract suite picks up the new endpoint through the existing seed.

## Risks / Trade-offs

- **[Two code paths: the adapter and `rosters()`.]** → The equality test (D7) runs over
  the seeded tournament and over every case the spec names. A change to `rosters()`
  that the adapter does not follow fails it.
- **[A joined person's key may change when a registration appears later (D3).]** →
  Nothing is stored yet. The first floor storage change has to address it.
- **[The adapter re-exports office dependencies (`TournamentDep`), so office types flow
  into `api.py`.]** → The imports go through the one door the checker permits. `api.py`
  never names `app.models`.
- **[`tests/floor/` is the first test subdirectory.]** → The `test_floor_` prefixes
  avoid basename clashes under rootdir-based collection. `pytest tests/floor -q` is
  run alone as an acceptance step.
- **[Building the replay per request is not cheap.]** → It is the same cost as the
  existing `/export/tables`, and the endpoint is console-only.
