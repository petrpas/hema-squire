/** Every national flag Squire serves, by ISO 3166 alpha-2 code, upper case.
 *  Each SVG is its own hashed asset: the browser fetches only the flags a
 *  roster draws, and no flag is fetched from a third party (spec
 *  public-entrants, Nationality is stated as a flag). The flags' colors are
 *  theirs, admitted by name in the design system's Global prohibitions. */
const FILES = import.meta.glob<string>("../../node_modules/flag-icons/flags/4x3/*.svg", {
  query: "?url&no-inline",
  import: "default",
  eager: true,
});

const FLAGS = new Map(
  Object.entries(FILES).map(([path, url]) => [
    (path.split("/").pop() ?? "").replace(/\.svg$/, "").toUpperCase(),
    url,
  ]),
);

/** The flag's URL for a country, or undefined where Squire has none. */
export function flagUrl(country: string): string | undefined {
  return FLAGS.get(country.toUpperCase());
}

/** Countries whose flag is drawn in greyscale: the owner's decision, and
 *  nothing reads it but the roster's own cell. */
export const GREYSCALE_FLAGS: ReadonlySet<string> = new Set(["RU"]);
