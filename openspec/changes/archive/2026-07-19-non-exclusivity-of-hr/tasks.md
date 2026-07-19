## 1. Backend — drop exclusivity

- [x] 1.1 Remove `unique=True` from `Fencer.hr_id` (add a plain index); alembic migration batch-recreating `fencers` without the unnamed unique constraint (SQLite-safe `copy_from`), plus the non-unique index
- [x] 1.2 Delete the `hr_id_already_bound` 409 checks from `signup` (routers/auth.py) and `bind_hr_later` (routers/accounts.py)
- [x] 1.3 Add `claimed: bool` to the `HRProfile` search schema, filled from existing account bindings in `/api/hr/search` results; add `hr_shared: bool` to `AdminAccountOut`, computed by a grouped query in the admin accounts listing
- [x] 1.4 Backend tests: signup and Profile bind succeed on an already-claimed hr_id; search marks claimed profiles; admin listing flags both sharers; write-once fencer rebinding still rejected; admin unbind still works

## 2. Frontend — warn, don't block

- [x] 2.1 `HRSearchPicker`: render the "already claimed by another account" notice on claimed candidates; signup window repeats the notice next to a confirmed claimed profile
- [x] 2.2 Remove the `hr_id_already_bound` error mappings (Login.tsx `signup.errors.hrBound`, ProfilePage `profile.hr.conflict`) and their i18n keys; add cs/en keys for the claimed notice
- [x] 2.3 Admin panel accounts table: warning badge on rows with `hr_shared`

## 3. Verification

- [x] 3.1 Frontend build + full backend test suite pass
- [x] 3.2 E2E via dev servers: search shows the claimed mark on a bound profile; second account claims it anyway (signup and Profile paths); admin accounts list flags both; unbind clears the flag
