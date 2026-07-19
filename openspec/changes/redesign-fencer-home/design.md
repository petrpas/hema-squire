## Context

`add-fencer-home` (implemented, pending archive) delivered `FencerHome.tsx` as a centered `login-card` list fed by `GET /api/tournaments/open`, which already returns every published, non-cancelled, upcoming tournament with `registration_status ∈ {open, opens_on, closed}`, per-discipline counts, and the caller's `my_registration_state`. `TournamentDetail.tsx` renders info + registration form/management. The organizer console (`Console.tsx`) has the target layout: `header.topbar` with logo button, a center control (`stage-control`), an identity block (`tournament-info`), and `AccountMenu`. Accounts carry an optional `hr_id` (hemaratings binding lives on the Profile page; public profile URL is `https://hemaratings.com/fighters/details/{hr_id}/`).

## Goals / Non-Goals

**Goals:**
- Fencer Home as a full-screen console-style page: topbar (logo | tabs | fencer identity + HRID | menu) and a tournament list workspace.
- Three disjoint tabs: Otevřené (registration open now, default after login), Vyhlášené (published upcoming, registration not open), Proběhlé (own history: non-cancelled registration or organizer).
- Read-only tournament detail for past tournaments.

**Non-Goals:**
- No results/standings of past tournaments (future change) — only listing and read-only detail.
- No changes to registration, pricing, payment, or the organizer console.
- No public (logged-out) browsing; no HR binding UI changes (Profile page keeps it).

## Decisions

- **D1 — Tabs are a client-side filter of `/open`; Past gets its own endpoint.** Otevřené = `registration_status === "open"`; Vyhlášené = the rest of the `/open` payload (opens_on + closed, still upcoming). The endpoint already returns exactly the published-upcoming superset, so no backend change. Past cannot be derived client-side (it needs history + organizer links), so add `GET /api/tournaments/mine/past`: non-cancelled tournaments with `date < today` where the caller has a non-cancelled registration or is in the tournament's organizers, ordered by date descending, reusing the `OpenTournamentOut` DTO (counts still meaningful; `registration_status` fixed to `closed`, `my_registration_state` folded in). Alternative (one endpoint with a `scope` query param) rejected: the past query joins different tables and shouldn't burden the hot list path. Route must be declared before `/{slug}` routes to avoid path capture.
- **D2 — Topbar reuse.** `FencerHome` renders the console's `header.topbar` structure: logo button (no-op/refresh — fencers have no "back"), a `stage-control`-style tab nav in the center, a `tournament-info`-shaped identity block (fencer display name; second line `HRID: <id>` as an external link, or a "no hemaratings" link that navigates to Profile), then `AccountMenu`. Reuses existing CSS classes; only minor additions to `index.css`. Alternative (new bespoke header component) rejected: one visual language, less CSS.
- **D3 — Tab state and landing.** Tab is local component state defaulting to Otevřené; login keeps landing on `home` (no view-union change). Each tab fetches lazily: `/open` once for both upcoming tabs, `/mine/past` on first visit to Proběhlé. Empty states get per-tab i18n copy.
- **D4 — Read-only past detail.** `TournamentDetail` gains a `readOnly` prop (set when navigating from the Past tab). In read-only mode it renders the info header, disciplines/extras with prices, and the caller's registration summary (state + items + total) when one exists; it suppresses the registration form, payment panel, and cancel action. Alternative (separate PastDetail component) rejected: 90 % of the rendering is shared.
- **D5 — Organizer-only past tournaments.** For past tournaments where the caller only organized (no registration), the card shows an "organizer" chip instead of a registration state and detail shows no registration summary. Clicking still opens the read-only fencer detail — jumping into the organizer console stays a `To Organizer` affair.

## Risks / Trade-offs

- [Closed-but-upcoming tournaments land in Vyhlášené, which may surprise ("announced" implies future opening)] → status badge on each card already says "closed"/"opens on"; disjointness was an explicit owner decision.
- [`/mine/past` grows unbounded over years] → ordered by date desc; add pagination only when it shows (personal history stays small for now).
- [Read-only flag on `TournamentDetail` could drift from registration-window logic] → read-only is driven by the caller (Past tab) and by `date < today` on the payload as a belt-and-braces check.
- [Concurrent `add-fencer-home` apply session touches the same files] → apply strictly after `add-fencer-home` is finished and archived.

## Migration Plan

Additive: one new endpoint, frontend rework of `FencerHome` and a prop on `TournamentDetail`. No schema migration. Rollback = revert.

## Open Questions

- None. Results for past tournaments are a future change.
