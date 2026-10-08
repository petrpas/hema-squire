## 1. Dependency and vendored files

- [x] 1.1 Add `typst` to `backend/pyproject.toml`, with a comment naming `app/rosterprint.py` as its importer. Then run `uv lock`, `uv sync`, and `docker build` of the backend stage (`uv sync --frozen --no-dev`) on 3.14. `uv run deptry .` must stay clean.
- [x] 1.2 Copy the four GFS Neohellenic TTFs and `OFL.txt` from `hema-agent/src/shared/typst/fonts/` to `backend/app/typst/fonts/`. Check that the Dockerfile's backend stage copies `app/` with them, and that `.dockerignore` does not exclude `*.ttf`.
- [x] 1.3 Write `backend/app/typst/templates/discipline_roster.typ` from `disciplines.typ` (D2). Its data comes from `json(bytes(sys.inputs.roster))` (title, headers, rows, last_in), and its layout is otherwise unchanged. Add a header comment naming the origin.

## 2. Rendering

- [x] 2.1 `app/rosterprint.py`: `render(title, headers, rows, last_in, fmt) -> bytes`. It calls `typst.compile` with `font_paths=[fonts]`, `ignore_system_fonts=True`, `sys_inputs`, and `ppi=200` for PNG. Confirm against the installed binding that it accepts these keyword names. It returns the first page for PNG.
- [x] 2.2 `POST /tournaments/{slug}/export/roster.{pdf,png}` in `routers/export_api.py`:
  - guards: console access and publication;
  - `discipline` must be an individual discipline of the tournament, else 404;
  - `rows` are capped at 1000, else 422;
  - headers and the title come from the locale catalog (`export.roster.*`, cs and en);
  - the response carries `Content-Disposition: attachment; filename=<slug>-<discipline>.<ext>`.

  Add the schemas in `schemas.py`.
- [x] 2.3 `tests/test_roster_print.py`, covering behaviour only:
  - the PDF starts with `%PDF` and the PNG with the PNG signature;
  - a club `#import "x"` renders without error;
  - 60 rows make one PNG;
  - a team discipline is refused;
  - a foreign organizer is refused;
  - the filename;
  - English headers when asked.

  Test-only helper: text extraction from the PDF, if `pypdf` is already available, to assert the Czech/English headers and the injected club text. Otherwise assert only through the render not failing.
- [x] 2.4 `uv run ruff check .` and `uv run basedpyright` are clean. Run the scoped pytest.

## 3. Frontend

- [x] 3.1 `api.ts`: `exportRoster(slug, format, body)`, returning a Blob that is downloaded the way `ExportPanel.downloadJson` does.
- [x] 3.2 `ExportTables.tsx`: build the roster body from the rows the discipline tab displays:
  - the same `activeOnly` + `rosterOrder` result the copy uses;
  - the cells No., Fencer, Nat., Club, HRID, Rank, Paid;
  - `line_after`;
  - `english`.

  Pass `onPrint(format)` to `TableOperations` on discipline tabs only.
- [x] 3.3 `TableOperations.tsx`: replace the copy text button with an `export-actions` icon row:
  - `IconCopy`;
  - on a discipline tab, `IconFileTypePdf` and `IconFileTypePng`.

  Each action is wrapped in `HintedAction`, with a visually hidden name. A button is disabled while its render runs, with no spinner. The outcome or error is stated as a rail hint.
- [x] 3.4 Locale keys, cs and en: `export.hints.copy`, `export.hints.pdf`, `export.hints.png`, `export.pdf`, `export.png`, and the roster headers. `locale-parity.test.ts` passes.
- [x] 3.5 Tests:
  - the copy is an icon with a hint on every tab;
  - PDF and PNG appear only on a discipline tab;
  - the roster body follows the switch and the seeding order and carries `line_after`.

  Update the existing assertions that looked for the copy button's text.
- [x] 3.6 `npm run typecheck`, `npm run check` and `npx vitest run` are clean.

## 4. Check and specs

- [x] 4.1 In the running app, download the PDF and PNG of a discipline with a queue. Check:
  - the rule under the last fencer in;
  - the font;
  - Czech and English headers;
  - the hints on the three icons.

  Compare by eye against a `hema-agent` render of the same roster.
- [x] 4.2 Rebase the `export-tables` delta onto `export-revenue`, which archived first. Done with the owner's refinements: the refresh as an icon, the English tick above both cards, the card renamed. `data-export` and `export-revenue` gain deltas for the last two.
