import { foldName, nameMatches } from "../nameSearch";

/** The admin panel's search (spec user-roles, Admin panel): a name matches as
 *  roster search matches one, every other field on a substring, all of it with
 *  case and diacritics folded. An empty needle matches everything. */
export function adminMatches(needle: string, names: string[], others: (string | null)[]): boolean {
  const trimmed = needle.trim();
  if (trimmed === "") return true;
  if (names.some((name) => nameMatches(name, trimmed))) return true;
  const folded = foldName(trimmed);
  return others.some((value) => value !== null && foldName(value).includes(folded));
}
