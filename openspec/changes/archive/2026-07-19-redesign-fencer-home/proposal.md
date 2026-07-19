## Why

Fencer Home (from `add-fencer-home`) is a centered card list of open tournaments only — it looks like a login dialog, not a working surface, and gives the fencer no view of announced tournaments whose registration hasn't opened, nor of their own tournament history. The organizer console already has a proven full-screen layout (topbar with logo, center control, identity block, account menu) that the fencer side should mirror so both surfaces feel like one application.

## What Changes

- Fencer Home becomes a full-screen console-style page with the standard topbar:
  - left: Hema Squire logo,
  - center: three filter tabs — Vyhlášené turnaje (Announced), Otevřené turnaje (Open), Proběhlé turnaje (Past),
  - right: the fencer's name with `HRID: <id>` linking to their hemaratings.com profile, or a "no hemaratings" link to the Profile page when no HR profile is bound,
  - far right: the existing account menu (⋯).
- The center area lists tournaments for the selected tab. Tabs are disjoint: **Open** = published upcoming tournaments with registration open right now; **Announced** = published upcoming tournaments whose registration is not open (not yet opened, or already closed); **Past** = tournaments before today where the fencer had a non-cancelled registration (paid, reserved, or substitute) or is an organizer — not all past tournaments.
- Login lands on this screen with the **Open** tab selected.
- Clicking a past tournament opens the tournament detail in read-only mode (info + own registration summary; no Register button, no payment panel). Results presentation remains a future change.
- New backend query for the Past tab (personal history); Announced/Open are served by the existing open-tournaments endpoint, which already returns all published upcoming tournaments with their registration status — the tabs are a client-side filter.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `fencer-home`: landing page becomes a full-screen tabbed console (Announced / Open / Past) with the fencer identity + HRID header; the tournament list requirement is split per tab, with Past limited to the fencer's own history; read-only detail for past tournaments.

## Impact

- Backend: new endpoint for past personal tournaments (registrations + organizer links) plus tests; `GET /api/tournaments/open` unchanged.
- Frontend: `FencerHome.tsx` rebuilt on the console `topbar`/workspace layout with tab state; `TournamentDetail.tsx` gains a read-only past mode; `api.ts`; cs/en i18n keys; `index.css`.
- Depends on `add-fencer-home` (currently being implemented) — must be applied after it; modifies its `fencer-home` spec once archived.
