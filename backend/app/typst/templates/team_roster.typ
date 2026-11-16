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

#let n = data.len()
#let last_in = input.last_in
// each team's rows: from its start to the next team's start, or the end
#let starts = if input.team_starts.len() > 0 { input.team_starts } else { (0,) }
#let spans = starts.enumerate().map(((k, s)) => {
  let end = if k + 1 < starts.len() { starts.at(k + 1) } else { n }
  (s, end - s)
})

// A team's number, name and paid are one cell spanning its rows, so a long
// team name wraps within the team's height rather than stretching its first
// row, and the span does not break: a team that does not fit moves to the next
// page whole. Rules are lines, not cell borders, since a cell's border cannot
// know where its span ends. Table row y is data row y + 1 (row 0 is the header).
#let heavy = 1pt + black
#let light = 0.5pt + luma(160)

#show table.header: set text(weight: "bold")

#let team-cells((s, rows)) = {
  let cells = ()
  // strings, never markup: a name is text whatever it contains
  for (k, line) in data.slice(s, s + rows).enumerate() {
    if k == 0 {
      cells.push(table.cell(rowspan: rows, breakable: false, line.at(0)))
      cells.push(table.cell(rowspan: rows, breakable: false, line.at(1)))
    }
    for cell in line.slice(2, 7) { cells.push(cell) }
    if k == 0 { cells.push(table.cell(rowspan: rows, breakable: false, line.at(7))) }
  }
  // the line above each team but the first, heavy where the capacity
  // line falls there
  let above = if s == 0 { () } else if s == last_in {
    (table.hline(y: s + 1, stroke: heavy),)
  } else {
    (table.hline(y: s + 1, stroke: light),)
  }
  return above + cells
}
#let body = spans.map(team-cells).flatten()

#table(
  align: (right, left, left, center, left, right, right, center),
  columns: (2.5em, 1.35fr, 1.35fr, 2.25em, 1.9fr, 4em, 4em, 4.6em),
  stroke: (x: heavy, y: none),

  table.header(
    table.hline(stroke: heavy),
    ..input.headers.map(h => table.cell(align: center, strong(h))),
    table.hline(stroke: heavy),
  ),
  ..body,
  table.hline(stroke: heavy),
)
