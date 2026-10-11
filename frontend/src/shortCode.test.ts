import { describe, expect, it } from "vitest";
import { shortCodeCheck, shortCodePatch, shortCodeShown } from "./setup/ShortCodeField";

// The Setup short code (spec tournament-admin, Tournament short code): an
// untouched field follows the name, and only a value that differs from the
// derived monogram is ever sent.

describe("the short code field", () => {
  it("shows the monogram of the name as it now stands until something is typed", () => {
    expect(shortCodeShown(null, "Pražský dlouhý meč")).toBe("PD");
    expect(shortCodeShown(null, "Brněnská šavle")).toBe("BŠ");
    expect(shortCodeShown("PDM", "Pražský dlouhý meč")).toBe("PDM");
  });

  it("sends nothing for an unchanged prefill, a restated monogram, or a cleared field", () => {
    expect(shortCodePatch(null, "Pražský dlouhý meč")).toBeNull();
    expect(shortCodePatch("PD", "Pražský dlouhý meč")).toBeNull();
    expect(shortCodePatch("  ", "Pražský dlouhý meč")).toBeNull();
  });

  it("sends a code that differs, trimmed", () => {
    expect(shortCodePatch(" PDM ", "Pražský dlouhý meč")).toBe("PDM");
  });

  it("refuses more than three characters and allows an empty field", () => {
    expect(shortCodeCheck("PRAHA")).not.toBeNull();
    expect(shortCodeCheck("")).toBeNull();
    expect(shortCodeCheck("PDM")).toBeNull();
  });
});
