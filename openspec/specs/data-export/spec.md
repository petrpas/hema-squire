# data-export Specification

## Purpose
Export tournament data in the canonical JSON format and as a Google Sheets workbook mirroring the console's export tables.
## Requirements
### Requirement: Exporting waits for publication
Every export SHALL be refused on an unpublished tournament, with a stated reason naming
publication. This covers the worksheet export and the canonical JSON document alike.

The export reads and writes nothing, so the rule that gates the console's data work
does not reach it on its own terms. It is gated because it is the one read whose
product leaves the console: a worksheet goes to the check-in desk, the referees and the
scorekeepers, and a canonical document is a tournament's whole state handed to
somebody. From a tournament nobody can enter, holding nobody, such a document states a
roster of nobody to a reader with no way to know that.

A draft has nothing to export in any case — it can hold no participant
(`tournament-publication`) — so what the refusal prevents is not a wrong answer but a
confident empty one.

#### Scenario: A draft is not exported to a worksheet
- **WHEN** an organizer exports a draft to Sheets
- **THEN** the export is refused with a reason naming publication, and no worksheet is created

#### Scenario: A draft produces no canonical document
- **WHEN** an organizer asks a draft for its canonical JSON document
- **THEN** it is refused with a reason naming publication

#### Scenario: Publication opens the export
- **WHEN** the tournament is published and the export asked for again
- **THEN** it runs as it does for any published tournament

### Requirement: Canonical JSON export
The full tournament dataset SHALL be exportable in the application's own versioned JSON format, sufficient to reconstruct the fencer table, registrations, and payment states.

A discipline SHALL be exported with its slug, its name, its weapon, its gender, and its material, and every reference to a discipline elsewhere in the document — an individual entry, a team — SHALL identify it by slug. The document SHALL NOT carry a discipline's derived taxonomy code, which is reconstructible from the exported classification. A restore SHALL resolve discipline references by slug, and SHALL reject a document referencing a slug it does not define rather than restoring a partial registration.

The document SHALL additionally carry every team and every roster member, so that a restore reconstructs teams and rosters exactly as they stood: each team with its discipline, its entering fencer's registration, its name, its waitlisted state and its entry order, and each member with its position, name, and — where bound — HEMA Ratings identifier, club, and nationality. A roster member SHALL be exported as the plain record it is, never as a fencer account, and restoring one SHALL NOT create an account. Discipline kind and roster bounds, and the tournament's team composition deadline, SHALL be exported with their owners.

The document version SHALL be raised for this addition. Documents produced before it SHALL remain loadable: a discipline carrying a code and no classification SHALL restore with that code as its slug and its classification parsed from it, which is exactly what the migration does to stored rows.

#### Scenario: Round-trip fidelity
- **WHEN** a tournament is exported and re-imported into an empty deployment
- **THEN** the reconstructed fencer table matches the original

#### Scenario: Tiers round-trip
- **WHEN** a tournament offering two longsword disciplines, with fencers entered in each, is exported and re-imported into an empty deployment
- **THEN** both disciplines are reconstructed under their own slugs, names, capacities and fees, and every fencer is restored into the one they had entered

#### Scenario: Individual and team in one weapon round-trip
- **WHEN** a tournament offering both an individual and a team longsword discipline is exported and re-imported
- **THEN** both are reconstructed with their own slugs and kinds, and no entry is attached to the wrong one

#### Scenario: Classification round-trips
- **WHEN** a tournament offering a discipline whose weapon is outside the taxonomy is exported and re-imported
- **THEN** that discipline is restored with its weapon, gender, material and name intact

#### Scenario: Dangling slug rejected
- **WHEN** a document references a discipline slug it does not define
- **THEN** the restore is rejected with the offending slug named, and no partial registration is created

#### Scenario: Teams and rosters round-trip
- **WHEN** a tournament with a team discipline, four teams (one waitlisted) and their rosters is exported and re-imported into an empty deployment
- **THEN** every team is reconstructed with its name, discipline, entering fencer, waitlisted state and entry order, and every roster with its members in order and their HEMA Ratings bindings intact

