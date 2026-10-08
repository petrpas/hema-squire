## Context

`hema-agent` (`src/pre_tournament/reg_agent/step_typst.py`) renders discipline
rosters in three steps:
1. It reads the exported Google Sheet by column position.
2. It splices the rows into `templates/disciplines.typ` as a Typst tuple
   literal, replacing `{{data}}`, `{{last_in}}` and `{{tournament_name}} ---
   {{discipline_name}}`.
3. It compiles with the `typst` Python package against
   `src/shared/typst/fonts/` (GFS Neohellenic, SIL OFL).

The template sets:
- an auto-height page, 48em wide, with 0.7cm margins;
- a bold title;
- a seven-column table: No., Fencer, Nat., Club, HRID, RANK, Paid;
- a heavier rule under row `last_in`, which marks the last fencer in.

In Squire, a discipline tab's displayed rows are computed in the frontend.
`ExportTables` applies:
- `activeOnly` (the switch);
- `rosterOrder(listed, slug, capacity, lineKind, seeded)`, which gives the
  seeding order and places the capacity line (`line.after`);

and `ExportGrid` draws the line. The copy action already serializes exactly
those rows.

## Goals / Non-Goals

**Goals:**
- One click from a discipline tab to a PDF or a PNG of the roster, matching
  the tab row for row.
- Keep the owner's established look: the template, the font and the rule
  under the last fencer in.
- Bring the rail card's copy into the icon-with-hint idiom the export card
  already uses.

**Non-Goals:**
- Fencers, item and Summary rosters, and team rosters. The owner said "zatím
  jen soupiska disciplín".
- Pools, eliminations and declarations. `hema-agent` keeps them.
- Designing the printed page to the console's Bureau 1952 tokens. The PDF is
  the owner's established artifact, and the UI prohibitions in CLAUDE.md
  govern the console, not this document.

## Decisions

### D1. The frontend sends the rows it shows; the backend only typesets
`POST /tournaments/{slug}/export/roster.{pdf|png}` takes a body of:
- `discipline`: the slug;
- `rows`: the displayed rows, as the cells No., Fencer, Nat., Club, HRID, Rank
  and Paid, already formatted;
- `line_after`: how many rows stand above the capacity line (the tab's
  `line.after`), or null;
- `english`.

This is the copy action's data, so the printout cannot drift from the tab.
Order, switch, seeding and a rating the organizer corrected all stay
frontend-only facts.

The backend:
- checks console access and publication, as `/export/summary` does;
- checks that `discipline` is one of the tournament's individual disciplines,
  which gives the title its name;
- caps `rows` at 1000.

*Alternative:* the backend recomputes the order, by porting `rosterOrder` to
Python. Rejected. Two implementations of the seeding order would eventually
disagree, and the printout is supposed to be the tab.

### D2. The template reads data, never spliced source
The template is vendored as `app/typst/templates/discipline_roster.typ`. It
differs from `disciplines.typ` in one respect: instead of `{{…}}`
placeholders, it reads `sys.inputs`, for example
`#let input = json(bytes(sys.inputs.roster))`. The input carries:
- `title`;
- `headers`;
- `rows`;
- `last_in`.

`rosterprint.render` calls `typst.compile(template_path, format=…,
font_paths=[fonts], ignore_system_fonts=True, sys_inputs={"roster":
json.dumps(…)})`. Fencer names and clubs never become Typst syntax, so a club
called `#import` prints as text.

*Alternative:* `hema-agent`'s `_escape_typst` splice. Rejected, because escaping
by hand is the class of bug this removes.

The layout is otherwise unchanged:
- page width, margins and font size;
- column widths and alignments;
- the title rule, "`<tournament>` — `<discipline>`" in bold 1.4em;
- the strokes: an outer frame, the header box, verticals between columns, and
  a horizontal rule only under the header, under row `last_in` and under the
  last row.

`last_in` is `line_after` (the 1-based row the rule falls under), or the row count where there is no
line, as `hema-agent` does when no limit is set.

### D3. Fonts and output
The four GFS Neohellenic TTFs and `OFL.txt` are copied into
`app/typst/fonts/`. `ignore_system_fonts=True` makes the output the same on a
laptop and in the container.

| | PNG | PDF |
|---|---|---|
| Resolution | `ppi=200` (the binding's default is 144), crisp enough for an Instagram post at 48em width | — |
| Pages | Auto-height gives one page whatever the length. Should the binding still return several, only the first is sent and the response says so in a header. This is not expected with `height: auto`. | One page, same layout |

The filename is `<tournament-slug>-<discipline-slug>.pdf|png`, sent with
`Content-Disposition: attachment`.

### D4. Language
The headers and Paid's `Yes`/`No` come from the locale catalog
(`export.roster.*`), in the console's language, or in English with the English
tick. The default Czech headers are `Č.`, `Šermíř`, `Nár.`, `Klub`, `HRID`,
`Rank`, `Zaplaceno`. The title uses the discipline's name as the organizer wrote
it.

### D5. The rail card's actions become an icon row
`TableOperations` renders an `export-actions` row:
- **copy**: `IconCopy`, with the hint "Zkopíruje tabulku do schránky, …";
- on a discipline tab, the **ratings refresh** (`IconRefresh`), whose hint
  carries the statement that it refreshes the whole tournament;
- on a discipline tab, **PDF** (`IconFileTypePdf`);
- on a discipline tab, **PNG** (`IconFileTypePng`).

Each action is wrapped in `HintedAction`, with its word as the visually hidden
accessible name, exactly as `ExportPanel` does. Tabler icons are outline icons,
so the no-filled-icons rule holds.

The owner decided on 2026-10-08, after implementation, three refinements:
- the ratings refresh joins the row, between the copy and the PDF, in place of
  its text button and standing statement;
- the English tick moves out of the export card to the rail above both cards,
  since it governs the copy, the printouts and the spreadsheet alike;
- the export card is headed "Exportovat vše" / "Export all".

The copy outcome ("Zkopírováno N řádků") stays as a rail hint below the row. A
failed render states its error there too. While a render is in flight its
button is disabled, with no spinner, as the export card does.

## Risks / Trade-offs

- **[A client-supplied table is typeset by the server.]** An organizer could
  post any text. → It is their own tournament's console, behind the same access
  check as the other tables. `sys_inputs` makes the text inert. The row cap
  bounds the work.
- **[Typst compile time on a 2-vCPU host.]** A 60-row roster compiles in well
  under a second locally in `hema-agent`. → The render is synchronous. Nothing
  is cached.
- **[A wheel the deploy image cannot install.]** → Task 1.1 runs
  `uv sync --frozen` in the Docker build before anything else is built on it.
- **[The template diverges from `hema-agent`'s copy.]** → Accepted. Squire's
  copy is now the authoritative one for rosters, and the vendored file's header
  comment names its origin.

## Open Questions

None. The owner decided on 2026-10-08:
- the Paid column stays, as in the template;
- the rows are as the tab shows them;
- the language follows the English tick.
