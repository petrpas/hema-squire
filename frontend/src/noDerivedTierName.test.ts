import { expect, it } from "vitest";

// The defect this whole change removed: a name for a state nothing stored.
// `isEasyMode` derived one from the feature flags wherever it was needed, and
// because the dialog offered it as a choice anyway, there had to be an answer
// for "advanced with nothing ticked". Nothing may compute such a label again
// (spec tournament-features: no name is derived from how many are enabled).
//
// A grep-shaped assertion is the right instrument here: what is asserted is
// the absence of a construct anywhere, which no unit test of a component can
// reach. Read through Vite's own glob rather than `node:fs`, so the file needs
// no ambient node types to typecheck.

const SOURCES = import.meta.glob("./**/*.{ts,tsx}", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

const FORBIDDEN = ["isEasyMode", "EASY_MODE", "MODE_FEATURES"];

it("no source file derives a tier name from the feature flags", () => {
  const offenders: string[] = [];
  for (const [path, text] of Object.entries(SOURCES)) {
    if (path.endsWith("noDerivedTierName.test.ts")) continue;
    for (const token of FORBIDDEN) {
      if (text.includes(token)) offenders.push(`${path}: ${token}`);
    }
  }
  expect(offenders).toEqual([]);
});

it("the sweep is actually reading files", () => {
  // guards the glob: a pattern that silently matched nothing would turn the
  // assertion above into no assertion at all
  expect(Object.keys(SOURCES).length).toBeGreaterThan(30);
});

const LOCALES = import.meta.glob("./i18n/*.json", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

it("neither locale still names an easy or advanced mode", () => {
  const named = Object.entries(LOCALES).filter(([, text]) =>
    /easy mode|advanced mode|jednoduch\w* režim|pokročil\w* režim/i.test(text),
  );
  expect(named.map(([path]) => path)).toEqual([]);
});