#### Scenario: Unbound members survive
- **WHEN** an exported roster contains members with no HEMA Ratings identifier
- **THEN** they are restored by name with no identifier and no account is created for them

#### Scenario: Older document still loads
- **WHEN** a document produced before disciplines carried a classification is restored
- **THEN** it loads, each discipline taking its old code as its slug and its classification parsed from that code, every discipline individual, and the deployment carries no teams and no composition deadline

### Requirement: Restoring a document is Admin work
Restoring a tournament from a canonical JSON document SHALL be open to an Admin and the
deployment Owner only, and refused to every other account with a stated reason naming the
role. A restore creates a tournament and rejoins accounts already present by their
address, which is recovery work across the deployment rather than an organizer's work on
one tournament.

A restore SHALL read from the document only the fields an export writes. Any other key —
on the tournament, such as an owner, a bank feed token or a publication moment, or on an
account, such as a role or a password — SHALL be ignored: an account a restore creates
carries the Fencer role and no password, and a restored tournament lands as a draft.

#### Scenario: An organizer cannot restore
- **WHEN** an account with the Fencer or the Organizer role posts a document to restore
- **THEN** the restore is refused naming the role, and no tournament is created

#### Scenario: A document cannot grant a role
- **WHEN** an Admin restores a document whose account record carries a role and a password, and whose tournament carries an owner, a feed token and a publication moment
- **THEN** the account is created as a Fencer with no password, and the tournament has no owner, no feed token and is a draft

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

A roster member SHALL appear in the `Fencers` worksheet as the Fencers tab lists
them — that worksheet is the tournament's start list (`etl-console`) — and in its
team discipline's worksheet under its team.

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
- **THEN** a worksheet `LS-T` is written listing its teams' fighters, the roster members stand in the Fencers worksheet as the Fencers tab lists them, and the Summary worksheet has no line for the team discipline

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

### Requirement: Export scope
Deleted (withdrawn) rows SHALL be excluded from exports. Payment state SHALL be exported in the Paid column.

#### Scenario: Withdrawn fencer
- **WHEN** a row was deleted in the console before export
- **THEN** the fencer appears in no exported worksheet

### Requirement: Hand-recorded payments and waivers survive an export
The canonical JSON document SHALL carry every payment an organizer recorded by hand — its registration, amount, currency, the date the money arrived, how it arrived, the note, who recorded it and when — and SHALL carry both payment journals: every credit with its amount, currency, arrival day, origin, the source row that carried it and its reversal where it has one, and every waiver with its reason, who granted it and who revoked it.

Both are load-bearing. What a registration has been credited is the sum of its live credits, and whether it is settled may stand on nothing but a person's word; a document that carried the consequence without the cause would restore a payment state that could not be audited, corrected or reversed. A restore SHALL reconstruct the journals as they stood and SHALL NOT replay a recorded payment as a fresh credit on top of the credit journal that already carries it.

A credit SHALL name the row that carried it, and SHALL be restored only where that row travelled in the same document. A credit whose source did not travel SHALL NOT be restored: a credit that cannot say where it came from is the one thing the journal exists to prevent.

Removed records SHALL NOT be exported: what the document reconstructs is the state, and a payment that has been reversed contributes none.

The document version SHALL be raised for this addition. A document produced before it SHALL remain loadable where it carries no payment state — restoring with no credit, no waiver and no hand-recorded payment, which is what those tournaments held. A document produced before it that **does** carry a credited amount or a settled-by-hand mark SHALL be refused, naming that as the reason. Such a document records a total whose composition was never kept — which payment, from where, arriving when — and there is no honest way to reconstruct the credits it was the sum of; restoring it with the payments silently dropped would be worse than refusing it.

#### Scenario: Cash payment round-trips
- **WHEN** a tournament holding a registration settled by a recorded cash payment is exported and re-imported into an empty deployment
- **THEN** the registration is restored paid with the same credit against it, and the recorded payment is restored beside it with its date, method, note and recorder

