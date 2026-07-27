## Context

Squire is a FastAPI + SQLAlchemy backend over a single-file SQLite database with
a React/TypeScript frontend styled under the "Bureau 1952" design system (see
`CLAUDE.md` and `openspec/squire-design-spec.md`). The fencer-facing flow lives
in `FencerHome.tsx` (tabbed list of `TournamentCard`s), `TournamentDetail.tsx`
(information + registration on one screen), and `Login.tsx` (signup with an HR
search step). Organizer setup lives in `SetupPanel.tsx`. Data models are in
`backend/app/models.py`, schemas in `schemas.py`, endpoints in
`routers/tournaments.py`.

This change is a set of small, mostly additive tweaks driven by
`openspec/small-layout-tweeks.md`: reuse the signup name field, add an explicit
HR ownership confirmation, add tournament subtitle/logo and discipline/extra
schedule metadata, re-lay-out the list cards, and split the tournament detail
into an information screen and a separate register screen. Two modeling
decisions were confirmed with the owner up front (see Decisions).

## Goals / Non-Goals

**Goals:**
- One name entry in signup; explicit, informed HR binding; HR id in the
  confirmed line.
- Optional subtitle and logo on tournaments; optional when/where + ruleset on
  disciplines; optional when/where/remark on extra services.
- List cards with 1 em inner padding, left logo, subtitle, and a responsive
  date/place layout that degrades cleanly when fields are absent.
- Tournament detail split: an information screen (disciplines + non-purchasable
  actions, no gear/merch) and a separate Register screen (all purchasable items
  grouped by section), the latter offered only when a slot is open.
- Stay entirely within the Bureau 1952 prohibitions.

**Non-Goals:**
- No change to pricing math, reservation lifecycle, payments, or the
  registration API contract.
- No new discipline schedule as structured time (free text is enough).
- No image cropping/editing UI beyond a bounded re-encode on upload.
- No routing framework change; screen switching stays state-driven as today.

## Decisions

### D1 — Logo stored as bytes in SQLite (not filesystem)
Store the logo as `logo_bytes: LargeBinary | None` plus `logo_mime: str | None`
on `Tournament`. Serve via `GET /tournaments/{slug}/logo`; upload via a
multipart endpoint that rejects uploads over ~512 KB and re-encodes/downscales
to a bounded PNG before persisting.

*Rationale:* the deployment's value is that all state is one SQLite file — a
media directory breaks the single-file backup and invites orphaned files and
dangling references. Logos are tiny (well under 100 KB), a range where SQLite is
as fast as or faster than the filesystem and keeps the write transactional with
the row. *Alternative (filesystem + filename):* rejected for the added media
dir, upload/serve/cleanup machinery, and backup-sync burden it imposes.

### D2 — Extend `ExtraItem` rather than a parallel activity model
Add optional `when`, `where`, `remark` to `ExtraItem`; add optional `when`,
`where`, `ruleset_name`, `ruleset_url` to `Discipline`. The register-screen
sections reuse the existing `ExtraCategory` enum (`seminar`→actions,
`afterparty`→actions, `rental`→gear lending, `merch`→merch & other).

*Rationale:* an afterparty is both informational and purchasable; one item can
render as an info line on the detail screen and a purchasable line on register,
with no duplication for an organizer to keep in sync. *Alternative (new
`TournamentActivity` model):* rejected — it splits the same afterparty into two
rows and doubles editing. The new fields are descriptive only and never touch
pricing (`pricing.py` is untouched).

### D3 — Two screens via existing state-driven view switching
`TournamentDetail.tsx` already renders sub-panels conditionally. Introduce an
internal screen state (`information` | `register`) so the information screen is
the default landing and a control opens the register screen. No router change,
no new URL. The register control is shown only when registration is open and at
least one discipline/item has an open slot (derived from the existing
availability payload), matching the fencer-home "Register availability"
behavior. Read-only (past) detail stays on the information screen only.

### D4 — HR ownership confirmation as an in-form step, name field reused
In `Login.tsx`, drop the separate name query inside `HRSearchPicker` for the
signup path by passing the form's `name` as the query and hiding the step's own
name input (the component already accepts `initialQuery`; add a prop to suppress
its query input in the signup context, or reuse `initialQuery` and remove the
second field). Selecting a candidate opens a confirmation panel (static, per
Bureau 1952 — no animated modal) showing name, nationality, club, HR id, and an
external hemaratings.com link (`https://hemaratings.com/fighters/details/{id}/`,
`target="_blank" rel="noreferrer"`); binding happens only on confirm. The
confirmed line uses an i18n string that includes the id, e.g.
`HEMA Ratings profile confirmed: {{name}} ({{hrId}})`.

### D5 — Responsive card date/place with CSS only
Replace the single `organizers · date · location` line in the card with a small
grid/flex block that wraps to fewer columns on narrow screens using CSS
(`flex-wrap` / `grid` with `auto-fit`, relative units), no JS breakpoints. Logo
sits in a left column that collapses when absent. All new styles use existing
`tokens.css` values only; no shadows, gradients, rounded cards, or radius > 2px.

### D6 — Additive migration, all fields nullable
One Alembic migration adds the new nullable columns. No backfill; existing rows
read as `NULL`/absent and every UI path treats absence as "omit". Legacy
tournaments and reproducible totals are unaffected.

## Risks / Trade-offs

- **DB growth from logos** → capped upload size + re-encode to a bounded image;
  worst realistic case is a few MB total. Acceptable for this deployment.
- **Serving raw bytes** → validate mime on upload, serve with a fixed
  `Content-Type`, no user-controlled filename or path; size cap limits abuse.
- **Two-screen split could regress the existing single-page flow** → keep the
  same components/panels, only gate them behind a screen state; cover with the
  existing detail tests plus new ones for the information→register transition.
- **Reusing one name field across form and HR search** → ensure the search still
  works when the fencer edits the name after a failed search; keep the field the
  single source of truth for the query.
- **Design-system drift** → every new element audited against the `CLAUDE.md`
  prohibition list before merge; no new hex values outside `tokens.css`.

## Migration Plan

1. Add nullable columns via one Alembic migration (`Tournament.subtitle`,
   `Tournament.logo_bytes`, `Tournament.logo_mime`; `Discipline.when`,
   `Discipline.where`, `Discipline.ruleset_name`, `Discipline.ruleset_url`;
   `ExtraItem.when`, `ExtraItem.where`, `ExtraItem.remark`).
2. Ship backend schema/endpoint changes (logo upload/serve, extended payloads),
   backward compatible.
3. Ship frontend changes behind no flag — additive rendering only.
4. Rollback: revert the migration (drops nullable columns); no data loss for
   pre-existing fields.

## Open Questions

- Column naming: `when`/`where` are SQL-reserved-ish words; use safe names such
  as `schedule_when`/`schedule_where` (or `sched_when`) at the model layer while
  keeping API/JSON keys friendly. Resolve during implementation.
- Exact upload cap and target dimensions for the logo re-encode (starting point:
  512 KB in, downscale longest side to ~512 px PNG) — tune during implementation.
