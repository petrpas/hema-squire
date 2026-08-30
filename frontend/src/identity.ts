import type { SheetRow } from "./api";
import type { Phase } from "./Console";

/** How a row is identified once matching has had its say (spec `etl-console`,
 *  HR identity in the phases after matching). From Deduplication onwards the
 *  three identity columns state the matched profile's values; a row bound to no
 *  profile keeps the values it registered under, in italic. */

export const IDENTITY_COLUMNS = ["name", "nationality", "club"];

/** The evidence field an identity column reads on an HR-identity phase. */
const HR_FIELD: Record<string, keyof SheetRow> = {
  name: "hr_name",
  nationality: "hr_nationality",
  club: "hr_club",
};

/** The phases that identify a row by its HR profile. Matching is not among
 *  them: it shows claim beside evidence, which is what the phase is for.
 *
 *  Membership in a set, not a position past Matching in the phase order: the
 *  order also carries Teams and Queue, which draw no fencer table at all, and
 *  an index comparison would quietly answer for them. */
const HR_IDENTITY_PHASES = new Set<string>(["dedup", "payments", "export"]);

export function usesHRIdentity(phase: Phase): boolean {
  return HR_IDENTITY_PHASES.has(phase);
}

/** What an identity cell states, and whether the profile stands behind it.
 *
 *  `declared` is decided by the row, not by the column: a row's identity is one
 *  thing, so its three cells are marked together. A bound row whose profile
 *  carries no club states an em dash upright rather than falling back to the
 *  registered club — the profile is the authority, and its silence is an
 *  answer. Nothing is marked where there is nothing to mark: an em dash is not
 *  a value and is never set in italic. */
/** Anything carrying a claim register, an evidence register and a binding: a
 *  fencer-table row, or a member or conclusion of a deduplication candidate
 *  group. The rule is about the record, not about the table it happens to sit
 *  in (spec `etl-console`, HR identity in the phases after matching). */
export interface IdentityRecord {
  hr_id: number | null;
  [key: string]: unknown;
}

export function identityValue(
  row: IdentityRecord,
  column: string,
  hrIdentity: boolean,
): { text: string; declared: boolean } {
  const bound = row.hr_id !== null && row.hr_id !== undefined;
  const source = hrIdentity && bound ? HR_FIELD[column] : column;
  const value = row[source as string];
  const text = value === null || value === undefined || value === "" ? "—" : String(value);
  return { text, declared: hrIdentity && !bound && text !== "—" };
}
