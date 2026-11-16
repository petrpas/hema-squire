## 1. Roster facts

- [ ] 1.1 `app/floor/roster.py`: `FloorDiscipline.id`, plus `Roster.date` and `Roster.timezone`. Fill them in `adapters/office.py`.
- [ ] 1.2 `adapters/office.py`: replace `_anchors`' confirmed-identifier join with `app.list_counts.same_person` (D8). Never join two registration-backed rows or two members of one team.
- [ ] 1.3 `tests/floor/test_floor_roster.py`: rewrite the identity tests to the modified requirement's scenarios, and add one asserting the floor and the public list count the same people for one tournament.
- [ ] 1.2 Add tests: a slug edit before anyone enters keeps the id, and the date and timezone are stated.

## 2. Floor tables

- [ ] 2.1 `app/floor/models.py`: the seven tables of design D3, with string foreign keys only.
- [ ] 2.2 Register `app.floor.models` in `alembic/env.py`. Add migration `floor_0001`.
- [ ] 2.3 `app/tournament_delete.py`: delete `floor_` tables by metadata (D4). Extend `tests/test_tournament_delete.py` with a floor row per table.
- [ ] 2.4 `app/account_deletion.py`: classify the floor columns. The classification test passes.

## 3. Setup service and API

- [ ] 3.1 `app/floor/setup.py`:
  - days, pistes, formats, officials and parameters, each read with its defaults and
    saved with field-level validation;
  - parameters through a typed dataclass.
- [ ] 3.2 `app/floor/api.py`: `GET/PUT /floor/setup/{days,pistes,formats,officials,params}` and `GET /floor/summary` (tab badges, published-plan flag), all behind the console gate. Refuse discipline-less events with 404.
- [ ] 3.3 `tests/floor/test_floor_setup.py`: one test per `floor-setup` scenario.
- [ ] 3.4 `tests/floor/test_floor_console_api.py`: the gate, the event 404 and the summary badges.

## 4. Frontend

- [ ] 4.1 `routes.ts`: `floorPath(slug, phase?)`. Add the two routes in `App.tsx`.
- [ ] 4.2 `frontend/src/floor/FloorConsole.tsx` and `FloorTabBar`: eight tabs, the default tab, badges, and placeholders for the unimplemented tabs.
- [ ] 4.3 `frontend/src/floor/setup/`: one section per file, with save, drafts and leave confirmation as office Setup has them.
- [ ] 4.4 `frontend/src/floor/data/DataTab.tsx`: the live roster per discipline, and the link to office Import for organizer-kept tournaments.
- [ ] 4.5 The schedule panel slot: beside the work on a wide screen, the last tab "Rozvrh" on a narrow one.
- [ ] 4.6 The office console header link "Den turnaje".
- [ ] 4.7 Add tests for the tab order, the default tab, the badge rendering and the narrow-screen tab. Add the i18n strings in both bundled languages.

## 5. Acceptance

- [ ] 5.1 `pytest tests/floor -q` passes, and so do `tests/test_tournament_delete.py` and `tests/test_account_deletion.py`.
- [ ] 5.2 `uv run ruff check .` and `uv run basedpyright` pass. The boundary test passes.
- [ ] 5.3 `npm run typecheck`, `npm run check` and `npm test` pass.
- [ ] 5.4 `openspec validate add-floor-console --strict` passes.
