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

/** Queued rows in queue order: by the placement's queue moment, stable, so
 *  rows sharing a moment keep the registration order they arrived in. Every
 *  queued row is a registration's and carries its moment; one that somehow
 *  does not goes last rather than being guessed a place. */
export function queueOrder(rows: SheetRow[], slug: string): SheetRow[] {
  const moment = (row: SheetRow) => {
    const at = Date.parse(row.queued_since?.[slug] ?? "");
    return Number.isNaN(at) ? Number.POSITIVE_INFINITY : at;
  };
  return [...rows].sort((left, right) => {
    const a = moment(left);
    const b = moment(right);
    return a === b ? 0 : a < b ? -1 : 1;
  });
}

/** A discipline tab's rows in display order, and where its line falls.
 *
 *  Fencers holding a substitute entry sit below the line whatever the sort key
 *  says, in queue order — by each placement's queue moment, which is its
 *  registration time unless it was demoted for non-payment (spec
 *  `seating-queue`). The sort is stable over rows arriving in registration
 *  order, so fencers sharing a moment keep that order. A fencer with the
 *  highest rating in the discipline is still below it if that is where the
 *  tournament put them.
 *
 *  Where the tournament's conduct creates no substitute placements there is no
 *  queued group, and the line marks where capacity falls in the tab's own
 *  order, naming nobody as queued. The seeding order does not move it: it
 *  orders the fencers above the line among themselves, and a fencer inside
 *  capacity is never shown past it for having a low rating.
 */
export function rosterOrder(
  rows: SheetRow[],
  slug: string,
  capacity: number | null,
  kind: "queue" | "capacity",
  seeded: boolean,
): { rows: SheetRow[]; line: CapacityLine } {
  const seatedRows = rows.filter((row) => (row.disciplines ?? []).includes(slug));
  const queuedRows = queueOrder(
    rows.filter((row) => !(row.disciplines ?? []).includes(slug)),
    slug,
  );
  const seed = (group: SheetRow[]) => (seeded ? seedingOrder(group, slug) : group);
  if (queuedRows.length > 0) {
    const above = seed(seatedRows);
    return { rows: [...above, ...queuedRows], line: { after: above.length, kind } };
  }
  if (capacity === null || seatedRows.length <= capacity) {
    return { rows: seed(seatedRows), line: { after: null, kind } };
  }
  const above = seed(seatedRows.slice(0, capacity));
  return { rows: [...above, ...seatedRows.slice(capacity)], line: { after: capacity, kind } };
}
