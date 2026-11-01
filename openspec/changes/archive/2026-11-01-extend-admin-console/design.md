## Context

`frontend/src/AdminPanel.tsx` renders the plea queue and a table of every `Fencer` row (`GET /api/admin/accounts`, ordered by email) on one page. The backend (`backend/app/routers/admin.py`) knows nothing about tournaments. Hard delete of a tournament exists only for its owner (`DELETE /api/tournaments/{slug}`, `routers/tournaments.py`) and only while the tournament has no registrations. Its `_cascade_delete` therefore never had to remove anything under a registration, and it does not.

Owner decisions taken when the change was proposed (2026-10-29):

- deleting people is a separate change, not this one;
- an admin delete of a tournament with registrations mails nobody;
- any Admin may delete any tournament (the role ladder's usual rank check, nothing stricter);
- the pending-tasks tab holds the plea queue and shared HR IDs. Undelivered outbox mail is not included.

## Goals / Non-Goals

**Goals:**
- Three tabs, with search and sort over people and tournaments.
- An admin delete that removes a tournament with everything under it and leaves nothing dangling.
- A server-side guard: deleting a tournament with registrations needs a confirmation the client cannot skip by accident.

**Non-Goals:**
- Deleting or anonymizing people.
- Server-side paging or search. The lists are small: hundreds of people and tens of tournaments.
- Admin access to a tournament's console. The admin list does not link into consoles.
- An undo or soft-delete for the admin delete.
- Showing undelivered mail.

## Decisions

### D1. Search and sort run in the client over the full lists

Both lists arrive whole, as the account list does today, and the browser filters and sorts them. At the deployment's scale this is instant and needs no new query parameters. Names fold through `nameSearch.ts` (`foldName`, `nameMatches`) so the admin search behaves exactly like roster search. Email, slug and HR ID match on a substring of the folded text. Sort state lives in the component and is not kept in the URL.
*Alternative*: server-side `?q=&sort=`. It earns its keep only at a scale this deployment will not reach, and it would add a request per keystroke.

### D2. Tabs are component state; the route stays `/admin`

The tab strip reuses the existing tab markup (`role="tablist"`, `stage-control`, `tab-count`, as in `payments/PaymentTabs.tsx`) and its arrow-key handling. The selected tab is local state that starts on pending tasks. No new path goes into `routes.ts`, because nothing links to a particular admin tab.
*Alternative*: `/admin/people` and the like. Rejected for now, since no mail or page links there. It can be added later without breaking `/admin`.

### D3. Shared HR IDs are derived in the client from the account list

`AdminAccountOut.hr_shared` already marks every account whose HR ID another account also holds. The tasks tab groups those accounts by `hr_id`, so no new endpoint is needed. Unbinding refreshes the account list, and a group with fewer than two members drops out. `AdminAccountOut` gains `created_at` for the people tab.

### D4. `GET /api/admin/tournaments` returns a flat row per tournament

Each row carries `slug`, `name`, `date`, `state` (`draft` | `published` | `cancelled`, derived from `published_at` / `cancelled_at`; cancelled wins), the owner's `id`, `display_name` and `email` (nullable: `owner_id` can be null), `registration_count`, and `credited`: a list of `{currency, amount_cents}`, the sum of live `PaymentCredit` rows (`reversed_at IS NULL`) grouped by currency. Counts and sums come from grouped queries rather than a query per row. `credited` is in the list so the confirmation dialog can state it without a second request. `Tournament` has no creation timestamp, and adding one would leave every existing row empty, so the list carries none.

### D5. `DELETE /api/admin/tournaments/{slug}?confirm=true`

The handler requires `Role.ADMIN` and not team membership. It reads the registration count inside the same transaction as the delete. If registrations exist and `confirm` is not true, it answers `409 has_registrations` and deletes nothing. This is the same detail code the owner's delete uses. The client sends `confirm=true` only from the confirmation dialog's button. The owner's endpoint is unchanged.
*Alternative*: echo the expected registration count as the confirmation token (`?expect=12`). That would also catch a registration arriving while the dialog is open. Rejected as more than the risk calls for: the dialog shows the count read when the list loaded, and a registration that arrives meanwhile goes with the rest, which is what the admin chose.

### D6. One cascade, moved out of the router and made complete

`_cascade_delete` moves from `routers/tournaments.py` to a module of its own (`app/tournament_delete.py`), and both endpoints call it. It grows to delete, in dependency order:

1. under registrations: `TeamMember` → `Team`, `RegistrationDiscipline`, `RegistrationExtra`, `PaymentCredit`, `PaymentWaiver`, `ManualPayment`, `PaymentEvent`. `BankTransaction` goes before registrations, because `matched_registration_id` points at them.
2. `Registration`.
3. the existing tournament-scoped list (snapshots, imports, rules and journal, manual rows, row numbers, organizers, extra items, disciplines), plus `Operation`, which the empty-tournament cascade never met.
4. the tournament.

All of it runs in one transaction. SQLite here has no `ON DELETE CASCADE`, so each table is named explicitly, as today.

To keep the list from going stale, a test walks `Base.metadata`. It collects every table with a foreign key to `tournaments.id`, or to the PK of a table that has one, and asserts that after an admin delete of a fully populated tournament none of them holds a row referring to it. A new table added later then fails this test until the cascade knows about it.

### D7. Confirmation is a `Modal`, shown only when registrations exist

A tournament with `registration_count == 0` is deleted on click, then the list refreshes. Otherwise the delete control opens a `Modal` that states the count and each currency's credited sum (through `money.ts` formatting). It says in plain text that a real event is cancelled by its organizer rather than deleted. Its buttons are "Smazat akci" (stamp-coloured, as other destructive confirmations) and "Zpět". Copy follows the design prohibitions: sentence case, no exclamation marks.

### D8. Frontend layout

`AdminPanel.tsx` becomes the orchestrator: it loads the lists, holds the tab and renders one section. Sections go under `frontend/src/admin/`: `AdminTabs.tsx`, `TasksTab.tsx` (pleas and shared HR IDs), `PeopleTab.tsx`, `TournamentsTab.tsx`, `DeleteTournamentDialog.tsx`, and a small `sortable.ts` (sort-state hook plus a header cell that renders `aria-sort` and a direction mark with a Tabler outline chevron, no filled icon). The people-table markup moves out of `AdminPanel.tsx` unchanged, apart from the new column.

## Risks / Trade-offs

- [An admin deletes a real event with paid fencers by mistake] → A confirmation that states the count and the money, the server-side `confirm` guard, and the dialog's reminder that real events are cancelled. There is no undo. The database backup is the recovery path.
- [The cascade misses a table added later and the delete fails on an FK, or leaves orphans] → The metadata-driven test (D6) fails until the cascade covers the new table.
- [Fencers who paid get no word that the event is gone] → Accepted by owner decision. The admin delete exists for test and junk tournaments.
- [Client-side filtering stops scaling] → Revisit with D1's alternative if the people list reaches thousands.

## Migration Plan

No schema change. The work deploys as a normal release. Rollback is a code revert, with nothing to undo in data except tournaments that were already deleted.

## Open Questions

None.
