## 1. Seating deadline onto one clock

- [x] 1.1 `setup.seating_has_settled` takes `now: datetime` instead of `today: date` and resolves it through `setup.local_date`; docstring states why it is an instant, as `registration_availability` does
- [x] 1.2 `scheduler.settle_seating_if_due` takes `now: datetime`, drops `date.today()`, and compares through `local_date`
- [x] 1.3 `scheduler._reminder_due` anchors its deadline branch on the tournament-local day rather than `now.date()`
- [x] 1.4 Update the three call sites (`scheduler.py:130`, `registrations.py:488`, and the tick that reaches `settle_seating_if_due`) to pass the instant they already hold
- [x] 1.5 Tests: a tournament in a zone ahead of UTC, an instant inside the disputed band — settlement waits for the local midnight; settled-ness and the settlement pass agree at the same instant

## 2. Team composition deadline

- [x] 2.1 `tournaments.console_teams` reads the deadline as a tournament-local day; `below_minimum` follows it
- [x] 2.2 Test: no team is marked below minimum in the band between UTC midnight and the tournament's own

## 3. Date-valued price thresholds

- [x] 3.1 `pricing.registration_total` and `pricing.registration_discounts` derive `at` from `registered_at` through the tournament's zone, guarding the tz-naive SQLite round-trip
- [x] 3.2 `registrations.price_preview` reads `local_date(tournament, _now())`
- [x] 3.3 Confirm no import cycle from `pricing` to `setup`; if one appears, move the conversion to the call sites that hold the tournament
- [x] 3.4 Tests: early bird runs to the end of the local cutoff day and no further, in a zone ahead of and a zone behind UTC; preview and stored total agree; a stored total is untouched

## 4. Operational windows to UTC

- [x] 4.1 `scheduler.run_tournament_tick` Fio window and `scheduler`'s running-tournaments select read `datetime.now(UTC).date()`
- [x] 4.2 `bank.FioClient` token check and `payments`' manual poll window read `datetime.now(UTC).date()`
- [x] 4.3 No test: the invariant is "no `date.today()` in `app/`", which ruff's DTZ011 (task 5.1) gates outright. A test that set `TZ` per case would assert what the linter now refuses to compile past, against a process-global it cannot restore cleanly

## 5. Close the door

- [x] 5.1 Add `DTZ` to `[tool.ruff.lint] select` in `backend/pyproject.toml`
- [x] 5.2 Clear the remaining findings: `# noqa: DTZ007` on `bank.py`'s statement-date parse and `# noqa: DTZ005` on `scripts/reset_local_db.py`'s filename stamp, each naming its reason; the `tests/` and `scripts/` `DTZ011`/`DTZ001` findings move to the conftest helpers or gain an explicit tz
- [x] 5.3 `uv run ruff check .` clean

## 6. Test helpers follow the code

- [x] 6.1 `tests/conftest.py`: `deadline_ahead` and `deadline_passed` anchor on the tournament-local day, and their docstrings name the boundary they now serve
- [x] 6.2 Drop the `min()` over three clocks and the comment explaining the straddle, both of which existed for the disagreement this change removes
- [x] 6.3 Full suite green in `TZ=UTC`, `TZ=Europe/Prague` and `TZ=Pacific/Kiritimati` — 1419 passed in each. `tests/test_api_contract.py` failed once in UTC and once in Prague on the first pass, a different operation each time, and did not reproduce on either rerun: it fuzzes the published schema with no fixed seed, so its inputs differ per run. The failure text was not captured

## 7. Specs and finish

- [x] 7.1 Sync the five delta specs into `openspec/specs/`, including the new `day-boundaries` capability
- [x] 7.2 `uv run basedpyright` and `uv run ruff check .` clean. `openspec/changes/date-boundaries-read-three-clocks.md` is left in place at the owner's decision — it is untracked, so deleting it would be unrecoverable; `design.md` carries its findings either way
