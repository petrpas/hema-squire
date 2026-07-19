## Context

The backend already exposes everything the profile page needs except refined search: `GET/PATCH /api/account` (email, display_name, hr_id, nationality, club, role, is_deployment_owner), `POST /api/account/hr-binding` (bind-later, write-once, audited), `GET/POST /api/account/plea`, and `GET /api/hr/search?q=` (diacritics-insensitive substring search over `hr_fighters`). The frontend is a state-machine SPA (`App.tsx`: Login → TournamentPicker → Console/AdminPanel) with no router; the plea UI lives inline in `TournamentPicker.tsx`.

## Goals / Non-Goals

**Goals:**
- A Profile page (account info, role + plea, HR find-and-match) reachable from every logged-in surface via a shared top-right "⋯" menu.
- Nationality-filtered, similarity-ranked fighters search.
- Idempotent bootstrap of the Petr Paščenko owner/organizer account in dev.

**Non-Goals:**
- No fencer landing page ("To Fencer" is a disabled placeholder until that change).
- No changes to role granting, plea semantics, or binding rules; no removal of the picker's plea section (kept until the fencers page replaces the picker as landing).
- No avatar/password-change/self-service beyond email + full name.

## Decisions

- **D1 — View state, not a router.** `App.tsx` keeps its state-machine style; replace the boolean flags with a `view` union (`picker | console | admin | profile`) plus the selected tournament. Profile is a sibling top-level view. Alternative (react-router) rejected: out of proportion for one added page.
- **D2 — Shared `AccountMenu` component** rendered top-right on TournamentPicker, Console, AdminPanel, and ProfilePage. Items: My Profile, Admin Panel (only `role === "admin" || is_deployment_owner`), To Fencer (disabled, "coming soon" title), To Organizer (→ picker), Logout. App passes navigation callbacks; the menu owns no state beyond open/closed. The picker's existing logout link and Admin Panel button move into the menu on the picker too, but the plea section stays (per owner decision).
- **D3 — Effective role is presentation-only.** Label = Owner when `is_deployment_owner`, else the stored role. No API change; the data is already in `Account`.
- **D4 — Search: extend, don't fork.** `GET /api/hr/search` gains optional `nationality` param; new `GET /api/hr/nationalities` returns distinct nationalities from the index for the select. Ranking server-side: fold query and name (existing `fold()`), score with `difflib.SequenceMatcher.ratio()` plus a substring-containment bonus, return top 20. Nationality pre-filters in SQL; the folded-similarity pass runs in Python over the filtered rows (index is thousands of rows; with nationality it is hundreds — acceptable; without nationality, prefilter to rows sharing any query token substring before scoring). Alternative (SQLite FTS/trigram extension) rejected: heavier than needed now.
- **D5 — Binding and link.** Confirm calls the existing `POST /api/account/hr-binding`; 409-style conflict surfaces the "already bound elsewhere" message. Profile link: `https://hemaratings.com/fighters/details/{hr_id}/`.
- **D6 — Plea UI extraction.** Move `PleaSection` out of `TournamentPicker.tsx` into a shared component used by both the picker (unchanged behavior) and the Profile role section, so the two surfaces cannot drift.
- **D7 — Owner bootstrap as a dedicated idempotent script** (`scripts/seed_owner.py`, callable standalone and from `dev.sh`): upsert fencer `petr.pascenko@gmail.com`, display name "Petr Paščenko", `role=organizer`, `password_hash=hash_password("swordismylife")` (scrypt, `app.auth.hash_password`). `dev.sh` defaults `HEMA_SQUIRE_OWNER_EMAIL=petr.pascenko@gmail.com` (still overridable). Alternative (fold into `seed_demo.py`) rejected: the owner account should exist without the demo tournament data.

## Risks / Trade-offs

- [Plaintext password in repo] → dev bootstrap only; production deployments set their own owner credentials. Noted in script docstring.
- [Similarity scoring in Python over an unfiltered index could be slow] → nationality filter is the primary path; unfiltered path prefilters by token substring and caps scored rows; revisit with FTS if the index grows.
- [Duplicated plea UI (picker + profile)] → mitigated by D6 extraction; picker copy is deleted wholesale when the fencers landing page replaces it.
- [Menu on Console overlaps existing header controls] → menu is additive; existing Console logout can be removed in the same pass to avoid two logout affordances.

## Migration Plan

Additive only: no schema migration (all columns exist). Deploy backend then frontend in one release; run `seed_owner.py` in dev via `dev.sh`. Rollback = revert; no data cleanup needed (the seeded account is harmless).

## Open Questions

- None blocking. "To Fencer" target page is deferred to the fencers-landing change.
