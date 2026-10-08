// A discipline roster, typeset by `app/rosterprint.py` (change roster-print).
//
// Vendored from hema-agent's `src/shared/typst/templates/disciplines.typ` and
// now the authoritative copy for rosters. The layout is that file's; the one
// difference is where the data comes from. hema-agent spliced the rows into
// this source as a Typst literal; here they arrive as JSON in
// `sys.inputs.roster`, so a name or a club is always text, never syntax:
//   title    "<tournament> — <discipline>"
//   headers  the seven column headers
//   rows     arrays of seven strings: No., Fencer, Nat., Club, HRID, Rank, Paid
//   last_in  1-based row the heavier rule falls under

#set page(margin: 0.7cm, height: auto, width: 48em)
#set text(font: "GFS Neohellenic", size: 12pt)

#let input = json(bytes(sys.inputs.roster))
#let data = input.rows

#place(
  top + center,
  scope: "parent",
  float: true,
  text(1.4em, weight: "bold", input.title),
)

#let row-count = data.len() + 1  // +1 for header
#let last_in = input.last_in

#set table(
  stroke: (x, y) => if y == 0 {
    (top: 1pt + black,
     bottom: 1pt + black,
     left: 1pt + black,
     right: 1pt + black)
  } else if y == row-count - 1 {
    (bottom: 1pt + black,
     left: 1pt + black,
     right: 1pt + black)
  } else if y == last_in {
    (bottom: 1pt + black,
     left: 1pt + black,
     right: 1pt + black)
  } else {
    (bottom: 0pt,
     left: 1pt + black,
     right: 1pt + black)
  },
)

#show table.header: set text(weight: "bold")


#table(
  align: (right, left, center, left, right, right, center),
  columns: (2.5em, 1.5fr, 2.25em, 2fr, 4em, 4em, 4em),

  table.header(..input.headers.map(h => table.cell(align: center, strong(h)))),
  ..data.flatten().map(cell => [#cell]),
)
