/** Matching a typed fragment against a fencer's name.
 *
 *  Case and diacritics are folded, because a Czech roster is full of names an
 *  organizer will not type accented — `Pekárek` has to be reachable by typing
 *  `pekarek`, and `Diviš` by `divis`. The backend has held this rule since the
 *  fighters index (`hr_index.name_key`, "disregards diacritics, case and word
 *  order"); this is the same rule where a person is doing the typing.
 *
 *  Word order is not folded here, and deliberately: this is a filter over a
 *  list the reader can see, not an identity test. Every word of the needle must
 *  appear, in any order, as the start of some word of the name — so `pek` finds
 *  Pekárek, `vaclav pek` finds Václav Pekárek, and `pek vac` finds him too,
 *  while `ekare` does not, because nobody searches from the middle of a
 *  surname and matching there makes a short query hit half the roster.
 */
export function foldName(value: string): string {
  return value
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLocaleLowerCase();
}

export function nameMatches(name: string, needle: string): boolean {
  const words = foldName(needle).split(/\s+/).filter(Boolean);
  if (words.length === 0) return true;
  const parts = foldName(name).split(/\s+/).filter(Boolean);
  return words.every((word) => parts.some((part) => part.startsWith(word)));
}
