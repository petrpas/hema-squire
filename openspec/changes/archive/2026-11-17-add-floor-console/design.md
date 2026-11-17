## Context

**Context: floor.** `add-floor-boundary` left `app/floor/` with three pieces: the roster
port, the office adapter, and one endpoint. Nothing in the floor is stored yet.

**Source documents.** Two owner documents of 2026-11-16 describe the tournament day:
- "HEMA Squire: formalizace plánovače turnaje": facts, decisions, parameters, outputs.
- "HEMA Squire: UX konzole pro den turnaje": a second console, eight tabs, a
  discipline × step matrix, gates.

**The seven changes.** This change is the first of seven, which together implement both
documents:
1. `add-floor-console`
2. `add-floor-planner`
3. `add-floor-checkin`
4. `add-floor-pools`
5. `add-floor-bracket`
6. `add-floor-officials`
7. `add-floor-results`

Each later change fills one or more tabs that this change sets up.

**Owner decisions of 2026-11-16 that bind this change:**
- Entrants come from the office only, through the roster port. Keep the port open for a
  second adapter later.
- Check-in state lives only in the floor.
- The engine is standard library only.
- Pistes are scored through a keyed link.
- Pool scoring is adopted from `hema-agent`.
- Team disciplines have individual pools and a team elimination.
- The advancing count is always set, and defaults to all.

## Goals / Non-Goals

**Goals:**
- The floor console shell: address, eight tabs, badges, the schedule panel slot.
- Floor Setup: days, pistes, formats, officials, parameters. Stored, validated, and
  given defaults.
- The Data tab over the live floor roster.
- The first floor tables, so that deleting a tournament and deleting an account keep
  working.

**Non-Goals:**
- Planning, check-in, pools, brackets, officials assignment, results. Each is its own
  change.
- A floor-own import of entrants.
- Any change to the office console beyond one header link.

## Decisions

### D1. A second console, not more phases
The office console's phase list (`Console.tsx`, `PHASES`) stays as it is. The floor is
its own route family under `/organizer/:slug/floor/:phase`. The office console has nine
phases and the floor has eight steps, and seventeen tabs in one band could not be read.

The two consoles still share rules carried over from `setup-navigation`:
- the fixed order;
- one field, one editor;
- badges that mean "waiting";
- a preview-style panel that becomes the last tab on a narrow screen.

**Alternative:** append the floor's steps to the office band. Rejected for the reason
above. It would also make the office mode switches (`offeredPhases`) decide floor tabs.

### D2. Floor tables refer to office rows by id, through string foreign keys
`app/floor/models.py` subclasses `app.db.Base` (allowed: `app.db`). A floor table's
reference to an office table is a string foreign key, for example
`ForeignKey("tournaments.id")` or `ForeignKey("disciplines.id")`. That needs no import
of `app.models`.

**Why the discipline id.** A slug can still be edited until a registration references
the discipline, and a format saved before then must survive that edit. The adapter
already reads `Discipline` objects, so adding `id` to `FloorDiscipline` costs one field.

**Persons.** A person is referred to by the roster's opaque key string (`reg:12`,
`mem:40`). There is no foreign key, because a key names a replay row, not a table row.
So nothing in the floor parses a key's prefix. A second roster adapter can then issue
keys of its own (owner decision: keep the port open).

**Alternative:** refer to a discipline by its slug. Rejected because of the edit window
described above.

### D3. Tables of this change
| Table | Holds |
|---|---|
| `floor_days` | `tournament_id`, `date`, `start`, `end`, `breaks` (JSON list of `[start, end]`) |
| `floor_pistes` | `tournament_id`, `name`, `ordinal`, `reserve`, `tag` |
| `floor_piste_days` | `piste_id`, `day_id`: availability |
| `floor_formats` | `tournament_id`, `discipline_id` (unique), `pool_min`, `pool_max`, `advance` (int or NULL = all), `third_place`, `staffing` (JSON role → count), `slot_pool_bout`, `slot_elim_bout`, `slot_pool_overhead`, `slot_team_match` |
| `floor_officials` | `tournament_id`, `name`, `person_key` (nullable), `roles` (JSON list), `discipline_ids` (JSON list) |
| `floor_official_days` | `official_id`, `day_id` |
| `floor_settings` | `tournament_id` (unique), `params` (JSON, keyed by parameter name) |

**Advancing "all".** "All" is stored as NULL in `advance`. That is the one meaning
NULL has there: a saved format always states its advancing count.

**Parameters.** They are stored as one JSON document. The parameter set will grow
change by change. The service reads it through a typed dataclass with the defaults in
code, so an absent key reads as its default.

### D4. Office edits, and why each one is needed
- **`app/tournament_delete.py`.** It names every child table explicitly, and its
  metadata test fails on a new table that refers to a tournament.

  The office cannot import `app.floor` (boundary rule 2). So `tournament_delete` deletes
  every `Base.metadata` table whose name starts with `floor_`. It goes in reverse
  dependency order (`sorted_tables` reversed), filtered by `tournament_id` where the
  table has one, and through its parent's id otherwise.

  The existing metadata test then covers floor tables without naming them.
