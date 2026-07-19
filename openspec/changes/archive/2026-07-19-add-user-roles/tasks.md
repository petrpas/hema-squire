# Tasks: add-user-roles

## 1. Data model and migration

- [x] 1.1 Add `Fencer.role` (str enum fencer/organizer/admin, default fencer), `Tournament.owner_id` (nullable FK) and `Tournament.cancelled_at`, and the `OrganizerRequest` model (fencer_id, message, state pending/granted/denied, created_at, decided_at, decided_by) to `models.py`
- [x] 1.2 Alembic migration: new columns and table, backfill each tournament's owner from its earliest `TournamentOrganizer` row; verify upgrade/downgrade/upgrade on a scratch DB
- [x] 1.3 Add `owner_email` to config settings (`HEMA_SQUIRE_OWNER_EMAIL`); log a startup warning when no account matches

## 2. Authorization core

- [x] 2.1 Rework `auth.py`: `is_owner(fencer)` (config email match), rank helpers, `require_role(min_role)`, `require_console_access(session, tournament, fencer)` (tournament owner OR team member) replacing `require_organizer`, and `require_tournament_owner`
- [x] 2.2 Gate tournament creation behind the Organizer role; creator recorded as `owner_id` (no duplicate team row); update all console endpoints to `require_console_access`
- [x] 2.3 Tests: role ladder capabilities, owner-from-config (incl. account created after deployment), creation gate, console access for owner/team/stranger

## 3. Team, transfer, lifecycle

- [x] 3.1 Team endpoints under `/api/tournaments/{slug}/team`: list, add by email (any account, 404 unknown email, 409 duplicate), remove — owner only
- [x] 3.2 Ownership transfer endpoint: owner transfers to a team member (previous owner joins team); admin fallback endpoint to assign/reassign any tournament's owner
- [x] 3.3 Delete/cancel endpoints: hard delete only with zero registrations (409 with cancel hint otherwise, cascade config rows); cancel sets `cancelled_at`; cancelled tournaments hidden from the public tournament list and rejected by the registration gate (`closed` reason); console remains accessible
- [x] 3.4 Tests: team CRUD authorization, transfer (owner and admin paths), delete-empty vs delete-blocked, cancelled tournament visibility and gating

## 4. Admin panel API

- [x] 4.1 New `routers/admin.py`: list accounts (email, display name, role, hr_id, pending-plea marker), set role (Admin grants/revokes organizer; only Owner touches admin; nobody edits the Owner), plea queue list + grant/deny
- [x] 4.2 Plea endpoints for any account: submit plea with optional message (409 when one is pending), view own plea state; history retained on re-plea after denial
- [x] 4.3 Admin HR unbind endpoint: clear `hr_id` keeping profile fields, write `FencerProfileAudit`; fencer-side rebind stays 409
- [x] 4.4 Tests: role-change authorization matrix, plea lifecycle (submit/duplicate/grant/deny/re-plea), HR unbind and audit, panel access denied below Admin

## 5. Frontend

- [x] 5.1 API client: role on account payload, team/transfer/delete/cancel/plea/admin endpoints
- [x] 5.2 Tournament picker: "New tournament" visible only with Organizer role; "request organizer role" plea action (with message) and pending/denied state for accounts without it
- [x] 5.3 Setup phase: Team section (owner only — member table, add by email, remove, transfer ownership) and danger zone (delete when empty, cancel otherwise, with confirmation)
- [x] 5.4 Admin panel view (Admins/Owner only): account table with role controls per granting rules, plea queue with grant/deny, HR unbind action
- [x] 5.5 i18n: cs+en keys for all new surfaces (identical key sets)

## 6. Seed, docs, verification

- [x] 6.1 Update `scripts/seed_demo.py` and `dev.sh` docs: owner email setting, demo accounts with roles (owner, admin, organizer, plain fencer)
- [x] 6.2 README: role model summary, owner-email configuration, migration note for existing deployments (grant organizer to known organizers)
- [x] 6.3 Full verification: backend tests (incl. pilot replay untouched), ruff, frontend build, `openspec validate add-user-roles`
