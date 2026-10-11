## 1. Payload

- [x] 1.1 `logo_tint` and `short_code` on `FencerTournamentOut` (and `TournamentOut` for the preview); add to the `FencerTournament` pick in `api.ts`; scoped pytest

## 2. Shared geometry

- [x] 2.1 `.rail-card` reads `--radius-card`; primary and secondary buttons read `--radius-pill`; verify the console's computed radii stay 2px
- [x] 2.2 `.stage-control-pill` modifier from the list's tab rules; worn by the list tabs, the detail tabs and the preview tabs

## 3. Cover on the detail

- [x] 3.1 `TournamentCover.tsx`: `coverTint`, `CoverPlate`; card and strip use it
- [x] 3.2 `StatusBlock` takes a narrow status shape; card unchanged in output
- [x] 3.3 `InfoHeader` opens on the cover with plate, ring and status block, fed by the page's own status and clock
- [x] 3.4 `MeterTrack` from `CapacityMeter`; `DisciplinesInfo` draws it under each row

## 4. Preview

- [x] 4.1 `SetupPreview` root carries `data-skin="night"`; move the full-height paint off the skin block onto the layout roots

## 5. Finish

- [x] 5.1 Tests: detail cover tint and ring by status, meter under a detail discipline, preview panel carries the skin; update tests asserting the old header
- [x] 5.2 Visual pass: list → detail → entrants → register, phone width, console Setup with preview
- [x] 5.3 `npm run typecheck`, `npm run check`, `npm test`; ruff, basedpyright
