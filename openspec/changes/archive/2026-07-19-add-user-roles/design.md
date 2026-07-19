# Design: add-user-roles

## Context

Every account is a `Fencer` row (email + password, optional write-once HR binding). Per-tournament console access is the `TournamentOrganizer` link table; the creator becomes its first member, and any signed-in account may create tournaments — a placeholder from `add-tournament-setup` where access policy was deferred. There is no global role concept, no owner of a tournament, and no way to delete or retire one. All decisions below were made interactively with the owner (2026-07-19).

## Goals / Non-Goals

**Goals:**
- Global role ladder (Owner, Admin, Organizer, Fencer) with in-app granting and an Organizer plea workflow.
- Per-tournament split: Tournament Owner (creator; team, transfer, delete/cancel) vs Tournament Organizer (console access).
- Minimal admin panel: users, roles, plea queue, HR unbinding.
- Tournament lifecycle guard: hard delete only while empty, cancel/archive afterwards.

**Non-Goals:**
- Public registration UI (next change, `add-public-registration`).
- Email notifications for pleas or role changes (admins check the queue).
- Fine-grained per-tournament permissions (any team member has full console access).
- Account recovery / password reset flows.

## Decisions

### D1: Single role enum on Fencer, ladder semantics
`Fencer.role`: `fencer` (default) | `organizer` | `admin`. Capabilities are rank-based: create tournaments requires ≥ organizer, manage roles requires ≥ admin. A ladder avoids flag combinatorics; an Admin who runs tournaments doesn't need a second flag.
*Alternative rejected:* separate boolean flags or a role table — more expressive than the model needs; the owner defined a strict hierarchy.

### D2: Owner is computed from configuration, not stored
The account whose email equals `settings.owner_email` is the deployment Owner: all capabilities, plus granting/revoking Admin. Never stored in the DB, cannot be revoked in-app, and works even if the account signs up after deployment. Avoids any bootstrap/seed problem.

### D3: `owner_id` on Tournament, team table unchanged
`Tournament.owner_id` (FK to fencers, nullable for safety) holds the single Tournament Owner; `TournamentOrganizer` rows remain the team. Console access = owner OR team member (`require_console_access`, replacing today's `require_organizer` check). The creator is recorded as owner only — no duplicate team row. Any account can be added to a team; the global Organizer role gates only creation. Ownership transfer (owner-initiated, to a team member; global Admin as fallback for stuck cases) updates `owner_id` and adds the old owner to the team so they keep access.
*Migration backfill:* each existing tournament's earliest `TournamentOrganizer` row becomes its owner; tournaments with no rows keep `owner_id` NULL until an Admin assigns one.

### D4: Plea workflow as an OrganizerRequest table
`OrganizerRequest`: fencer_id, message (optional), state (pending/granted/denied), created_at, decided_at, decided_by. One pending plea per account; a denied account may plead again (new row — history retained). Granting sets the fencer's role; the queue lives in the admin panel.

### D5: Tournament lifecycle — delete only while empty, cancel afterwards
Hard DELETE is allowed only when the tournament has no registrations at all (any state); it cascades config rows only. Otherwise the Tournament Owner may cancel: `cancelled_at` timestamp; a cancelled tournament is hidden from public listings, its registration gate rejects with the existing `closed` reason, and its console stays accessible for records. Financial history is never deletable.

### D6: Admin HR unbinding, fencer-side write-once unchanged
An Admin may clear a wrongly linked `hr_id` (profile fields keep their values; the change is recorded in `FencerProfileAudit`). The fencer can then bind the correct profile via the existing flow. Fencer-initiated rebinding stays rejected (409), preserving the write-once rule.

### D7: Revoking Organizer keeps existing tournaments
Revocation only removes the ability to create new tournaments. Existing ownership and team memberships are untouched — revocation mid-season must not break a live tournament. Admins remove someone from a specific tournament via that tournament's team if needed.

## Risks / Trade-offs

- [Owner email typo in config] → Owner capabilities are simply dormant; fixing the setting requires no migration. Log a startup warning when no account matches.
- [BREAKING: existing accounts lose tournament creation] → Deployment is small; migration note tells the operator to grant `organizer`/`admin` to known organizers (seed script does this for the demo).
- [NULL owner after backfill] → Only possible for tournaments that already had no organizers (effectively orphaned today); admin panel can assign an owner.
- [Cancelled tournaments reuse `closed` reason] → Fencers see "closed" rather than "cancelled"; acceptable for v1, avoids touching the availability contract.

## Migration Plan

1. Alembic: add `fencers.role` (server default `'fencer'`), `tournaments.owner_id` + `cancelled_at`, create `organizer_requests`; backfill owners from earliest team row.
2. Deploy with `HEMA_SQUIRE_OWNER_EMAIL` set; grant roles via admin panel (Owner signs in).
3. Rollback: downgrade drops the new columns/table; creation gate disappears with the code.

## Open Questions

None — all policy decisions were made by the owner in the planning conversation.
