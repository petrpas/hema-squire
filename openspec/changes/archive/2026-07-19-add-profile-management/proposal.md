## Why

After login the account has no home: the tournament picker mixes the tournament list with an organizer plea, and a logged-in user cannot see who they are, what role they hold, or manage their HEMA Ratings binding. Profile data (email, name) and the HR find-and-match flow that fencer-accounts already specifies have no UI surface.

## What Changes

- New **Profile page**, reachable by every logged-in user, showing:
  - **Account section**: email and full (display) name, editable.
  - **Role section**: the account's effective role (Fencer / Organizer / Admin / Owner); for plain Fencers it embeds the existing organizer-plea flow (request button, pending/denied status).
  - **HEMA Ratings section**: HRID, HR name, club, nationality when bound, with a link to the hemaratings.com profile; when unbound, a find-and-match flow — nationality select narrows the search space, then name search ranked by text similarity, candidates shown with HRID/name/club/nationality, confirm to bind (write-once, per fencer-accounts).
- New shared **account menu** ("⋯") in the top-right of every logged-in page: My Profile, Admin Panel (Admin/Owner only), To Fencer (placeholder until the fencers landing page exists), To Organizer (tournament picker), Logout.
- Tournament picker stays as-is for now (including its plea section); it will be replaced when the fencers landing page lands.
- HR search endpoint gains an optional nationality filter and similarity-ranked name results.
- Seed/bootstrap: create the account **petr.pascenko@gmail.com** (Petr Paščenko) with role Organizer and password `swordismylife`; dev.sh sets `HEMA_SQUIRE_OWNER_EMAIL=petr.pascenko@gmail.com` so the account is also the deployment Owner (Fencer capabilities are inherent per the role ladder).

## Capabilities

### New Capabilities
- `profile-page`: the logged-in profile surface — account info editing, role display with organizer plea entry point, HR binding display and find-and-match UI, and the shared top-right account menu.

### Modified Capabilities
- `hr-integration`: fighters-index search gains a nationality-filtered, similarity-ranked search mode (nationality narrows the space, name matches ranked by text similarity) serving the profile find-and-match flow.

### Unchanged (used, not modified)
- `fencer-accounts`: binding rules (write-once from fencer side, one account per hr_id, audit) already cover the profile page's behavior; the page is a new surface over the existing `/api/account` contract.
- `user-roles`: role ladder, Owner-from-config, and plea workflow are unchanged; the profile page only displays and reuses them.

## Impact

- **Backend**: `routers/accounts.py` (account update already exists; expose role/HR data as needed), `hr_index.py` + `routers/accounts.py` `/api/hr/search` (nationality filter + similarity ranking, list of nationalities), seed script (`scripts/seed_demo.py` or a dedicated bootstrap) for the Petr account.
- **Frontend**: new `ProfilePage.tsx`, new shared `AccountMenu` header component mounted on TournamentPicker, Console, AdminPanel; `App.tsx` routing state; i18n keys (cs/en).
- **Config/dev**: `dev.sh` exports `HEMA_SQUIRE_OWNER_EMAIL`.
- **No breaking changes**; existing endpoints keep their contracts.