#### Scenario: Waiver round-trips
- **WHEN** a tournament holding a waived registration is exported and re-imported
- **THEN** that registration is restored paid, waived with its reason, and holding no credits

#### Scenario: A restore does not double the credit
- **WHEN** a document carrying one recorded payment of 1750 and the credit it wrote is restored
- **THEN** the registration holds 1750, not 3500

#### Scenario: Older document with no payments still loads
- **WHEN** a document produced before this addition, in which nothing was credited and nothing waived, is restored
- **THEN** it loads, no registration is waived, and no hand-recorded payment exists

#### Scenario: Older document carrying a credited amount is refused
- **WHEN** a document produced before this addition carries a registration with a credited amount, or with a settled-by-hand mark
- **THEN** the restore is refused with that as the stated reason, and no tournament is created

### Requirement: The export's destination is configured where the export is run
The spreadsheet the Sheets export writes to SHALL be configured in the Export phase, in
the same rail as the control that writes to it, and SHALL NOT be offered anywhere in
Setup.

The address is not a fact about the tournament — it does not govern publication, it is not
read by any rule, and no fencer is affected by it. It is where one tool puts its output,
and it is discovered at the moment that tool is used. An organizer who has just pressed
Export is the only person who has ever needed it.

The address SHALL remain one field in storage with one editor, so that the value the
export reads is the value the organizer last entered. The editor is the destination
dialog, and it SHALL open only from an export pressed with no destination stored: a
destination is changed by forgetting it and exporting again, so the rail offers no
separate control for changing one.

#### Scenario: Setup no longer offers the address
- **WHEN** the organizer opens Setup and visits every tab
- **THEN** no tab offers the export sheet address

#### Scenario: The address is changed beside the export
- **WHEN** the organizer forgets the stored destination and presses export
- **THEN** the destination dialog opens on the same screen, and confirming it stores the new address and runs the export

### Requirement: Configuring the destination is a stated three-step procedure
The console SHALL offer the destination not as a bare address field but as a dialog
stating, in order, the three things that must be true for an export to succeed:

1. an empty spreadsheet exists;
2. it is shared for **writing** with the address the server's Google access acts as, which
   the dialog SHALL state in full and SHALL offer a control that puts on the clipboard;
3. its link is entered, in the field the dialog carries.

The second step is the one a procedure has to state: the service account is its own
identity, so an organizer's own access to their spreadsheet grants the export nothing, and
a spreadsheet that is merely visible is not writable. Without that sentence the export
fails on a permission the organizer has no way to guess at.

Confirming the dialog SHALL store the address and run the export the organizer pressed
for. Dismissing it SHALL store nothing.

#### Scenario: The procedure is stated in order
- **WHEN** the organizer opens the destination dialog
- **THEN** it states the three steps in order, states the service account's address in full, and offers a field for the link

#### Scenario: The address is copied rather than transcribed
- **WHEN** the organizer uses the dialog's copy control
- **THEN** the service account's address is on the clipboard and the dialog states that it was copied

#### Scenario: Dismissal stores nothing
- **WHEN** the organizer types a link into the dialog and dismisses it without confirming
- **THEN** the tournament's stored address is unchanged

### Requirement: The console states the export's service account
The console SHALL be able to read, for an account with console access to a published
tournament, whether the server is configured for Google access at all and — where it is —
the address that access acts as.

The address SHALL be read from the credentials the server already holds, never entered
a second time as its own setting: an address that could disagree with the credentials
would send organizers to share their spreadsheets with an identity that cannot open them.

The address SHALL be stated only within the destination dialog, to an organizer of that
tournament. It is an operational address, not a public one.

#### Scenario: Configured server states its account
- **WHEN** an organizer of a published tournament opens the destination dialog on a server holding Google credentials
- **THEN** the dialog states the address those credentials act as

#### Scenario: No credentials, no export offered
- **WHEN** the server holds no Google credentials
- **THEN** the export control is not offered, the card says that the server has no Google access configured, and the JSON download is still offered

