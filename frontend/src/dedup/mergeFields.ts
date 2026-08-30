import type { DedupMember } from "../api";

/** The columns a candidate group states, for its members and for its
 *  conclusion alike. One list, because reading a merge is reading down a column
 *  (spec `etl-console`, Deduplication candidate review): a value the conclusion
 *  keeps has to sit under the record it came from.
 *
 *  `hr_id` is here as evidence and `registered_at` as context; neither is the
 *  merge's to decide (design D7). */
export const GROUP_COLUMNS = [
  "name",
  "nationality",
  "club",
  "email",
  "hr_id",
  "disciplines",
  "weapon_rentals",
  "afterparty",
  "registered_at",
  "notes",
];

/** How a conclusion cell is edited. `fixed` is stated and not decided here. */
export type FieldKind = "text" | "number" | "list" | "boolean" | "fixed";

const KINDS: Record<string, FieldKind> = {
  name: "text",
  nationality: "text",
  club: "text",
  email: "text",
  notes: "text",
  problems: "text",
  disciplines: "list",
  weapon_rentals: "list",
  afterparty: "boolean",
  hr_id: "fixed",
  registered_at: "fixed",
};

export function fieldKind(column: string): FieldKind {
  return KINDS[column] ?? "fixed";
}

/** Whether any member of the group is bound to a HEMA Ratings profile.
 *
 *  A bound group is identified by its profile, and its identity is not the
 *  merge's to decide — it is changed by rebinding the id on Matching. An
 *  unbound group's identity is the registered words, and choosing which
 *  spelling survives is taken here or nowhere (design D7). */
export function isBound(members: DedupMember[]): boolean {
  return members.some((member) => member.hr_id !== null && member.hr_id !== undefined);
}

/** Whether the organizer may edit this column of the conclusion. */
export function editableInConclusion(column: string, members: DedupMember[]): boolean {
  if (fieldKind(column) === "fixed") return false;
  if (["name", "nationality", "club"].includes(column)) return !isBound(members);
  return true;
}

/** The values the members carry for a field, in member order and without
 *  repetition: what the cell offers as one click each. A merge is nearly always
 *  a choice among what the records already say. */
export function choicesFor(column: string, members: DedupMember[]): string[] {
  const seen: string[] = [];
  for (const member of members) {
    const value = member[column];
    if (value === null || value === undefined || value === "") continue;
    const text = String(value);
    if (!seen.includes(text)) seen.push(text);
  }
  return seen;
}

/** Every value any member carries for a list field, in member order: the pool a
 *  list cell includes from and excludes from. */
export function unionFor(column: string, members: DedupMember[]): string[] {
  const union: string[] = [];
  for (const member of members) {
    const values = member[column];
    if (!Array.isArray(values)) continue;
    for (const value of values) {
      const text = String(value);
      if (!union.includes(text)) union.push(text);
    }
  }
  return union;
}

/** The list a conclusion field holds, tolerant of a payload that has none. */
export function asList(value: unknown): string[] {
  return Array.isArray(value) ? value.map(String) : [];
}
