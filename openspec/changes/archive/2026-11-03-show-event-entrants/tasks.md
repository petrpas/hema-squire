## 1. Rosters

- [x] 1.1 In `backend/app/entrants.py`, `_event` takes the conduct's queue flag and sets `line = conduct.queue and item.capacity is not None` (design D2); update its docstring, which still says an event has no capacity
- [x] 1.2 Tests in `backend/tests/test_entrants.py`: a capped seminar on an automatic upcoming record draws the line with nothing queued, both full and part full; an uncapped seminar draws none; a held record draws none for a capped seminar

## 2. List aggregates

- [x] 2.1 In `backend/app/list_counts.py`, `seated_entrants` fills event entries from a second query over `RegistrationExtra` → `ExtraItem` in `PUBLIC_EVENT_CATEGORIES`, live, distinct by registration, dropping removed registrations; tournaments keep the discipline query (design D3); update the module and function docstrings
- [x] 2.2 In `backend/app/familiar.py`, `_ratings` leaves out a tournament with no individual discipline, so its order is by name and `ranked` false (design D4)
- [x] 2.3 Add `ProgramMeterOut` (`id`, `name`, `entered`, `capacity`) and `program_meters: list[ProgramMeterOut] = []` to `OpenTournamentOut` in `backend/app/schemas.py`
- [x] 2.4 Compute program meters for the whole list in one grouped query (events only, capped items in `PUBLIC_EVENT_CATEGORIES`, live and non-removed registrations, item-id order) and set them in `_fencer_list` / `_fencer_tournament_out` in `backend/app/routers/tournaments.py` (design D5)
- [x] 2.5 Tests in `backend/tests/test_list_aggregates.py`: an event counts seminar and program attendees once each and not afterparty-only registrations; a removed row does not count; a tournament ignores its seminar attendees and carries no meters; an event's meters cover capped seminar/program items only, in offer order, with the roster's count
- [x] 2.6 Tests in `backend/tests/test_familiar.py`: clubmates at an event's seminar are found with `ranked` false even when the event keeps a rating snapshot; a team-only tournament has no seated entrants and so never carries `familiar`, so its half of D4 is not observable and has no test

## 3. Frontend

- [x] 3.1 Add `program_meters` to the list entry type in `frontend/src/api.ts`
- [x] 3.2 Narrow `CapacityMeter`'s prop to a `Meter` shape (`name`, `entered`, `capacity`, `queue_length`) and keep discipline callers compiling (design D6)
- [x] 3.3 In `TournamentCard.tsx`, render the program meters, with `queue_length: 0`, where an event has no disciplines
- [x] 3.4 In `TournamentDetail.tsx`, offer the Entrants tab on an event when its `extra_items` include a seminar or other program item; keep the category list beside a comment naming `entrants.PUBLIC_EVENT_CATEGORIES` (design D1)
- [x] 3.5 Tests: the detail offers the tab for an event with a seminar (including an empty one) and for one with other program, and not for one with only an afterparty and goods; an event card shows `12/20` and `plno` for a capped seminar and no row for uncapped or afterparty items; a tournament card shows no item meter

## 4. Found in the eye check

- [x] 4.4 A side event's line states its capacity: `capacity` on `Roster`/`RosterOut` where the line is drawn, `CapacityLine` labels it `kapacita N` / `capacity N` (`export.line.limit`); backend and frontend tests
- [x] 4.5 An event's Tournament tab shows no empty disciplines section: `DisciplinesInfo` renders nothing without disciplines; frontend test

## 5. Checks

- [x] 5.1 `uv run ruff check .` and `uv run basedpyright` pass in `backend/`; scoped pytest over the touched test files passes
- [x] 5.2 `npm run typecheck`, `npm run check` and `npm test` pass in `frontend/`
- [x] 5.3 Run the app and check by eye an event with a capped seminar: card meter, foot counts, Entrants tab with the line; and an event with only an afterparty: no tab, no meter
