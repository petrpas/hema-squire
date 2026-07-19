# Add User Roles

## Why

Today any signed-in account can create tournaments (a placeholder from `add-tournament-setup`, where access policy was explicitly deferred), and per-tournament console access is a flat organizer list with no owner. Before the app opens to the public (`add-public-registration`), the deployment needs a real authorization model: who may create tournaments, who manages people, and who controls each tournament's team and lifecycle.

## What Changes

- Introduce four global roles: **Owner** (one per deployment, from configuration), **Admin** (granted/revoked by Owner), **Organizer** (may create tournaments; granted/revoked by Admin), **Fencer** (every account).
- Add an in-app **plea workflow**: any account can request the Organizer role with an optional message; Admins see a pending queue and grant or deny.
- Add a minimal **admin panel**: user list with roles, role management, plea queue, and audited HRID unbinding for wrongly linked accounts.
- Split the per-tournament organizer concept: **Tournament Owner** (the creator; manages the team, transfers ownership, deletes or cancels the tournament) vs **Tournament Organizer** (console access, granted by the Tournament Owner to any account — no global role required).
- **BREAKING**: tournament creation is restricted from "any signed-in user" to accounts holding the global Organizer role.
- Tournament lifecycle guard: hard delete only while the tournament has no registrations; afterwards the owner can cancel/archive (hidden from public, registration closed, data retained).
- Revoking the global Organizer role stops future tournament creation but does not strip access to tournaments the account already owns or organizes.

## Capabilities

### New Capabilities
- `user-roles`: the global role model (Owner/Admin/Organizer/Fencer), role granting and revocation rules, the Organizer plea workflow, and the admin panel surface.

### Modified Capabilities
- `tournament-admin`: creation restricted to the Organizer role; new Tournament Owner concept (team management, ownership transfer, delete/cancel lifecycle); "Organizer authorization" requirement reworded around the owner/team split.
- `fencer-accounts`: HR binding stays write-once for the fencer, but an Admin SHALL be able to unbind a wrongly linked hr_id (audited), reopening the account for a correct binding.

## Impact

- Backend: `models.py` (role column/table on Fencer, owner marker on the tournament team, plea table), Alembic migration, `auth.py` (role dependencies: require_admin, require_organizer_role, require_tournament_owner), `routers/tournaments.py` (creation gate, team CRUD, transfer, delete/cancel), new `routers/admin.py` (users, roles, pleas, HR unbind).
- Frontend: admin panel view, team management in the console Setup phase, "request organizer role" surface, tournament delete/cancel controls.
- Config: owner email setting; seed/demo script updated to assign roles.
- Existing tournaments: migration backfills each tournament's first organizer as its Tournament Owner.
