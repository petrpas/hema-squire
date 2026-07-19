## 1. Backend — search and bootstrap

- [x] 1.1 Extend `hr_index.py` search with optional nationality filter and similarity ranking (fold + `difflib` ratio with substring bonus, top 20; token-substring prefilter when no nationality), keeping the `HRIndex` protocol and `StubHRIndex` in sync
- [x] 1.2 Add `GET /api/hr/nationalities` (distinct non-empty nationalities from `hr_fighters`, sorted) and a `nationality` query param on `GET /api/hr/search` in `routers/accounts.py`
- [x] 1.3 Backend tests: nationality narrows candidates, similarity ordering ("pascenko" finds Paščenko first), no-nationality path still works, nationalities endpoint
- [x] 1.4 Add idempotent `scripts/seed_owner.py` (upsert petr.pascenko@gmail.com / "Petr Paščenko" / role organizer / scrypt hash of `swordismylife`); wire into `dev.sh` and default `HEMA_SQUIRE_OWNER_EMAIL=petr.pascenko@gmail.com` there (overridable)

## 2. Frontend — shared navigation

- [x] 2.1 Refactor `App.tsx` to a `view` union (`picker | console | admin | profile`) with navigation callbacks; add `api.ts` functions for nationalities and nationality-filtered search
- [x] 2.2 Create `AccountMenu` component ("⋯" top-right: My Profile, Admin Panel for admin/owner, To Fencer disabled placeholder, To Organizer, Logout) and mount it on TournamentPicker, Console, AdminPanel, ProfilePage; remove now-redundant standalone logout/admin buttons except the picker's plea section
- [x] 2.3 Extract `PleaSection` from `TournamentPicker.tsx` into a shared component (picker behavior unchanged)

## 3. Frontend — profile page

- [x] 3.1 Create `ProfilePage.tsx` with account section: show and edit email + full name via `PATCH /api/account`, with save/error states
- [x] 3.2 Role section: effective role label (Owner when `is_deployment_owner`, else role); embed shared `PleaSection` for plain Fencers only
- [x] 3.3 HR section, bound state: HRID, name, club, nationality and link to `https://hemaratings.com/fighters/details/{hr_id}/`; no rebind controls
- [x] 3.4 HR section, find-and-match: nationality select (from `/api/hr/nationalities`), name search, ranked candidate list with HRID/name/club/nationality, confirm → `POST /api/account/hr-binding`; surface already-bound conflict
- [x] 3.5 Add cs/en i18n keys for the menu and all profile sections; style per existing `index.css` patterns

## 4. Verification

- [x] 4.1 Frontend build + backend test suite pass
- [x] 4.2 End-to-end pass via `dev.sh`: log in as petr.pascenko@gmail.com, verify Owner role shown, edit name, bind an HR profile via nationality+name search, check the hemaratings link, menu navigation from picker/console/admin
