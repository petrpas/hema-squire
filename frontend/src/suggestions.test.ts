import { describe, expect, it } from "vitest";

import {
  filterSuggestions,
  organizerEntries,
  plainEntries,
  worthOffering,
} from "./suggestions";

describe("filterSuggestions", () => {
  const entries = plainEntries(["Sokolovna Praha", "Tělocvična Brno", "Hala Ostrava"]);

  it("offers everything for an empty query", () => {
    expect(filterSuggestions(entries, "")).toEqual(entries);
    expect(filterSuggestions(entries, "   ")).toEqual(entries);
  });

  it("matches a substring, not only a prefix", () => {
    expect(filterSuggestions(entries, "Brno").map((e) => e.value)).toEqual(["Tělocvična Brno"]);
  });

  it("ignores case on both sides", () => {
    expect(filterSuggestions(plainEntries(["Spolek SHBU Praha"]), "shbu")).toHaveLength(1);
    expect(filterSuggestions(plainEntries(["spolek shbu"]), "SHBU")).toHaveLength(1);
  });

  it("preserves the order it was given", () => {
    // the backend hands them over most-recent-first; nothing here re-sorts
    expect(filterSuggestions(entries, "a").map((e) => e.value)).toEqual([
      "Sokolovna Praha",
      "Tělocvična Brno",
      "Hala Ostrava",
    ]);
  });

  it("returns nothing when the query matches nothing", () => {
    expect(filterSuggestions(entries, "Zlín")).toEqual([]);
  });
});

describe("worthOffering", () => {
  it("says no to an empty set, so a field with no history shows no affordance", () => {
    expect(worthOffering([], "")).toBe(false);
  });

  it("says no when the only entry restates what is already typed", () => {
    expect(worthOffering(plainEntries(["Praha"]), "Praha")).toBe(false);
    expect(worthOffering(plainEntries(["Praha"]), " Praha ")).toBe(false);
  });

  it("says yes when a sole entry differs from the typed text", () => {
    expect(worthOffering(plainEntries(["Praha"]), "Pra")).toBe(true);
  });

  it("says yes whenever more than one value is on offer", () => {
    expect(worthOffering(plainEntries(["Praha", "Brno"]), "Praha")).toBe(true);
  });
});

describe("organizerEntries", () => {
  it("carries the link as the secondary line so it can fill alongside the name", () => {
    expect(organizerEntries([{ name: "SHBU", link: "https://shbu.example" }])).toEqual([
      { value: "SHBU", secondary: "https://shbu.example" },
    ]);
  });

  it("keeps a linkless club linkless rather than borrowing another's", () => {
    expect(organizerEntries([{ name: "SHBU", link: null }])).toEqual([
      { value: "SHBU", secondary: null },
    ]);
  });

  it("keeps one name used with two links as two distinguishable entries", () => {
    const entries = organizerEntries([
      { name: "SHBU", link: "https://a.example" },
      { name: "SHBU", link: "https://b.example" },
    ]);
    expect(entries).toHaveLength(2);
    expect(entries.map((e) => e.secondary)).toEqual(["https://a.example", "https://b.example"]);
  });
});
