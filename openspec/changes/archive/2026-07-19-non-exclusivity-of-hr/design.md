## Context

Exclusivity is enforced in three places: a `unique=True` on `Fencer.hr_id` (models.py, created as an unnamed `UniqueConstraint('hr_id')` in the core migration), a 409 `hr_id_already_bound` in `signup` (routers/auth.py), and the same 409 in `bind_hr_later` (routers/accounts.py). The frontend maps that detail to `signup.errors.hrBound` (Login.tsx) and `profile.hr.conflict` (ProfilePage.tsx). Nothing else depends on `Fencer.hr_id` being unique — registration exports read `registration.fencer.hr_id` per row, and rating snapshots key on hr_id independently of accounts. `HRSearchPicker` is the shared candidate UI for both the signup window and the Profile page. The admin panel already lists accounts (`GET /api/admin/accounts` → `AdminAccountOut`) and has the hr-unbind resolution action. Alembic runs with `render_as_batch=True` (SQLite-compatible).

## Goals / Non-Goals

**Goals:**
- Allow any account to claim any HR profile; never block on an existing claim.
- Make an existing claim visible to the fencer at claim time (warn, don't block).
- Make duplicate claims visible to admins in the accounts list; resolution stays hr-unbind.

**Non-Goals:**
- No claim verification (identity proof, email to club, etc.) — future work if ever.
- No change to fencer-side write-once binding (rebinding a different profile stays admin-only).
- No account recovery / merge flow; duplicates are resolved by admin unbinding.

## Decisions

- **D1 — Surface the existing claim in HR search results.** `HRProfile` (the search result schema) gains `claimed: bool` — true when any account currently binds that hr_id. The one shared `HRSearchPicker` renders the notice on claimed candidates and the signup window repeats it next to a confirmed claimed profile, so both entry points warn identically without a second endpoint. Alternative (dedicated pre-check endpoint or warn only after submit) rejected: extra round-trip or too late to inform the choice. `/api/hr/search` is public, so `claimed` leaks one bit (an account exists for this profile) — accepted; it contains no identity of the claimant.
- **D2 — Delete the 409s outright; no soft-confirm parameter.** `signup` and `bind_hr_later` simply stop checking for an existing claimant; no `force`/`confirm` flag, since the UI already warned. This removes the `hr_id_already_bound` error contract — frontend mappings and i18n keys are replaced by the claimed-notice keys.
- **D3 — Migration drops the unique constraint via batch table recreate.** The constraint is unnamed and the DB may be SQLite, so the migration uses `batch_alter_table` with a `copy_from` table definition omitting the constraint (plain `drop_constraint` needs a name SQLite never stored). Model side: `unique=True` removed; a plain (non-unique) index on `hr_id` is added since the admin duplicate flag groups by it.
- **D4 — Admin duplicate flag computed per listing, not stored.** `AdminAccountOut` gains `hr_shared: bool`, filled by one grouped query (hr_ids with count > 1) over the accounts listing; the admin table shows a warning badge on those rows. Alternative (persisted flag or separate duplicates endpoint) rejected: the listing is small-scale and already loads all accounts; owner chose the in-list flag over a dedicated section.

## Risks / Trade-offs

- [A malicious user can claim a famous fighter's profile] → already possible today by claiming first; non-exclusivity at least never locks the real owner out, and admins see the collision in the accounts list.
- [Duplicate claims make "the account for hr_id X" ambiguous] → nothing resolves accounts by hr_id today (verified); future features that need it must handle multiplicity — the spec now says claims are non-exclusive.
- [Public `claimed` bit reveals a profile has an account] → single boolean, no claimant identity; accepted.
- [Warning relies on search-time data] → a claim created between search and submit goes unwarned; harmless, since submit succeeds either way and admins still see the duplicate.

## Migration Plan

One alembic revision: batch-recreate `fencers` without the hr_id unique constraint, then create a non-unique index on `hr_id`. Purely relaxing — existing data always satisfies it. Rollback (drop index, re-add unique constraint) only works while no duplicates exist; after real duplicate claims, rolling back requires admin unbinding first — acceptable.

## Open Questions

- None.
