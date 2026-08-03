# Squire UI — design prohibitions

Full design spec: `openspec/squire-design-spec.md` ("Bureau 1952"). This section
(copied from spec section 8) is binding for all Squire frontend work regardless
of what else is in context.

This list takes precedence over everything else. The implementation NEVER uses:

- gradients, shadows (`box-shadow`, `text-shadow`), blur, glow
- zebra stripes in tables
- `border-radius` > 2px (no pills, no rounded cards)
- pure white `#FFF` or pure black `#000`
- default blue links or the browser's default blue focus outline
- emoji or filled icons
- skeleton shimmer, spinners, animated progress bars
- toasts with entrance animations; confirmations are static and leave via
  fade-out
- weight 600+, Title Case, exclamation marks in system copy
- more than one saturated color (`--stamp` is the only one)
- any hex value outside `tokens.css`

# Frontend conventions

Components live one per file; a file approaching ~300 lines should be split
along component seams. Panels composed of sections keep the orchestrator thin
and give each section its own file under a directory named after the panel
(see `frontend/src/setup/`).
