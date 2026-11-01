## Why

The admin panel is one page: the plea queue above a table of every person, sorted by address, with no search and no way to see tournaments at all. That was enough for the first accounts and is not enough for a deployment with real traffic. An admin who needs to find a person scrolls. An admin who wants a test or junk tournament gone has to ask its owner, and cannot remove it at all once someone has registered.

## What Changes

- The admin panel is split into three tabs: **Úkoly** (pending tasks), **Lidé** (people) and **Akce** (tournaments).
- **Úkoly** gathers what waits on an admin. It holds the organizer plea queue as it is today, plus **shared HR IDs**: every HR ID bound by more than one account, listed with those accounts and the existing unbind action. Today a shared ID is only a tag in the people table. The tab label carries the count of open items.
- **Lidé** is today's account table with a search box (name, address, HR ID) and sortable columns (name, address, role, HR ID, created). Role controls and unbinding stay as they are.
- **Akce** is new: every tournament, drafts and cancelled ones included, with name, date, owner, state and registration count. A tournament records no creation date, so none is shown. It can be searched (name, slug, owner) and sorted by each column.
- An admin can **delete a tournament**. One with no registrations goes in one step, as the owner's delete does today. One with registrations asks for confirmation first. The dialog states the number of registrations and the amount credited, and reminds the admin that an organizer's real event is cancelled, not deleted. The delete then removes the tournament with everything hanging off it, registrations and payment history included. Nobody is mailed.
- **BREAKING (spec)**: "financial history is never deletable" stops being absolute. It still binds the Tournament Owner, whose delete stays limited to an empty tournament. A global Admin can override it with explicit confirmation.
- Deleting people is **out of scope**. A person is referenced from registrations, tournament ownership, organizer teams and other people's console records. What deleting one means is its own change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `user-roles`: the Admin panel requirement gains the three tabs, search and sorting over people and tournaments, and the shared-HR-ID task list.
- `tournament-admin`: the deletion requirement gains the admin delete. It works on a tournament in any state and, when registrations exist, only after explicit confirmation.

## Impact

- `backend/app/routers/admin.py`: `GET /api/admin/tournaments` (list with owner, state, registration count, credited sum), `DELETE /api/admin/tournaments/{slug}` (refuses `has_registrations` unless confirmed), and `created_at` on `AdminAccountOut`. Shared HR IDs are grouped client-side from the account list.
- `backend/app/routers/tournaments.py` `_cascade_delete` moves to a shared module and grows to cover registrations and every table hanging off them (extras, disciplines, teams, payment events, credits, waivers, manual payments, bank transactions, operations). A test derived from the model metadata guards the cascade against new tables being forgotten.
- `frontend/src/AdminPanel.tsx` becomes a thin orchestrator over `frontend/src/admin/` (tasks, people, tournaments, delete dialog via `Modal`), with `cs`/`en` locale keys and `api.ts` additions.
- No migration, no new dependency.
