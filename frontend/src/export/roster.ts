import type { TFunction } from "i18next";

import type { ExportTab, RosterPrint, SheetRow } from "../api";
import { CLUB, HR_ID, NAME, NATIONALITY, POSITION, paidColumn, rankColumn } from "./columns";
import { rosterOrder, teamOrder } from "./ordering";
import { flatTeamRows, teamPrintCells } from "./teamFlat";

/** What a discipline's printed roster carries, cell for cell: the tab's own
 *  columns but the rating, which the template has no column for (spec
 *  roster-print, The roster's columns, title and language). */
export const PRINT_COLUMNS = (t: TFunction, slug: string) => [
  POSITION,
  NAME,
  NATIONALITY,
  CLUB,
  HR_ID,
  rankColumn(slug),
  paidColumn(t),
];

/** The roster as the tab shows it, for the server to typeset.
 *
 *  `listed` is the tab's rows under its active-only switch; they are put in the
 *  tab's order here by the same `rosterOrder` — or, on a team discipline,
 *  `teamOrder` — that the table and the copy use, so the printout lists what is
 *  on screen, numbered as on screen, with its rule where the screen draws its
 *  line. A team discipline is flattened to one row per fighter, eight cells
 *  each, with where each team begins (spec roster-print, A team discipline
 *  prints as a flat roster). */
export function rosterPrint(
  t: TFunction,
  listed: SheetRow[],
  tab: ExportTab,
  seeded: boolean,
  english: boolean,
): RosterPrint {
  if (tab.teams) {
    const teams = teamOrder(listed, tab.line ?? "capacity");
    const flat = flatTeamRows(teams.rows, teams.numbers, teams.line);
    return {
      discipline: tab.key,
      rows: flat.rows.map((row) => teamPrintCells(t, tab.key, row)),
      line_after: flat.lineAfter,
      team_starts: flat.teamStarts,
      english,
    };
  }
  const { rows, line } = rosterOrder(listed, tab.key, tab.capacity, tab.line ?? "capacity", seeded);
  const columns = PRINT_COLUMNS(t, tab.key);
  return {
    discipline: tab.key,
    rows: rows.map((row, index) => columns.map((column) => column.value(row, index))),
    line_after: line.after,
    english,
  };
}

/** Offers a file the server answered with as a download, as the JSON export
 *  does. */
export function saveBlob(blob: Blob, filename: string) {
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}