#### Scenario: The account is not public
- **WHEN** a request without console access to the tournament asks for the export's configuration
- **THEN** it is refused, as every other read of that tournament's console is

### Requirement: The export asks for a destination once
Pressing the export control on a tournament with no stored destination SHALL open the
destination dialog rather than reporting an error. Pressing it on a tournament that has one
SHALL run the export without asking.

A missing destination is not a failure the organizer caused; it is the next step, and the
console knows what that step is. The refusal the server raises for an absent address
SHALL remain, as the guarantee behind the console's behaviour rather than something an
organizer meets.

#### Scenario: First export opens the dialog
- **WHEN** the organizer presses export on a tournament that has never been exported
- **THEN** the destination dialog opens and no export is attempted

#### Scenario: A stored destination is not asked for again
- **WHEN** the organizer presses export again after confirming the dialog
- **THEN** the export runs without a dialog

#### Scenario: The server still refuses an address-less export
- **WHEN** an export is requested for a tournament with no stored address
- **THEN** the request is refused naming the missing address

### Requirement: A destination can be forgotten

Beside the stated destination the Export phase SHALL offer a control that clears it, after
which the tournament names none and the next export asks for one again through the
destination dialog.

Clearing SHALL NOT be confirmed. It ends nothing an organizer holds: the spreadsheet and
everything written into it are untouched, the tournament keeps every row it would export,
and undoing it costs pasting back a link the organizer still has. A confirmation would
weigh more than the act it guards.

The control SHALL be offered only where a destination is stored, since there is otherwise
nothing to forget.

#### Scenario: Forgetting returns the tournament to asking
- **WHEN** the organizer clears the stated destination and presses export
- **THEN** the tournament names no destination, the destination dialog opens, and no export is attempted

#### Scenario: Clearing is not confirmed
- **WHEN** the organizer uses the clearing control
- **THEN** the destination is gone at once, with no dialog asking them to confirm it

#### Scenario: Nothing to forget where nothing is stored
- **WHEN** the organizer opens the Export phase on a tournament that names no destination
- **THEN** no clearing control is offered

### Requirement: The rail states the destination as a link
Where the tournament has a stored destination, the Export phase's rail SHALL state it as a
link that opens the spreadsheet. The export control, the link, the control that forgets
the destination and the JSON download SHALL stand on one row, in that order, each as an
icon whose word is its accessible name and whose hint says what it does. The card holding
them SHALL be headed **Export all** (`Exportovat vše`). The English tick SHALL stand above
this card and the open tab's card, not in either (`export-tables`).

Every control of the card SHALL carry a hint saying what it does, opened by hovering or
focusing the control itself, and the card SHALL carry no standing paragraph explaining
them.

While an export is running the link SHALL be withdrawn, and SHALL return when the run
concludes. The withdrawal is how a run states that it is a run: the export has no progress
to report and no interruption to offer, so the one honest signal of "working, then done" is
the destination going away and coming back. It SHALL return on failure as well as on
success — the spreadsheet is still where it is — with the failure stated separately.

#### Scenario: A stored destination is a link on arrival
- **WHEN** the organizer opens the Export phase on a tournament that has a destination
- **THEN** the rail states it as a link, before any export has been run in this visit

#### Scenario: The link withdraws for the run
- **WHEN** the organizer presses export
- **THEN** the link is absent while the export runs and present again once it concludes

#### Scenario: A failed run still leaves the link
- **WHEN** an export fails
- **THEN** the failure is stated and the destination is stated as a link beside it

### Requirement: Discount codes survive an export
The canonical export document SHALL carry the tournament's discount codes, and each registration SHALL state the code it carries and whether a code covered its total. A restore SHALL reconstruct them, so that a registration's total, what it owes and whether it reads as paid are unchanged. A document produced before codes existed SHALL load as a tournament with none. The export document is available only to console access, as it is today.

#### Scenario: Codes round-trip
- **WHEN** a tournament with two codes, one holder of which is covered in full, is exported and restored
- **THEN** both codes exist with their limits and effects, uses read as before, and the covered holder reads as paid with no credit

