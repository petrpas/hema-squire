// A team discipline's roster, typeset by `app/rosterprint.py` (change
// team-export-layouts). The page, font and frame are `discipline_roster.typ`'s;
// the table is flat, one row per fighter, with the team's number, name and paid
// on its first row only. The data arrives as JSON in `sys.inputs.roster`, so a
// name, club or team name is always text, never syntax:
//   title        "<tournament> — <discipline>"
//   headers      the eight column headers
//   rows         arrays of eight strings: No., Team, Fencer, Nat., Club, HRID,
//                Rank, Paid
//   last_in      1-based row the heavier rule falls under
//   paper        "a4" for the printed PDF, "long" for the one-image PNG
//   team_starts  0-based rows a team begins at; a thin rule stands above each
//                but the first

#let input = json(bytes(sys.inputs.roster))

// The PDF is printed: A4 pages, the header row repeated on each. The PNG is
// posted: one page as tall as its content, so one image however long.
#let a4 = input.at("paper", default: "long") == "a4"
#set page(margin: 0.7cm, height: auto, width: 48em) if not a4
#set page(paper: "a4", margin: 0.7cm) if a4
#set text(font: "GFS Neohellenic", size: 12pt)
#let data = input.rows

#place(
  top + center,
  scope: "parent",
  float: true,
  text(1.4em, weight: "bold", input.title),
)

#let row-count = data.len() + 1  // +1 for header
#let last_in = input.last_in
// table rows are 1-based below the header, so a team starting at data row i
// begins at table row i + 1, and the rule is the bottom of the row before it
#let team-ends = input.team_starts.filter(i => i > 0)

#set table(
  stroke: (x, y) => {
    let sides = (left: 1pt + black, right: 1pt + black)
    if y == 0 {
      (top: 1pt + black, bottom: 1pt + black, ..sides)
    } else if y == row-count - 1 or y == last_in {
      (bottom: 1pt + black, ..sides)
    } else if team-ends.contains(y) {
      (bottom: 0.5pt + luma(160), ..sides)
    } else {
      (bottom: 0pt, ..sides)
    }
  },
)

#show table.header: set text(weight: "bold")

#table(
  align: (right, left, left, center, left, right, right, center),
  columns: (2.5em, 1.35fr, 1.35fr, 2.25em, 1.9fr, 4em, 4em, 4.6em),

  table.header(..input.headers.map(h => table.cell(align: center, strong(h)))),
  ..data.flatten().map(cell => [#cell]),
)
