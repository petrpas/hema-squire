# Design: fix-setup-tab-click

## Context

The console stepper renders seven `.step-slot` flex children; every slot after the first contains a connector line plus the tab button. `.step-slot:first-child { flex: 0 }` was meant to stop the connector-less first slot from stretching, but the shorthand sets `flex-basis: 0%`, and with the slots' `min-width: 0` the Setup slot collapses to zero width. Its button overflows and the next slot's connector, later in paint order, covers the button and swallows clicks.

## Goals / Non-Goals

**Goals:** restore the Setup tab's clickable area with the minimal CSS correction; keep the stepper's visual layout otherwise unchanged.

**Non-Goals:** any stepper redesign, responsive rework, or component restructuring.

## Decisions

### D1: `flex: none` on the first slot
`flex: none` (`0 0 auto`) sizes the slot to its content, which is the original intent. Alternative rejected: `z-index`/`pointer-events` patches on the connector — they would leave the layout genuinely wrong (a zero-width slot with overflowing content) and only mask the symptom.

## Risks / Trade-offs

- [Stepper spacing shifts slightly since the first slot now occupies real width] → That is the correct layout; verified visually across all seven tabs at normal and narrow widths (the stepper already has `overflow-x: auto` for narrow cases).
