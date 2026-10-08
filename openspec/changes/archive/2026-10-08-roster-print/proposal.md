## Why

Before a tournament the organizer posts each discipline's roster on social
media. Today they do it outside Squire: `hema-agent` reads the exported Google
Sheet and typesets `disciplines.typ` with Typst into a PNG. That needs a
finished spreadsheet, a second tool, and a reader that guesses column positions.
Squire already holds the roster in the order the organizer settled on, so it
can typeset it directly.

## What Changes

- **PDF and PNG on a discipline tab.** A discipline tab of the Export phase
  gains two actions in its rail card, **PDF** and **PNG**. Each downloads the
  roster typeset by Typst from the `disciplines.typ` template, in the GFS
  Neohellenic font, as `hema-agent` does today.
- **What is printed is what the tab shows.** The roster carries:
  - the same rows, order, active-only filter and seeding order as the tab;
  - the capacity line, drawn as the template's rule after the last fencer in;
  - the columns No., Fencer, Nat., Club, HRID, Rank and Paid;
  - headers and the Yes/No in the console's language, or in English where the
    English tick is on.
- **The copy action becomes an icon.** The rail card's text button "copy table"
  becomes a copy icon. Like the PDF and PNG actions, it carries a floating hint
  (`HintedAction`), in the same icon row the export card already uses.
- **Vendored files.** The template and the fonts (SIL OFL) are copied into
  Squire. Squire then depends on neither `hema-agent` nor its file layout. The
  template reads its rows as data, not as text spliced into its source.

## Capabilities

### New Capabilities
- `roster-print`: typesetting a discipline roster to PDF and PNG. Covers which
  rows, order and columns it prints, where the capacity rule falls, the title,
  the language, the font and template, and how the file is named and offered.

### Modified Capabilities
- `export-tables`: in the rail card, the copy and the ratings refresh become
  icons with hints, and a discipline tab gains the PDF and PNG actions beside
  them. The English tick moves above both rail cards.
- `data-export`: the export card is headed "Export all" and no longer holds the
  English tick.
- `export-revenue`: Include finances sits under the export card's actions,
  no longer under the English tick.

## Impact

- **Backend.**
  - New dependency `typst` (Python binding; abi3 wheels, so it runs on
    3.14), declared in `pyproject.toml`.
  - New `app/rosterprint.py` and new
    `POST /tournaments/{slug}/export/roster.{pdf,png}`.
  - New files `app/typst/templates/discipline_roster.typ` and
    `app/typst/fonts/` (4 TTFs + `OFL.txt`).
- **Frontend.**
  - `TableOperations`: an icon row of copy, PDF and PNG, each wrapped in
    `HintedAction`.
  - `api.ts`: download helpers.
  - New locale keys.
- **Deploy.** The fonts ship inside the backend image. Nothing is installed
  system-wide, because the binding takes a font path.
- **Overlap with `export-revenue`.** That change also modified the export-tables
  rail requirement; it archived first, and this change's delta is rebased on it.
