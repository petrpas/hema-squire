## Context

`TeamRoster` uses `table-layout: fixed` with declared widths for every column but the
name (so opening a team does not reshuffle columns under the pointer); `IndividualRoster`
uses the automatic layout. Both read their headers from `export.column.*`, shared with the
organizer's Export tables. Since `entrant-nationality-flags` the Nat. cell is mostly a
16×12 flag, but its column is still sized for a code. The breakpoint set is 480/768/1024,
written as literals beside the component's rule (`responsive-layout`).

## Goals / Non-Goals

**Goals:** every column visible at 390px; name before club; the decisions in the proposal.

**Non-Goals:** a card layout or stacked rows (the roster stays a table, with its line and
queue); any change to the Export tables, the console or the printed roster; the detail
tab band (already a scrolling band by `responsive-layout`).

## Decisions

**Both rosters use a fixed layout with declared widths, and the name gets the rest.**
The bug is not fixed layout itself but that the name was the only flexible column while
club had 163px. As built: gutter 2.25rem (1.9rem narrow), Nat. 3.25rem (2.25rem), HR
(individual) 5.5rem (2rem), Paid 4rem (2.75rem), club 30% of the table (24% narrow,
where it otherwise took as much as the name), the name taking the remainder. Cells close
up to 6px side padding below 768px. Club cells get `white-space: nowrap;
overflow: hidden; text-overflow: ellipsis`. The individual roster joins the fixed layout
so the ellipsis has a width to cut against. Alternative considered: `min-width` on the
name with auto layout. Rejected: auto layout lets one long club still win the width.

**Nat. and Paid centred.** Both columns' `th` and `td` get `text-align: center`, through
column classes on the cells (`col-nat`, `col-paid`) rather than `colgroup`, since a `col`
cannot set alignment. The flag is an inline image, so centring the cell centres it.

**Position numbers 2px further left.** The gutter's right padding grows from 0.5rem to
`calc(0.5rem + 2px)` under `.entrants-table` only; the console's sheet tables share
`.sheet-table .col-gutter` and keep theirs. A visual adjustment the owner asked for, with
no requirement behind it.

**Narrow HRID by CSS, not by JavaScript.** `HrIdCell` renders the number inside a
`<span className="hr-number">` and sets `aria-label` to the identifier on the link. Below
768px the span is visually hidden (the existing `::after` arrow stays), so the arrow
alone shows and the accessible name still states the number. No width measurement, no
resize listener. The header carries both words in two spans swapped the same way
("HRID" / "HR"), and Paid likewise ("Zapl." / "Zap.").

**Own i18n keys.** `entrants.column.paid` ("Zapl."/"Paid"), `entrants.column.paidShort`
("Zap."/"Paid"), `entrants.column.hr` ("HRID"), `entrants.column.hrShort` ("HR"). The
Export tables keep their `export.column.*` words.

**Member club.** `TeamRoster` already computes the team's shared club; a member's club
cell renders empty when the shared club is non-null. Done in the client: it is a
statement about display next to the team row, and the server keeps sending each member's
club, which a narrower answer would not make more private.

**Members' identifiers leave the answer.** `TeamMemberRow.hr_id` and
`EntrantTeamMemberOut.hr_id` are removed, under "A roster carries only what it states".
The projection lookup that settled the member's identifier stays for name, club and
nationality.

**Toggle in the gap, names in one column.** Today the chevron is inline before the
name, so an openable team's name starts 12px plus a gap to the right of an unopenable
one's. The team name cell gets a left padding wide enough to hold the chevron (about
1.4rem), and every team's name starts at that padding, button or not. The chevron is
taken out of the flow (`position: absolute` within the cell, `position: relative` on the
`td`) and centred horizontally in the padding, its vertical centre on the first line of
the name (`top` set from the line height, not the cell's middle), so a wrapped name keeps
it level with its first line. The button still wraps the chevron and the name, so the
whole name stays the target. Members keep their indent, measured from the same edge.

## Risks / Trade-offs

- [A club cut to "Pardubický spo…" cannot be read whole on a phone, where `title` does
  not show] → accepted by the owner: visitors know the clubs.
- [Fixed layout on the individual roster changes desktop widths too] → the same rule
  (name first) is what the owner asked for at every width; checked on desktop in tasks.
- [Visually hidden text must stay out of copy-paste oddities] → the hidden span is
  removed from layout with the standard visually-hidden pattern, not `display: none`, only
  for the header words; the link's number uses `aria-label` so `display: none` is fine.
