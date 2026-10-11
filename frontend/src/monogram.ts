/** Words a monogram skips: they carry no identity of their own, and "Memoriál
 *  v Praze" should read MP rather than MV. Czech and English together, since
 *  tournaments are named in both. */
const FUNCTION_WORDS = new Set(["a", "i", "v", "ve", "na", "z", "ze", "do", "of", "the", "and"]);

/** What a tournament's plate shows where it has no logo (spec fencer-home, A
 *  tournament without a logo shows its monogram): the initials of its first two
 *  meaningful words, uppercased, diacritics kept. Never empty, never longer
 *  than three characters. */
export function monogram(displayName: string): string {
  const tokens = displayName
    .split(/[\s\p{P}\p{S}]+/u)
    .filter((token) => token !== "" && !/^\p{N}+$/u.test(token))
    .filter((token) => !FUNCTION_WORDS.has(token.toLocaleLowerCase("cs")));
  const letters = (s: string) => Array.from(s);
  const [first, second] = tokens;
  let result: string;
  if (first !== undefined && second !== undefined) {
    result = (letters(first)[0] ?? "") + (letters(second)[0] ?? "");
  } else if (first !== undefined) {
    result = letters(first).slice(0, 2).join("");
  } else {
    result = letters(displayName.replace(/\s+/gu, "")).slice(0, 2).join("");
  }
  result = result.toLocaleUpperCase("cs");
  return letters(result).slice(0, 3).join("") || "?";
}
