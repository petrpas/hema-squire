## REMOVED Requirements

### Requirement: Google Sheets export in the legacy format
**Reason**: The exported spreadsheet becomes the organizer's own working
document, mirroring the export tables they read in the console, rather than a
feed shaped for the v1 in-tournament tooling. Keeping both shapes in one
spreadsheet was considered and rejected: two worksheets stating overlapping
things is a spreadsheet nobody can be told the truth about. The requirement is
replaced by **Google Sheets export mirrors the export tables** below.

**Migration**: This is a breaking change for v1 in-tournament tooling reading an
exported spreadsheet. The destination is the organizer's own
`output_sheet_url`, so the blast radius is one spreadsheet per tournament; a
tournament still feeding v1 tooling should point Squire at a fresh spreadsheet
and keep the old one, which Squire no longer writes to, as it stands. The
`Reg.` and `No.` columns downstream staff fill by hand survive the format change
in place: the merge addresses existing cells by their header name, so a column
that stays keeps its contents.

## ADDED Requirements

### Requirement: Google Sheets export mirrors the export tables
The Google Sheets export SHALL write one worksheet per export table: a `Fencers`
worksheet, one worksheet per individual discipline named for the discipline's
slug, and one worksheet per extra-item category the tournament offers, named for
the category. Each worksheet SHALL carry its table's columns and its table's
order, as `export-tables` fixes them.

Slugs are unique within a tournament, so several disciplines classified alike
produce several distinct worksheets. A worksheet whose discipline has no HEMA
Ratings counterpart SHALL still be produced, with its rating and rank columns
empty.

The rating written SHALL be the rating the console states — the fetched value as
corrected by the organizer — so that re-exporting never restores a stale fetched
value over a typed one.

Teams SHALL NOT change this format. A roster member SHALL NOT appear in the
`Fencers` worksheet — they hold no registration, so they have no row — and a team
discipline SHALL NOT produce a worksheet. How team participation reaches
in-tournament tooling remains out of scope here.

The export SHALL write English column headers and English yes/no values when the
organizer has asked for an English export, and the organizer's own language
otherwise.

#### Scenario: A worksheet per tab
- **WHEN** a tournament offering two individual disciplines, a rental item and a merch item is exported to Sheets
- **THEN** five worksheets are written — Fencers, the two discipline slugs, Rentals and Merch — each carrying its table's columns

#### Scenario: Tiers produce separate worksheets
- **WHEN** a tournament offering two longsword disciplines is exported to Sheets
- **THEN** two worksheets are produced, named for the two slugs, each listing only its own entrants

#### Scenario: Unrated discipline still exported
- **WHEN** a tournament offering a discipline whose weapon is outside the taxonomy is exported to Sheets
- **THEN** that discipline's worksheet is produced with its entrants listed and its rating and rank columns empty

#### Scenario: A category the tournament does not offer produces no worksheet
- **WHEN** the tournament sells no merch
- **THEN** no merch worksheet is written

#### Scenario: A corrected rating is what the sheet carries
- **WHEN** the organizer has corrected a fencer's rating and exports to Sheets
- **THEN** the worksheet's rating column carries the corrected value

#### Scenario: Teams absent from the sheet
- **WHEN** a tournament with team disciplines and rosters is exported to Sheets
- **THEN** the worksheets are exactly those the same tournament would produce without teams, and no roster member appears in the Fencers worksheet

#### Scenario: An English sheet from a Czech console
- **WHEN** a Czech-speaking organizer ticks the English export and writes to Sheets
- **THEN** the worksheets carry English headers and Yes/No in the paid column

## MODIFIED Requirements

### Requirement: Repeat-export preservation semantics
Re-exporting to an existing sheet SHALL leave manually managed columns (Reg., No.) untouched, SHALL always refresh the rating and rank columns, and SHALL write other cells only when blank or unchanged, preserving downstream manual work.

These semantics SHALL survive the change of worksheet shape. Existing cells are
addressed by their header name, so a column that remains keeps its contents, a
column that goes is dropped, and a column that arrives is filled — and the `Reg.`
and `No.` columns downstream staff fill by hand are preserved across the format
change itself, not only across re-exports of one format.

What the rating column refreshes to SHALL be the rating the console states,
including an organizer's correction. A correction is therefore never overwritten
by a re-export, and never preserved as a stale cell either: it is written afresh
every time, because it is what the tournament currently holds.

#### Scenario: Manual numbering survives
- **WHEN** the organizer re-exports after downstream staff filled the No. column
- **THEN** the numbering is preserved while ratings refresh

#### Scenario: Manual numbering survives the format change
- **WHEN** the organizer re-exports to a spreadsheet written in the old format whose No. column downstream staff had filled
- **THEN** the numbering is preserved, columns the new format drops are gone, and columns it adds are filled

#### Scenario: A correction is rewritten, not preserved
- **WHEN** the organizer corrects a rating and re-exports twice
- **THEN** the rating column carries the correction both times
