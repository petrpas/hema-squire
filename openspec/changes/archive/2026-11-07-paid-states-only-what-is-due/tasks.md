## 1. The predicate

- [x] 1.1 State the due question in `app/entrants.py` — a running payment window, or `setup.seating_has_settled` (design D1) — and verify it through the roster across the four modes (immediate, deposit before and after the deposit, reservation, items-only) before and after the deadline
- [x] 1.2 Resolve "now" once in `entrants.rosters` and give `_conduct` the seating-settled field (design D2, D4), reading each registration's window off `expires_at` — which the replayed rows already carry — so the page issues no new query

## 2. The cell and the fade

- [x] 2.1 Give `_paid` its third input and the three-branch answer (design D3), and verify by the existing `test_entrants.py` cases for a collecting tournament with a running window (still no + faded) and a non-collecting one (still empty, never faded)
- [x] 2.2 Pass the predicate through `_individual`, `_teams` and `_event` and verify each builder's rows against the spec's scenarios — in particular that a side event's items-only row reads no while a reservation-mode seat on the same tournament reads empty

## 3. Spec scenarios as tests

- [x] 3.1 Add `test_entrants.py` cases for "Nothing is claimed before the seating deadline" and "The seating deadline is when the roster may say no" — sixteen seated, three paid early — and verify the thirteen go from empty/unfaded to no/faded as the deadline passes
- [x] 3.2 Add the deposit-mode case ("A deposit paid is paid enough to carry no mark") and the team case ("A seated team owing nothing yet carries no mark"), and verify both read empty and unfaded
- [x] 3.3 Verify the untouched rules still hold: queued rows and waitlisted teams state nothing, ordering stays paid-first, and an organizer's early seating close (`seating_settled_at`) switches the claim on as the deadline would

## 4. Gates

- [x] 4.1 Run `pytest tests/test_entrants.py -q` green, then the payments and registration scopes for anything that read `_paid`
- [x] 4.2 Run `uv run ruff check .` and `uv run basedpyright` clean from `backend/`
