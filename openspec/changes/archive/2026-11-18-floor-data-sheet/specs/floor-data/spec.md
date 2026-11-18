## MODIFIED Requirements

### Requirement: Data shows who the floor will work with
The `data` tab SHALL show one discipline at a time, chosen from the discipline strip
(`floor-console`, Step tabs choose their discipline by tabs). The chosen discipline's
sheet SHALL be drawn in the office Export's discipline columns, with the office's
headings and the office's grid (owner decision 2026-11-17):

| Column | States |
|---|---|
| # | the row's place in the sheet's order |
| Jméno | the entrant's name |
| Nár. | nationality, as the country's code where the text names a country, as written otherwise |
| Klub | club |
| HR ID | the HEMA Ratings identifier |
| Rating | the discipline's rating |
| Rank | the discipline's rank |
| Zaplaceno | the entry's paid mark |

**Individual disciplines.** One row per entrant, ordered by rating as the pool draw
seeds (`floor-draw`): rated entrants first, by rating descending, with rank breaking a
tie, then the unrated by name.

**Team disciplines.** The sheet SHALL read as the office's team tab reads: each team on
its own row, numbered, with its paid mark, and its members beneath it stating name,
nationality, club, HR ID, rating and rank. Teams are listed in roster order.

**The count.** The sheet SHALL state its discipline's entry count. Withdrawn entries
are not counted (`floor-checkin`).

**Live until the snapshot.** Until the discipline's check-in closes, the sheet SHALL be
read on every open. It is the floor roster with the floor's own edits laid over it
(Requirement: The sheet is the floor's to correct). It changes as the office changes.
Once check-in closes, the sheet SHALL show the discipline's snapshot (Requirement: A
closed discipline's sheet is the snapshot).

#### Scenario: A cancellation reaches the floor
- **WHEN** a registration is cancelled in the office console before check-in closes
- **THEN** the Data tab no longer lists that entrant

#### Scenario: Rating and rank are stated
- **WHEN** the organizer opens Data at Longsword Open, where a fencer has rating 1612.4 and rank 87
- **THEN** that fencer's row states the HR ID, 1612.4 and 87, in the office Export's column order

#### Scenario: Seeding order
- **WHEN** Sabre's entrants are rated 1500, unrated, 1700 and 1500 with ranks 40 and 12
- **THEN** the sheet lists 1700 first, then 1500 at rank 12, then 1500 at rank 40, then the unrated

### Requirement: Entrants come from the office
The `data` tab SHALL NOT offer a table import of its own. Entrants come from the office
(`floor-roster`). Where the tournament's list is kept by the organizer, the operations
panel SHALL link to the office console's Import phase and state that a table imported
there reaches the floor.

The floor roster port stays the only way the office's entrants reach the floor. The
floor's own edits (Requirement: The sheet is the floor's to correct) lie over the port
inside the floor. A later change may fill the port from a second source without
changing any other floor code (owner decision 2026-11-16).

#### Scenario: An organizer-kept tournament is pointed to Import
- **WHEN** the organizer opens Data on a tournament whose list they keep
- **THEN** the operations panel links to `/organizer/:slug/console/import`

## ADDED Requirements

### Requirement: The sheet is the floor's to correct
Until the discipline's check-in closes, the organizer SHALL be able to correct the
sheet in place. These are the day's manual corrections, and this sheet is where they are
made (owner decision 2026-11-17). The desk keeps only its own acts: arrival,
withdrawal and the team lineup (`floor-checkin`). No later tab corrects an entrant.

**A cell.** The name, club, nationality and HR ID cells are a person's and apply in
every discipline that person entered. The rating and rank cells are the entry's, for
this discipline only. Each cell opens for editing as the office's rating cell does. An
emptied cell returns the cell to the value beneath it. A corrected cell is marked the
way the office marks a manual edit.

**An added entrant.** The operations panel SHALL offer "Přidat účastníka" (`floor-console`). The organizer either
picks a person already on the floor, or names a new one as a registrant names a team
member: the name typed once, then looked up in HEMA Ratings (which fills HR ID, club
and nationality) or taken as typed. A new person is a floor-only person (`floor-checkin`, A team
fields a lineup for the day). An added entrant is an entry like any other: the desk
ticks them and they count toward N.

**An added team.** On a team discipline, "Přidat účastníka" SHALL add a team instead
(owner decision 2026-11-17). The team is given a name and its members, and the members
are named in the registrant's own roster editor (`team-disciplines`), each looked up in
HEMA Ratings or taken as typed (owner decision 2026-11-18). A member whose HR ID a person
already on the floor holds SHALL be that person. Any other member is a new floor-only
person. A person who already stands on another team of the discipline SHALL be refused,
since a person fences for one team in a discipline. The number of members is held
to the discipline's team size bounds. The team exists only on the floor. Its members
are its lineup, and the desk changes that lineup as it changes any team's.

**Paid is shown, never changed.** The paid mark SHALL be read from the office and SHALL
NOT be editable on the sheet. An entrant or team added on the floor has no registration
behind it, and its paid cell is empty. Whoever needs to settle a payment does it in the
office or outside Squire (owner decision 2026-11-17).

