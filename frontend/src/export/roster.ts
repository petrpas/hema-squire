import type { TFunction } from "i18next";

import type { ExportTab, RosterPrint, SheetRow } from "../api";
import {
  CLUB,
  HR_ID,
  NAME,
  NATIONALITY,
  POSITION,
  paidColumn,
  rankColumn,
  teamNameColumn,
  teamPaidColumn,
  teamPositionColumn,
} from "./columns";
import { rosterOrder, teamOrder } from "./ordering";

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

/** The same seven columns for a team discipline's tab, read by its two kinds
 *  of row: the number and the paid cell belong to the team, and so does the
 *  name cell, which carries the entering fencer and the member count with it
 *  (spec roster-print — the printout typesets what the tab shows). */
export const TEAM_PRINT_COLUMNS = (t: TFunction, slug: string, numbers: Map<string, number>) => [
  teamPositionColumn(numbers),
  teamNameColumn(t),
  NATIONALITY,
  CLUB,
  HR_ID,
  rankColumn(slug),
  teamPaidColumn(t),
];

/** The roster as the tab shows it, for the server to typeset.
 *
 *  `listed` is the tab's rows under its active-only switch; they are put in the
 *  tab's order here by the same `rosterOrder` — or, on a team discipline,
 *  `teamOrder` — that the table and the copy use, so the printout lists what is
 *  on screen, numbered as on screen, with its rule where the screen draws its
 *  line. The server only typesets, and a team discipline's tab needs no change
 *  there: it is the same seven cells per row. */
export function rosterPrint(
  t: TFunction,
  listed: SheetRow[],
  tab: ExportTab,
  seeded: boolean,
  english: boolean,
): RosterPrint {
  const { rows, line, columns } = tab.teams
    ? (() => {
        const teams = teamOrder(listed, tab.line ?? "capacity");
        return { ...teams, columns: TEAM_PRINT_COLUMNS(t, tab.key, teams.numbers) };
      })()
    : {
        ...rosterOrder(listed, tab.key, tab.capacity, tab.line ?? "capacity", seeded),
        columns: PRINT_COLUMNS(t, tab.key),
      };
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
