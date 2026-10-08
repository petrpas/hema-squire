import type { TFunction } from "i18next";

import type { ExportTab, RosterPrint, SheetRow } from "../api";
import { CLUB, HR_ID, NAME, NATIONALITY, POSITION, paidColumn, rankColumn } from "./columns";
import { rosterOrder } from "./ordering";

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
 *  tab's order here by the same `rosterOrder` the table and the copy use, so
 *  the printout lists what is on screen, numbered as on screen, with its rule
 *  where the screen draws its line. The server only typesets. */
export function rosterPrint(
  t: TFunction,
  listed: SheetRow[],
  tab: ExportTab,
  seeded: boolean,
  english: boolean,
): RosterPrint {
  const ordered = rosterOrder(listed, tab.key, tab.capacity, tab.line ?? "capacity", seeded);
  const columns = PRINT_COLUMNS(t, tab.key);
  return {
    discipline: tab.key,
    rows: ordered.rows.map((row, index) => columns.map((column) => column.value(row, index))),
    line_after: ordered.line.after,
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
