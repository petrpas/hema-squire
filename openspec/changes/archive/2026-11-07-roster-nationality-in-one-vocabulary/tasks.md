## 1. The reading on the write path

- [x] 1.1 Apply `hr_index.country_code(x) or x` to the member's nationality in `update_roster` (`app/routers/registrations.py`) and verify a roster saved with `Czech Republic` stores `CZ`
- [x] 1.2 Apply the same reading in the restore (`app/export_json.py`) and verify a document carrying `Czech Republic` restores to `CZ` while the export of those rows states what they hold
- [x] 1.3 Verify an unresolvable spelling survives both paths unchanged, and that `None` stays `None`

## 2. Existing rows

- [x] 2.1 Add the data-only Alembic revision over `team_members.nationality` (design D3) and verify `alembic upgrade head` converts a row holding `Poland` to `PL` and leaves an unresolvable one alone
- [x] 2.2 Verify `alembic downgrade -1` then `upgrade head` runs clean on a database holding both kinds of row

## 3. What must not change

- [x] 3.1 Verify the canonical JSON export still states the stored value and that an export/import round-trip over a tournament with teams reproduces the same member rows (`tests` for `export_json`)
- [x] 3.2 Verify `/api/hr/search` and its nationality filter are untouched — the index keeps the fighters page's own spelling
- [x] 3.3 Update the team and entrants tests that assert a spelled-out country, and verify `pytest tests -k "team or entrant or export_json" -q` is green

## 4. Gates

- [x] 4.1 Run `uv run ruff check .` and `uv run basedpyright` clean from `backend/`
- [x] 4.2 Confirm on the local TTT tournament that the Teams tab, the organizer's teams view and the public roster all read `CZ`, `SK`, `PL`, `HU`, `DE`, `HR`
