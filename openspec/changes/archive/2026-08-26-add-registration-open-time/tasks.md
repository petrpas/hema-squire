## 1. Data model and migration

- [x] 1.1 Add `registration_opens_time` (nullable `Time`) and `timezone` (non-null `String(64)`) to `Tournament` in `backend/app/models.py`, each with the comment convention the surrounding columns use, stating that an unset time means the start of the local day and that the zone governs every timeline date. Verify by importing the model and reading the mapped columns.
- [x] 1.2 Write one Alembic revision adding both columns inside `batch_alter_table` (the SQLite-compatible pattern of `a7c41e90d2b5`), backfilling `timezone = 'Europe/Prague'` on existing rows, then making it non-null with that server default. Verify `alembic upgrade head` then `alembic downgrade -1` both run clean on a copy of the dev database and that `upgrade` again leaves every existing row with a zone.
- [x] 1.3 Add `tzdata` to the backend's dependencies. Verify `python -c "from zoneinfo import ZoneInfo; ZoneInfo('Europe/Prague')"` succeeds in a container with no system zone database. *(The backend is packaged with `uv`/`pyproject.toml`; there is no `requirements.txt`, so the dependency went there.)*

## 2. Resolution and the gate

- [x] 2.1 Add `registration_opens_at(tournament) -> datetime | None` to `backend/app/setup.py` — the single place date, time and zone are folded into a UTC instant (design D1). Unset time means the start of the local day; no opens date means `None`. Verify with unit tests covering both, plus a zone ahead of UTC.
- [x] 2.2 Add the local-day helper the closing edge needs (`now` → the tournament's local date) beside it, and use it for every whole-day comparison in the registration path (design D2, D3). Verify a tournament closing on date D still accepts at 23:30 local and rejects at 00:30 local the next day.
- [x] 2.3 Change `registration_availability(tournament, today: date)` to take `now: datetime` (aware UTC), comparing the opening edge as an instant and the closing edge as a local day; follow with `amendment_availability`, whose own `amendments_close` stays a local day (design D5). Verify `test_registration_gating.py` passes with cases at one minute before, exactly at, and one minute after the opening moment.
- [x] 2.4 Update the three call sites — `routers/tournaments.py:212`, `routers/registrations.py:405`, `routers/registrations.py:614` — to pass `_now()` rather than `_now().date()`. Verify no caller of either function still passes a `date` (`grep` for `.date())` at those call sites) and the full backend suite passes.

## 3. Validation

- [x] 3.1 Add the DST resolution rules to the write path (design D4): a nonexistent local time is rejected, an ambiguous one resolves to its first occurrence. Verify with tests pinned to the Europe/Prague spring-forward and autumn-back dates using `fold`.
- [x] 3.2 Add the field-level rejections with router codes and `_ROUTER_CODE_FIELDS` entries in `backend/app/errors.py`: `opening_time_without_date` → `registration_opens_time`, `opening_time_does_not_exist` → `registration_opens_time`, `unknown_timezone` → `timezone`. Verify each returns 422 with the field named, in the shape `apiErrors()` already parses.
- [x] 3.3 Make clearing `registration_opens` clear `registration_opens_time` in the same save (design D9). Verify a PATCH nulling the date leaves both fields null and returns 200.
- [x] 3.4 Validate `timezone` against `zoneinfo.available_timezones()` on write. Verify an unknown name is rejected and a known one round-trips.

## 4. API surface

- [x] 4.1 Add `registration_opens_time` and `timezone` to the tournament setup DTOs in `backend/app/schemas.py` (the `TournamentUpdate`-side model and the detail DTO). Verify a PATCH sets them and the detail response returns them.
- [x] 4.2 Add the resolved `registration_opens_at` (offset-bearing ISO instant, or null), `timezone`, and `server_time` to `OpenTournamentOut` and the fencer detail DTO (design D6). Replace `registration_opens_on`'s role as the not-yet-open date with the resolved instant, keeping the bare date field present so an older client still works. Verify `test_open_tournaments.py` asserts the instant on a not-yet-open tournament and that `server_time` is present on every response carrying an opening moment.
- [x] 4.3 Round-trip both new fields through `backend/app/export_json.py` — add the `_parse_time` sibling to `_parse_date` and extend the field list at `export_json.py:51`. Verify `test_export_json.py` exports a tournament with an 18:00 opening and reimports it to the same opening instant.

## 5. Setup UI

- [x] 5.1 Add the opening-time input to `frontend/src/setup/TimelineSection.tsx`, beside the registration-opens date as one field pair rather than a new row in the chronological sequence (spec: setup-navigation). Verify the timeline still reads as the same sequence of dates with the tournament's own date closing it read-only.
- [x] 5.2 Add the timezone control to the same section, presented as governing the section rather than as an entry in the sequence, offering a zone list with `Europe/Prague` preselected and always including the tournament's stored zone (design D9). Verify a tournament whose stored zone is outside the list keeps it after saving the section unchanged.
- [x] 5.3 Extend the section's single `flush` to write both new fields with the rest of the timeline, and surface the three new rejection codes through the existing `applyApiErrors` path. Verify a rejected opening time marks that field and blocks the save, leaving neither field stored.
- [x] 5.4 Add the hints for both controls (design D10) and their strings to `en.json` and `cs.json`, alongside the new `validation.*` entries for the three codes. Verify no literal reaches a component and both bundles carry every new key.

## 6. Fencer-facing surfaces

- [x] 6.1 Extend the API types in `frontend/src/api.ts` with `registration_opens_time`, `timezone`, `registration_opens_at` and `server_time`. Verify `tsc` passes.
- [x] 6.2 Rewrite `registrationStatus()` in `frontend/src/TournamentFace.tsx` to compare the resolved instant against the skew-corrected now, keeping the closing edge a local-day comparison; `amendmentOpen()` follows unchanged on top of it (design D6). Verify it agrees with the backend at one minute either side of the opening moment.
- [x] 6.3 State the opening moment with its time and zone on the information header's registration-window line, and keep the date-alone rendering where no time is set (spec: fencer-home). Verify both renderings against a tournament with and without an opening time.
- [x] 6.4 Add the skew calculation — `server_time` minus the device clock, taken once per load — and share it with everything that reads "now" on the detail page. Verify a stubbed device clock several minutes fast still counts down and unlocks on the server's time.
- [x] 6.5 Build the countdown as a text figure per design D7 and the `design-system` delta: tabular numerals at fixed width, one update per second, `MM:SS` under an hour and `H:MM:SS` above, shown only inside the last 24 hours, stopping at zero and never negative, with no bar, ring, spinner, animation, or transition. Verify by inspecting the rendered element for any animated property and confirming the line does not reflow as digits change.
- [x] 6.6 Add the in-place unlock (design D8): one `setTimeout` scheduled for the corrected opening moment plus a small margin, one refetch when it fires, no polling, and re-evaluation on `visibilitychange` and window focus. Verify the waiting page issues no requests for an hour, that the moment triggers exactly one refetch, and that a backgrounded tab returned to after the moment shows registration open immediately.
- [x] 6.7 Handle a `not_yet_open` rejection of a submission by returning to the waiting state with the countdown recomputed from that response, rather than a generic error (spec: registration, fencer-home). Verify with a stubbed rejection.
- [x] 6.8 Update the Fencer Home card's opening status to read from the resolved instant so the Announced/Open tabs and the card badge agree with the detail page at the boundary. Verify a tournament opening within the hour still sits in Announced and moves to Open at its moment.

## 7. Verification

- [x] 7.1 Add the end-to-end gating test: a tournament in Europe/Prague opening at 18:00 rejects at 17:59:59 local, accepts at 18:00:00 local, and rejects at midnight UTC the same day when that falls before the opening. Verify the test fails against the pre-change gate.
- [x] 7.2 Verify the existing-tournament shift is exactly what the proposal states: a date-only tournament in Europe/Prague now opens at 00:00 local rather than 00:00 UTC — two hours *earlier* in summer, since Prague is ahead of UTC — with no stored value changed.
- [x] 7.3 Run the full backend suite and the frontend typecheck and lint; confirm no remaining caller passes a bare date to either availability function and no new hex value or animated property entered the frontend (design prohibitions, `tokens.css`).
