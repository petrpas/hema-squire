## MODIFIED Requirements

### Requirement: Google Sheets export mirrors the export tables
The Google Sheets export SHALL write one worksheet per export table: a `Fencers`
worksheet, one worksheet per discipline, individual and team alike, named for the
discipline's slug, and one worksheet per extra-item category the tournament
offers, named for the category, a `Summary` worksheet, and — only where the
organizer ticked Include finances for that export (`export-revenue`) — a `Revenue`
worksheet. An export without the tick SHALL leave a `Revenue` worksheet the
spreadsheet already holds untouched. Each worksheet
SHALL carry its table's columns and its table's order, as `export-tables`,
`export-summary` and `export-revenue` fix them, except a team discipline's, whose
shape `A team discipline's worksheet is flat` fixes.
Worksheet names SHALL be the same in every locale, since the export finds an
existing worksheet by its name.

Every worksheet but `Summary` and `Revenue` SHALL open, as every tab but Summary
and Revenue does, with a position column headed `Poř.` (`Pos.` in English). The
mark `#` is reserved for the fencer's fixed number (`etl-console`) and SHALL NOT head
a position.
No worksheet SHALL carry a blank column left for numbering by hand. On every
worksheet but a team discipline's, the position SHALL number the
worksheet's rows 1 to n from the top as the worksheet stands after the export,
rewritten on every export. Because a re-export keeps existing rows where they
stand and appends new ones, the position numbers the sheet, not the console:
after the console's order has moved, the two may differ, and the sheet's
numbering still runs unbroken down the sheet.

The position, the HEMA Ratings identifier, the rating, the rank and the
summary's paid and unpaid counts, and the revenue's prices, counts and amounts,
SHALL be written to the worksheet as numbers, not as text, whatever locale the
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

A roster member SHALL NOT appear in the `Fencers` worksheet — they hold no
registration, so they have no row there. They appear only in their team
discipline's worksheet.

The export SHALL write English column headers and English yes/no values when the
organizer has asked for an English export, and the organizer's own language
otherwise.

#### Scenario: A rebound row carries its new profile's rating
- **WHEN** the organizer resolves a fencer's match to another HR profile and takes a snapshot
- **THEN** the worksheet carries that profile's rating and rank, and a rating the organizer had typed for the fencer still stands

#### Scenario: The position numbers the sheet as it stands
- **WHEN** the organizer re-exports after one fencer was deleted and another registered
- **THEN** the deleted fencer's row is gone, the new fencer's row is appended, and the position column reads 1 to n down the worksheet with no gap

#### Scenario: A worksheet per tab
- **WHEN** a tournament offering two individual disciplines, a rental item and a merch item is exported to Sheets
- **THEN** six worksheets are written — Fencers, the two discipline slugs, Rentals, Merch and Summary — each carrying its table's columns, and with Include finances ticked a seventh, Revenue

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

#### Scenario: A team discipline has its worksheet
- **WHEN** a tournament with an individual and a team longsword discipline, slugs `LS` and `LS-T`, is exported to Sheets
- **THEN** a worksheet `LS-T` is written listing its teams' fighters, no roster member appears in the Fencers worksheet, and the Summary worksheet has no line for the team discipline

#### Scenario: An English sheet from a Czech console
- **WHEN** a Czech-speaking organizer ticks the English export and writes to Sheets
- **THEN** the worksheets carry English headers and Yes/No in the paid column, and the Summary worksheet's queue and unanswered lines read in English

### Requirement: Repeat-export preservation semantics
Re-exporting to an existing sheet SHALL always refresh the position, rating and rank columns of a table's worksheet, and SHALL write its other cells only when blank or unchanged, preserving downstream manual work. On a team discipline's worksheet the team's name and paid SHALL be refreshed too, since they identify and qualify the team rather than a fighter.

A row SHALL be recognised across exports by its identity: on a team discipline's
worksheet by its team's name together with the fighter — the fighter's HEMA
Ratings identifier where it has one, else the fighter's name, folded — and on
every other worksheet by the fighter alone in the same way. A fighter named on
two teams is therefore two rows, each kept under its own team.

The `Summary` and `Revenue` worksheets SHALL be written whole on every export,
replacing what they held. Each is a report of figures, not a list staff work
through. Neither has a row
identity a merge could keep a cell by, and a preserved figure would be a stale
one. Anything written into either by hand SHALL NOT survive the next export.

These semantics SHALL survive the change of worksheet shape. Existing cells are
addressed by their header name, so a column that remains keeps its contents, a
column that goes is dropped, and a column that arrives is filled. A sheet written
while the format carried `Reg.` and `No.` columns loses them on its next export,
with whatever downstream staff had written into them.

A team discipline's worksheet still in the shape that listed team rows with their
fighters beneath them — recognised by carrying no team column — SHALL be written
whole on its next export, as the Summary is, since none of its rows can be
recognised by the team they belong to. What staff had written into it is lost
that once; every later export merges as above.

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

#### Scenario: The revenue is rewritten
- **WHEN** downstream staff typed a note into the Revenue worksheet and the organizer re-exports with Include finances ticked after a registration was settled
- **THEN** the Revenue worksheet states the new amounts and the note is gone

#### Scenario: A correction is rewritten, not preserved
- **WHEN** the organizer corrects a rating and re-exports twice
- **THEN** the rating column carries the correction both times

#### Scenario: A team worksheet keeps its rows on a re-export
- **WHEN** staff wrote a note into the club cell of a Wolves fighter's row and the organizer exports the team discipline again unchanged
- **THEN** every row stands where it stood, the note is kept, and the Wolves rows still lie together

#### Scenario: A fighter on two teams keeps both rows
- **WHEN** a fighter bound to HEMA Ratings profile 7 is named on both Wolves and Bears and the organizer exports twice
- **THEN** the worksheet holds a Wolves row and a Bears row for that fighter after each export

#### Scenario: An old-shape team worksheet is rewritten once
- **WHEN** the spreadsheet holds a team discipline's worksheet with team rows and fighter rows and no team column, and the organizer exports
- **THEN** the worksheet is replaced by the flat shape, and a note staff had typed into it is gone

## ADDED Requirements

### Requirement: A team discipline's worksheet is flat
A team discipline's worksheet SHALL carry the columns position, team, name,
nationality, club, HEMA Ratings identifier, rating, rank and paid, and SHALL list
one row per fighter on a team's roster, in the tab's order of teams and each
team's roster order. A team with no fighter on its roster SHALL be one row stating
its team cells, with the fighter cells empty.

Every row SHALL state its team's number as the position, as the tab numbers teams,
and its team's name and paid. These three SHALL be repeated on every row of the
team, so the worksheet filters and sorts without parting a fighter from their
team. Unlike every other worksheet, its position therefore numbers teams, not the
worksheet's rows, and is refreshed from the console on every export.

The worksheet SHALL NOT carry the fencer who entered a team, nor the team's member
count against the discipline's bounds.

The team header SHALL read `Tým` (`Team` in English).

#### Scenario: Team cells on every row
- **WHEN** a team discipline listing Wolves with four fighters and Bears with three is exported
- **THEN** its worksheet holds seven rows, four stating position 1, Wolves and Wolves' paid, three stating 2, Bears and Bears' paid

#### Scenario: An empty team is one row
- **WHEN** a seated team has no fighter on its roster yet and the tournament is exported
- **THEN** the team's worksheet holds one row for it with its position, name and paid and empty fighter cells

#### Scenario: No console facts in the sheet
- **WHEN** a team entered by Petr Novák is exported
- **THEN** no cell of the worksheet states Petr Novák as its entering fencer or its member count against the bounds
