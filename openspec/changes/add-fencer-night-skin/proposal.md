## Why

The fencer-facing side of Squire (tournament list, detail, entrants, sign-in) is
read mostly on phones by a younger audience, and today it wears the same light
ledger as the organizer console. A dark skin with cards, bolder display type and
a visible fill state makes the list easier to scan and gives the public side an
identity of its own, while the console stays Bureau 1952. The design source is
`openspec/night-skin-brief.md`, section 1.

## What Changes

- **Skins.** `tokens.css` gains a `[data-skin="night"]` block that redefines the
  existing role tokens (`--paper`, `--ink`, `--stamp`, …) for dark, plus new role
  tokens whose day values change nothing (`--radius-card/pill/plate/chip`,
  `--font-display`, `--weight-display`, `--body-size`, `--hairline-strong`,
  `--stamp-on-tint`, `--plate`, `--qr-paper`, `--scrim`). No component
  reads the skin.
- **Where it applies.** Every screen under the fencer layout (list, detail and
  its tabs, the sign-in screen it renders), the Profile page and the not-found
  screen render night, always — no `prefers-color-scheme` branch and no toggle.
  Organizer and admin screens stay day. The skin follows the route, not the role.
- **BREAKING (binding text).** The global prohibitions on `border-radius > 2px`
  and weight 600+ gain carve-outs that hold only through the named skin tokens.
  `CLAUDE.md` and the `design-system` spec change together, before any CSS.
- **Capacity meter.** A new static figure: a 4px track showing entered/capacity,
  stated beside it as text, never animated.
- **Home page redesign.** Cards in a grid instead of rows: a cover with a
  deterministic tint, a logo plate or monogram, a ring while registration is
  open, an ordinal, and a three-line status block; per-discipline meters; a
  footer stating seated fencers and clubs. Organizer names stay on the card as
  plain text. The tab band becomes a segmented pill control. A next-opening
  strip counts down to the nearest registration opening within 7 days.
- **Card actions.** The card states registration state through its status block
  and the whole body links to the detail; the spec's per-card Register / Manage
  registration action is retired to match the code. Spravovat stays.
- **Payload.** `OpenTournament` gains `registration_closes_on`, `entrant_count`
  and `club_count`, all public aggregates.
- **Monogram.** A pure `monogram(displayName)` helper used where a tournament has
  no logo.
- **Narrow screens.** Below 480px a card becomes a compact row with a 56px plate.

## Capabilities

### New Capabilities
<!-- none: every behavior extends an existing capability -->

### Modified Capabilities
- `design-system`: adds Skins, the capacity meter and display headings; modifies
  Typography conventions, Global prohibitions, and Modal and payment slip
  framing (scrim and QR plate tokens).
- `fencer-home`: modifies the landing (cards, tab band, narrow row) and the Past
  tab's card parts; adds the monogram and the next-opening strip.
- `public-browsing`: the list payload gains three public aggregates.
- `profile-page`: the Profile page renders in the night skin.
- `routing`: the not-found screen renders in the night skin.

## Impact

- Frontend: `tokens.css`, `index.css` (home, card, tab band, slip QR, modal
  scrim), `index.html` (Plex Sans Condensed 600/700 on the existing Google Fonts
  link), `FencerShell.tsx`, `FencerLayout.tsx`, `FencerHome.tsx` split into
  `TournamentCard.tsx`, new `NextOpening.tsx`, `monogram.ts`, `slugHash` lifted
  out of `PaidStamp.tsx`, `ProfilePage.tsx`, `NotFound.tsx`, `cs.json`/`en.json`.
- Backend: `OpenTournamentOut` and its builder in `routers/tournaments.py`;
  batched counts for the `/open`, `/held` and mine lists.
- Binding text: `CLAUDE.md`.
- Organizer console: no visual change (new tokens have day values equal to the
  old literals).
