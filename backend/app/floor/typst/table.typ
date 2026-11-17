// A titled table, for the floor's lists: an official's rozpis, a piste's
// sheet. Filled through sys.inputs.table as JSON {title, subtitle, headers, rows}.
#let data = json(bytes(sys.inputs.table))
#set page(paper: "a4", margin: 1.5cm)
#set text(font: "GFS Neohellenic", size: 12pt)

#text(1.4em, weight: "bold")[#data.title]
#v(0.3em)
#text(0.9em)[#data.subtitle]
#v(1em)

#table(
  columns: data.headers.len(),
  inset: 7pt,
  stroke: 0.5pt,
  table.header(..data.headers.map(h => text(weight: "bold")[#h])),
  ..data.rows.flatten().map(c => [#c]),
)