#### Scenario: Older document
- **WHEN** a v19 document is restored
- **THEN** it loads with no codes and no registration carries one

### Requirement: The document carries the tournament's settings
The canonical document SHALL carry every setting that decides what Squire does
with the tournament or how it presents it, so that a restore reconstructs the
same tournament and not one that behaves differently: its mode (who keeps its
registrations), its payment mode and deposit in each currency, its seating
deadline and the moment seating settled, its amendments deadline, its expiry
grace, its external registration address, each of its features, its subtitle,
short code and cover and logo tints, and its HEMA Ratings category map.

Each registration SHALL carry whether its lifecycle clocks are dormant, the
fencer-list row it was issued from, and its own contact address. A source row
naming a manual row SHALL be rewritten to the restored manual row, as a rule
target is; one naming an imported row SHALL carry over as it stands.

The document SHALL NOT carry the logo or the cover photo; a restored tournament
has neither until the organizer uploads them, and so restores without the
logo's hue band and without a cover ground of "photo". Nor SHALL it carry what belongs to
the deployment rather than the tournament: the owner, the publication moment and
author, the cancellation moment, the bank feed token, the export destination,
the retention stamp, and the generation of guest links. A guest's link from the
original therefore does not open the restored registration, and the organizer
sends it again.

The document version SHALL be raised for this addition. A document produced
before it states no mode, and SHALL restore as a tournament whose registrations
the organizer keeps: Squire then runs no lifecycle against it and sends no
lifecycle mail, and it cannot be published until it is given an external
registration address, so nobody publishes it without deciding its mode. Every
other setting such a document lacks SHALL take the value a new tournament takes.

#### Scenario: A manual tournament round-trips as manual
- **WHEN** a published manual tournament holding registrations issued from an imported fencer list is exported and restored
- **THEN** the restored draft is manual, carries the same external registration address, and every issued registration is dormant and stands in for its row under that row's id

#### Scenario: Payment settings round-trip
- **WHEN** a tournament in deposit mode, with a deposit in both currencies, a seating deadline, an amendments deadline, payments and teams on, is exported and restored
- **THEN** the restored tournament has the same payment mode, deposits, deadlines and features

#### Scenario: A settled seating stays settled
- **WHEN** a tournament whose seating already settled is exported and restored
- **THEN** the restored tournament records the same settlement moment, and no later pass settles it again

#### Scenario: Images stay behind
- **WHEN** a tournament with a logo and a cover photo is exported and restored
- **THEN** the restored tournament has the same chosen cover tint, subtitle and short code and has no logo and no cover photo
- **AND** neither the logo's hue band nor a cover ground of "photo" comes back, since each means something only beside an image that did not travel

#### Scenario: A guest's address comes back
- **WHEN** a registration entered as a guest, with a contact address of its own, is exported and restored
- **THEN** the restored registration carries that contact address, and its old management link does not open it

#### Scenario: An older document restores as manual
- **WHEN** a document of version 23 or earlier is restored
- **THEN** the restored tournament is manual, no reminder, expiry or demotion is ever run against its registrations, and publishing it is refused until an external registration address is set

A restore SHALL NOT fail because the tournament's variable-symbol series is
already held on the deployment: it SHALL take a free series of the same year
instead, and the restored registrations SHALL keep the symbols they were given.
A symbol is never renumbered, so a document whose registrations hold a symbol
the deployment already holds SHALL be refused, and nothing of it restored.

#### Scenario: A copy restores beside its original
- **WHEN** a manual tournament with registrations issued from an imported fencer list is exported and restored on the same deployment under another slug
- **THEN** the restore succeeds, the copy draws from a series of its own, and each tournament keeps its own registrations standing in for its own rows

#### Scenario: A copy whose symbols are taken is refused
- **WHEN** a document whose registrations hold variable symbols already held on the deployment is restored
- **THEN** the restore is refused as a conflict and no tournament is created

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
