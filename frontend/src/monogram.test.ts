import { describe, expect, it } from "vitest";
import { monogram } from "./monogram";

describe("monogram", () => {
  it("takes the initials of the first two words, diacritics kept", () => {
    expect(monogram("Brněnská šavle 2027")).toBe("BŠ");
  });

  it("takes two letters of a single word", () => {
    expect(monogram("Bohemia")).toBe("BO");
  });

  it("skips function words and ampersands", () => {
    expect(monogram("Memoriál v Praze")).toBe("MP");
    expect(monogram("Sword & Buckler Open")).toBe("SB");
    expect(monogram("The Hall of Arms")).toBe("HA");
  });

  it("falls back to the raw name when nothing is left", () => {
    expect(monogram("2027")).toBe("20");
  });

  it("is never empty and never longer than three", () => {
    for (const name of ["", " ", "!!", "Ⅻ", "Ångström Åland Öresund"]) {
      const result = monogram(name);
      expect(result.length).toBeGreaterThan(0);
      expect(Array.from(result).length).toBeLessThanOrEqual(3);
    }
  });
});