- **`app/account_deletion.py`.** `COLUMN_HANDLING` classifies every column by name. It
  gains strings for the floor columns:
  - `floor_officials.name`: `("kept", "another person, entered by the organizer")`, as
    `team_members.name` is;
  - `floor_officials.person_key`: `("none", "a roster key")`;
  - the rest: `("none", ...)`.
- **`alembic/env.py`.** Registers `app.floor.models` beside `app.models`. `alembic/` is
  outside the boundary checker's scope (it checks `app/`), and the checker is not
  changed.
- **The office console header.** Its "Turnaj" stage, until now a disabled placeholder
  beside "Před turnajem", becomes a link to `floorPath(slug)`. The floor console draws
  the same header with "Turnaj" current and "Před turnajem" leading back. This is a
  frontend edit, and the import boundary governs only the backend.
- **A discipline's deletion.** `floor_formats.discipline_id` is `ON DELETE CASCADE`
  (SQLite runs with `foreign_keys=ON`). So the office's discipline delete takes the
  format along, with no knowledge of the floor.

### D5. Imports that cross the floor boundary
**New in this change:**
- `app/floor/models.py`: `app.db` (`Base`). Allowed.
- `app/floor/setup.py`: `app.floor.models`, `app.floor.roster`, `app.errors`. Allowed.
- `adapters/office.py` adds `app.list_counts.same_person` (D8).
- `app/floor/api.py`: as before. Its new handlers call `app.floor.setup` and the adapter.
- `app/floor/adapters/office.py`: adds `Tournament.date` and `Tournament.timezone`, and
  `Discipline.id`, through objects it already reads. No new module.

**Unchanged:** nothing outside `app.floor` imports it except `main.py`.

### D6. The default tab, badges and the schedule panel
**The default tab.** It is decided on the client. The floor setup endpoint returns
whether a published plan exists. In this change the answer is always "no", until
`floor-plan` exists.

**Badges.** A badge is computed by the backend per tab and returned with the setup
summary (`GET /floor/summary`). Each later change adds its own conditions to that
summary. A client restating the conditions would drift from the server, as `entrants`
D4 already argues.

**Updates.** There is no polling in this change. Setup is edited by one person. Live
refresh arrives with `today`.

### D7. Frontend structure
- `frontend/src/floor/FloorConsole.tsx` is the thin orchestrator.
- Each tab gets its own directory: `floor/setup/` (one file per section: `DaysSection`,
  `PistesSection`, `FormatsSection`, `OfficialsSection`, `ParametersSection`),
  `floor/data/`, and placeholders for the rest.
- `FloorTabBar` reuses the office tab bar's component if it accepts a tab list.
  Otherwise it is a sibling built the same way.

The design rules in `CLAUDE.md` apply in full:
- no spinners while loading;
- no colour beyond `--stamp` for a badge;
- Title Case only where the tab labels need an initial capital.

### D8. Team members are joined by the office's rule
`add-floor-boundary` joined rows only by a confirmed HEMA Ratings identifier, and
merged nobody by name. The public tournament list already counts people by a looser
rule: the same identifier, or equal folded names where either has none
(`app.list_counts.same_person`). The office and the floor could therefore count one
tournament differently. The owner chose the office's rule (2026-11-16).

The adapter imports `same_person` rather than restating it, so the two cannot drift.
It is an office module read through `adapters/office.py` only, which the boundary
allows.

**The floor's two additions.** Two registration-backed rows are never joined, as the
office never joins them either. Two members of one team are never joined, which the
office count has no need for but a lineup does.

**Which identifier counts.** The identifier a row's own record stores: a confirmed match.
A matcher's proposal is not stored, and the office's count does not read it either. A
member joins the first person, in anchor order, whose every row it is the same person
as, so no person ends up holding two different identifiers.

**Keys.** A name edit on a member row can now change a join, and with it which key a
member row resolves to. The anchor rule keeps a registration-backed person's key
stable. Only a member-only person can change key, and only through such an edit.

## Risks / Trade-offs

- **[Metadata-driven deletion of `floor_` tables could delete in the wrong order once
  floor tables refer to each other.]** → It uses `sorted_tables` reversed. The existing
  metadata test builds a tournament with every table populated. It is extended with a
  floor row per table, so a wrong order fails the test.
- **[The parameters JSON can drift from the dataclass.]** → Unknown keys are refused on
  save. Absent keys read as defaults. A test covers both.
- **[Eight tabs, most empty for months.]** → Each one states that it is not available
  yet, rather than being hidden. A later change then does not move the band.

## Open Questions

None left. Resolved 2026-11-16:
- **Staffing** has no default and is stated per discipline (one referee alone, a
  referee with judges, …).
- **Slot lengths** are parameters. 4 / 6 / 5 / 25 minutes are only starting values.
- **Identity** follows the office's public rule (D8).
