import type { TFunction } from "i18next";

import type { SheetRow } from "../api";
import { CLUB, HR_ID, NAME, NATIONALITY, rankColumn, ratingColumn } from "./columns";
import type { CapacityLine } from "./ordering";

/** One fighter of a team discipline's tab, flattened: the fighter, or null for
 *  a team whose roster names nobody yet, with the team it fights for. `first`
 *  marks the team's first row, the only one the printout states the team on
 *  (spec roster-print, A team discipline prints as a flat roster). */
export interface FlatTeamRow {
  fighter: SheetRow | null;
  team: SheetRow;
  number: number;
  first: boolean;
}

/** The team tab's rows — each team followed by its fighters, in `teamOrder`'s
 *  order and numbering — as one row per fighter. `teamStarts` are the indices
 *  each team begins at; `lineAfter` is the tab's capacity line counted in the
 *  flat rows, so it falls under the last fighter of the last team above it
 *  (design team-export-layouts D2). */
export function flatTeamRows(
  ordered: SheetRow[],
  numbers: Map<string, number>,
  line: CapacityLine,
): { rows: FlatTeamRow[]; teamStarts: number[]; lineAfter: number | null } {
  const rows: FlatTeamRow[] = [];
  const teamStarts: number[] = [];
  let lineAfter: number | null = null;
  let team: SheetRow | null = null;
  let fighters = 0;

  const close = () => {
    if (team !== null && fighters === 0) {
      rows.push({ fighter: null, team, number: numbers.get(team.id) ?? 0, first: true });
    }
  };

  ordered.forEach((row, index) => {
    if (index === line.after) {
      close();
      team = null;
      lineAfter = rows.length;
    }
    if (row._team !== undefined) {
      close();
      team = row;
      fighters = 0;
      teamStarts.push(rows.length);
      return;
    }
    if (team === null) return;
    rows.push({ fighter: row, team, number: numbers.get(team.id) ?? 0, first: fighters === 0 });
    fighters += 1;
  });
  close();
  return { rows, teamStarts, lineAfter };
}

const blank = (row: SheetRow | null, read: (row: SheetRow) => string) =>
  row === null ? "" : read(row);

/** A flat team row as the printout's eight cells: No., Team, Fencer, Nat.,
 *  Club, HRID, Rank, Paid, the team's three only on its first row. Neither the
 *  entering fencer nor the member count is printed. */
export function teamPrintCells(t: TFunction, slug: string, row: FlatTeamRow): string[] {
  const rank = rankColumn(slug);
  const own = (read: (row: SheetRow) => string) => blank(row.fighter, read);
  return [
    row.first ? String(row.number) : "",
    row.first ? (row.team.name ?? "") : "",
    own((r) => NAME.value(r, 0)),
    own((r) => NATIONALITY.value(r, 0)),
    own((r) => CLUB.value(r, 0)),
    own((r) => HR_ID.value(r, 0)),
    own((r) => rank.value(r, 0)),
    row.first ? t(row.team.paid ? "export.yes" : "export.no") : "",
  ];
}

/** The ids of a team tab's copy, the same columns its worksheet carries (spec
 *  data-export, A team discipline's worksheet is flat). */
export const TEAM_COPY_COLUMN_IDS = [
  "position",
  "team",
  "name",
  "nat",
  "club",
  "hr_id",
  "rating",
  "rank",
  "paid",
] as const;

/** A team tab as tab-separated values: one row per fighter, the team's
 *  number, name and paid on every row, so a pasted copy sorts and filters
 *  without parting a fighter from their team (spec export-tables, A table
 *  leaves by the clipboard). */
export function teamCopyTsv(
  t: TFunction,
  slug: string,
  rows: FlatTeamRow[],
  header: (id: string) => string,
): string {
  const rating = ratingColumn(slug);
  const rank = rankColumn(slug);
  const lines = [TEAM_COPY_COLUMN_IDS.map(header).join("\t")];
  for (const row of rows) {
    const own = (read: (row: SheetRow) => string) => blank(row.fighter, read);
    lines.push(
      [
        String(row.number),
        row.team.name ?? "",
        own((r) => NAME.value(r, 0)),
        own((r) => NATIONALITY.value(r, 0)),
        own((r) => CLUB.value(r, 0)),
        own((r) => HR_ID.value(r, 0)),
        own((r) => rating.value(r, 0)),
        own((r) => rank.value(r, 0)),
        t(row.team.paid ? "export.yes" : "export.no"),
      ].join("\t"),
    );
  }
  return lines.join("\n");
}