**A removed entrant.** Each row SHALL offer "Odebrat". Removing an entry that came from
the office is the check-in withdrawal (`floor-checkin`, Withdrawal is per entry and
stays in the floor). It is one state, shown and undone on either tab. A withdrawn row
stays on the sheet, struck through, with "Vrátit". The same holds for a team. Removing
an entrant or a team added on the floor deletes the addition.

**What it reaches.** Every floor reader SHALL read the corrected sheet: the check-in
desk, the snapshot, the planner's N, the draw, the bracket, the results and the public
floor pages.

**What it never reaches.** A correction SHALL NOT be written to the office. The office
console, its exports and its rules state nothing about it (owner decision 2026-11-16,
confirmed 2026-11-17).

**Who may.** The organizer and the tournament's team (`floor-console`).

#### Scenario: A club is corrected once
- **WHEN** the organizer corrects the club of a fencer entered in Longsword Open and Sabre Open on Longsword Open's sheet
- **THEN** both sheets, and the check-in desk, state the corrected club, and the office's export table still states the old one

#### Scenario: A walk-in
- **WHEN** "Jana Nováková" turns up unregistered and the organizer adds her to Sabre Open by name
- **THEN** she is listed on Sabre's sheet and at the desk, Sabre's count rises by one, and no registration exists for her in the office

#### Scenario: A team formed on the day
- **WHEN** on a team discipline with team size 3 to 4, the organizer adds the team "Brno B" with two fencers already on the floor and one new floor-only person
- **THEN** "Brno B" is listed on the sheet with its three members and an empty paid cell, the desk shows it with that lineup, and nothing is written to the office

#### Scenario: A member found in HEMA Ratings is the person already on the floor
- **WHEN** the organizer names a member of a new team, finds them in HEMA Ratings, and that HR ID belongs to a fencer on another team of the discipline
- **THEN** the team is refused, since the member is that fencer and already fences for another team

#### Scenario: A nationality is a code
- **WHEN** a member's nationality arrives from HEMA Ratings as "Czech Republic"
- **THEN** the sheet states "CZ", as the office's export does

#### Scenario: Paid cannot be ticked on the floor
- **WHEN** the organizer opens Data at a discipline with an unpaid entrant
- **THEN** the paid cell states the office's mark and does not open for editing

#### Scenario: A no-show removed on Data appears withdrawn at the desk
- **WHEN** the organizer removes a fencer from Sabre on the Data sheet
- **THEN** the check-in desk shows the fencer withdrawn from Sabre, and "Vrátit" on either tab restores the entry

#### Scenario: A rating corrected by hand
- **WHEN** the organizer types 1550 into a fencer's rating cell on Sabre's sheet
- **THEN** the sheet reorders by the new rating, the cell is marked as edited, and the office Export still states the fetched rating

### Requirement: The ratings are refreshed for one discipline
The operations panel of `data` SHALL offer "Obnovit ratingy" for the chosen
discipline. It is the office Export's control, taken over: the same icon, hint and
result line (`export-tables`).

**What it fetches.** It SHALL fetch from HEMA Ratings the current rating and rank of
every entrant of the chosen discipline that carries an HR ID, including an HR ID
corrected or added on the sheet. It fetches in the discipline's rating category, as
the office fetch does. Entrants of other disciplines are not fetched.

**Where it goes.** The fetched figures SHALL be stored as the floor's figures for that
discipline, over the office's. A hand correction on the sheet stands over a fetched
figure. The office's ratings snapshot SHALL NOT be written, so the office Export is
unchanged.

**The state line.** Beside the control, the panel SHALL state when the discipline was
last fetched on the floor, or that it never was, and how many of its entrants with an
HR ID have no fetched figure. This is the office's statement, worded the same.

**Failure.** Where the fetch fails, the sheet keeps its figures and the panel says the
fetch failed.

#### Scenario: Only Sabre is fetched
- **WHEN** the organizer refreshes the ratings on Sabre's sheet
- **THEN** HEMA Ratings is asked for Sabre's entrants only, the sheet shows their fetched figures, and the office Export's ratings and its "staženo" moment are unchanged

#### Scenario: A hand correction survives a refresh
- **WHEN** a fencer's rating was corrected by hand to 1550 and the organizer then refreshes Sabre
- **THEN** the cell still states 1550, marked as edited

### Requirement: A closed discipline's sheet is the snapshot
Once the discipline's check-in is closed (`floor-checkin`), its sheet SHALL show the
snapshot's entrants with the values the snapshot froze. The paid mark is read from the
live sheet, and it is empty for an entrant no longer on it.

**Read-only.** No cell opens. "Přidat účastníka", "Odebrat" and "Obnovit ratingy" are
not offered. The operations panel SHALL state in one line when check-in closed and
that a change needs the check-in reopened at the desk.

#### Scenario: Refresh after close is not offered
- **WHEN** the organizer opens Data at Sabre after Sabre's check-in closed
- **THEN** the sheet lists the snapshot, no cell is editable, and the panel offers no ratings refresh and says check-in must be reopened to change the list
