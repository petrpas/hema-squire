## Context

The list's card (`TournamentCard`) owns the cover, plate, ring and status
block; the detail's blocks are `TournamentFace` components shared with the
console's Setup preview. `rail-card`, `button.secondary`, the primary button
and `.stage-control` are shared with the whole console.

## Goals / Non-Goals

**Goals:** the detail reads as the card opened; the console pixel-identical.

**Non-Goals:** restyling the entrant tables or form fields; changing what the
detail states.

## Decisions

### D1. Shared rules read tokens, never a skin selector
`.rail-card` takes `border-radius: var(--radius-card)`; the primary and
secondary button rules take `var(--radius-pill)`. Day values are 2px, so the
console is unchanged; no rule in `index.css` names the skin.

### D2. One pill tab control, two users
The list's `.stage-control.home-tabs` rules become a modifier,
`.stage-control-pill`, worn by the list's filter tabs and the detail's tabs.
The Setup preview's own tabs (`preview-tabs`) and the entrants tab's
discipline band (`entrants-band`) take it too: the preview is night, and the
roster's band sat square beside the pill tabs above it.

The registration form's title (`.tiskopis-number + h1`) also reads the display
tokens, as the detail's other titles do; and the information block is kept
from shrinking in a flex column (`flex: none`), which its clipping otherwise
allows.

### D3. Cover extracted from the card
`CoverPlate` (plate with logo/short code/monogram and ring) and `coverTint`
move into `TournamentCover.tsx`, used by `TournamentCard`, `NextOpening` and
`InfoHeader`. `StatusBlock` takes the few fields it reads
(`registration_status`, `registration_closes_on`, `registration_opens_on`,
`registration_opens_at`, `timezone`) rather than a whole `OpenTournament`, so
the detail feeds it its own client-computed status (`registrationStatus(detail,
now)`) and its closing day (`registration_closes ?? date`, the same fallback
`setup.registration_closes_on` states).

### D4. Meter track as its own piece
`CapacityMeter`'s track becomes `MeterTrack` (`aria-hidden`, static), reused
under each detail discipline row; the row's existing count text stays the
statement and stays a link.

### D5. The preview panel carries the skin
`SetupPreview`'s root gets `data-skin="night"`. Everything inside inherits;
the console around it does not. Its `min-height: 100dvh` from the night root
rule must not apply to the panel, so the full-height paint moves from the
skin block to the layout roots that need it (`.app`, `.login-page`).

## Risks / Trade-offs

- [The night island in the console looks out of place] → Owner decision; it
  is what fencers will see.
- [Pill buttons on wide form actions look heavy] → Primary keeps its full
  width where it had it; only corners change.

## Migration Plan

Frontend plus two additive response fields. No data change.

## Open Questions

None.
