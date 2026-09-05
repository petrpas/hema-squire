import { describe, expect, it } from "vitest";

import { nameMatches } from "./nameSearch";

// The link dialog's filter over the roster. A Czech roster is not typed with
// its diacritics, and the organizer resolving a payment is reading a list, not
// asserting an identity.

describe("finding a fencer by typing part of their name", () => {
  it("finds a name typed without its diacritics", () => {
    expect(nameMatches("Václav Pekárek", "pekarek")).toBe(true);
    expect(nameMatches("Milan Diviš", "divis")).toBe(true);
  });

  it("finds a name typed with them", () => {
    expect(nameMatches("Václav Pekárek", "Pekárek")).toBe(true);
  });

  it("disregards case", () => {
    expect(nameMatches("Václav Pekárek", "PEKAREK")).toBe(true);
  });

  it("matches on a prefix, so a few letters are enough", () => {
    expect(nameMatches("Václav Pekárek", "pek")).toBe(true);
  });

  it("takes the words in any order", () => {
    expect(nameMatches("Václav Pekárek", "pek vac")).toBe(true);
    expect(nameMatches("Václav Pekárek", "vaclav pekarek")).toBe(true);
  });

  it("does not match from the middle of a word", () => {
    // a short query matching inside words would hit half the roster
    expect(nameMatches("Václav Pekárek", "ekare")).toBe(false);
  });

  it("requires every word typed", () => {
    expect(nameMatches("Václav Pekárek", "vaclav novak")).toBe(false);
  });

  it("lists everyone when nothing is typed", () => {
    expect(nameMatches("Václav Pekárek", "   ")).toBe(true);
  });

  it("does not decline the name for the reader", () => {
    // "Pekárka" is the accusative; a substring filter is not a Czech
    // morphology engine, and the prefix is what gets there
    expect(nameMatches("Václav Pekárek", "pekárka")).toBe(false);
    expect(nameMatches("Václav Pekárek", "pekár")).toBe(true);
  });
});
