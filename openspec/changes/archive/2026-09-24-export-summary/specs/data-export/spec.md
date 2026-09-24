## MODIFIED Requirements

### Requirement: Google Sheets export mirrors the export tables
The Google Sheets export SHALL write one worksheet per export table: a `Fencers`
worksheet, one worksheet per individual discipline named for the discipline's
slug, and one worksheet per extra-item category the tournament offers, named for
the category, and a `Summary` worksheet. Each worksheet SHALL carry its table's
columns and its table's order, as `export-tables` and `export-summary` fix them.
Worksheet names SHALL be the same in every locale, since the export finds an
existing worksheet by its name.

Every worksheet but `Summary` SHALL open, as every tab but Summary does, with a
position column headed `#`.
No worksheet SHALL carry a blank column left for numbering by hand. The position SHALL number the
worksheet's rows 1 to n from the top as the worksheet stands after the export,
rewritten on every export. Because a re-export keeps existing rows where they
stand and appends new ones, the position numbers the sheet, not the console:
after the console's order has moved, the two may differ, and the sheet's
numbering still runs unbroken down the sheet.

The position, the HEMA Ratings identifier, the rating, the rank and the
summary's paid and unpaid counts SHALL be written to the worksheet as numbers, not as text, whatever locale the
spreadsheet is set to; a cell of those columns holding no number SHALL be
written as it stands.

Slugs are unique within a tournament, so several disciplines classified alike
produce several distinct worksheets. A worksheet whose discipline has no HEMA
Ratings counterpart SHALL still be produced, with its rating and rank columns
empty.

The rating written SHALL be the rating the console states — the fetched value as
corrected by the organizer — so that re-exporting never restores a stale fetched
value over a typed one.

The fetched value SHALL be the one for the HR profile the row is bound to as the
console states it, including a binding an organizer's match resolution, merge or
substitution made. A correction the organizer typed SHALL outlive a later change
of that binding: it belongs to the row, not to the profile.

Teams SHALL NOT change this format. A roster member SHALL NOT appear in the
`Fencers` worksheet — they hold no registration, so they have no row — and a team
discipline SHALL NOT produce a worksheet. How team participation reaches
in-tournament tooling remains out of scope here.

The export SHALL write English column headers and English yes/no values when the
organizer has asked for an English export, and the organizer's own language
otherwise.

#### Scenario: A rebound row carries its new profile's rating
- **WHEN** the organizer resolves a fencer's match to another HR profile and takes a snapshot
- **THEN** the worksheet carries that profile's rating and rank, and a rating the organizer had typed for the fencer still stands

#### Scenario: The position numbers the sheet as it stands
- **WHEN** the organizer re-exports after one fencer was deleted and another registered
- **THEN** the deleted fencer's row is gone, the new fencer's row is appended, and the `#` column reads 1 to n down the worksheet with no gap

#### Scenario: A worksheet per tab
- **WHEN** a tournament offering two individual disciplines, a rental item and a merch item is exported to Sheets
- **THEN** six worksheets are written — Fencers, the two discipline slugs, Rentals, Merch and Summary — each carrying its table's columns

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
- **THEN** the worksheets are exactly those the same tournament would produce without teams, no roster member appears in the Fencers worksheet, and the Summary worksheet has no line for a team discipline

#### Scenario: An English sheet from a Czech console
- **WHEN** a Czech-speaking organizer ticks the English export and writes to Sheets
- **THEN** the worksheets carry English headers and Yes/No in the paid column, and the Summary worksheet's queue and unanswered lines read in English

### Requirement: Repeat-export preservation semantics
Re-exporting to an existing sheet SHALL always refresh the position, rating and rank columns of a table's worksheet, and SHALL write its other cells only when blank or unchanged, preserving downstream manual work.

The `Summary` worksheet SHALL be written whole on every export, replacing what it
held. It is a report of counts, not a list staff work through. It has no row
identity a merge could keep a cell by, and a preserved count would be a stale one.
Anything written into it by hand SHALL NOT survive the next export.

These semantics SHALL survive the change of worksheet shape. Existing cells are
addressed by their header name, so a column that remains keeps its contents, a
column that goes is dropped, and a column that arrives is filled. A sheet written
while the format carried `Reg.` and `No.` columns loses them on its next export,
with whatever downstream staff had written into them.

What the rating column refreshes to SHALL be the rating the console states,
including an organizer's correction. A correction is therefore never overwritten
by a re-export, and never preserved as a stale cell either: it is written afresh
every time, because it is what the tournament currently holds.

#### Scenario: Manual work survives
- **WHEN** the organizer re-exports after downstream staff corrected a fencer's club in the sheet
- **THEN** the correction is preserved while ratings refresh

#### Scenario: A sheet in an older format keeps what remains
- **WHEN** the organizer re-exports to a spreadsheet written in an older format
- **THEN** cells of the columns that remain keep their contents, the columns the current format drops are gone, and the columns it adds are filled

#### Scenario: The summary is rewritten
- **WHEN** downstream staff typed a note into the Summary worksheet and the organizer re-exports after two more shirts were ordered
- **THEN** the Summary worksheet states the new counts and the note is gone

#### Scenario: A correction is rewritten, not preserved
- **WHEN** the organizer corrects a rating and re-exports twice
- **THEN** the rating column carries the correction both times
