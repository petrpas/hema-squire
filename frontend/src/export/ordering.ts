import type { SheetRow } from "../api";
import { ratingOf } from "./columns";

/** Where a discipline tab draws its line, and what the line means.
 *
 *  `after` is the number of rows above it; null where the table is shorter
 *  than the discipline's capacity and there is nothing for a line to separate.
 */
export interface CapacityLine {
  after: number | null;
  kind: "queue" | "capacity";
}

export function activeOnly(rows: SheetRow[], active: boolean): SheetRow[] {
  return active ? rows.filter((row) => row.paid) : rows;
}

/** The seeding order: rating descending, a fencer with no rating last in the
 *  order they arrived in.
 *
 *  A stable sort over rows already in registration order, so the unrated keep
 *  it among themselves and so do fencers sharing a rating. */
export function seedingOrder(rows: SheetRow[], slug: string): SheetRow[] {
  return [...rows].sort((left, right) => {
    const a = ratingOf(left, slug);
    const b = ratingOf(right, slug);
    if (a === b) return 0;
    if (a === null) return 1;
    if (b === null) return -1;
    return b - a;
  });
}

/** A discipline tab's rows in display order, and where its line falls.
 *
 *  Fencers holding a substitute entry sit below the line whatever the sort key
 *  says, in queue order — which is registration order, the order the rows
 *  arrive in. A fencer with the highest rating in the discipline is still
 *  below it if that is where the tournament put them.
 *
 *  Where the tournament's conduct creates no substitute placements there is no
 *  queued group, and the line marks only where capacity falls in the current
 *  order, naming nobody as queued.
 */
export function rosterOrder(
  rows: SheetRow[],
  slug: string,
  capacity: number | null,
  kind: "queue" | "capacity",
  seeded: boolean,
): { rows: SheetRow[]; line: CapacityLine } {
  const seatedRows = rows.filter((row) => (row.disciplines ?? []).includes(slug));
  const queuedRows = rows.filter((row) => !(row.disciplines ?? []).includes(slug));
  const above = seeded ? seedingOrder(seatedRows, slug) : seatedRows;
  const ordered = [...above, ...queuedRows];
  if (queuedRows.length > 0) {
    return { rows: ordered, line: { after: above.length, kind } };
  }
  const overflows = capacity !== null && ordered.length > capacity;
  return { rows: ordered, line: { after: overflows ? capacity : null, kind } };
}
