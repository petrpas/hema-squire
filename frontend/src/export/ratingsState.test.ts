import { describe, expect, it } from "vitest";

import i18n from "../i18n";
import { ratingsState } from "./ratingsState";

const t = i18n.getFixedT("cs");

describe("the ratings statement beside the refresh", () => {
  it("says the ratings were never fetched and how many wait", () => {
    expect(ratingsState(t, "cs", null, 56)).toBe(
      `${t("export.ratingsState.never")} · ${t("export.ratingsState.missing", { count: 56 })}`,
    );
    expect(ratingsState(t, "cs", null, 56)).toContain("56 šermířů");
  });

  it("states the fetch and the fighters bound since", () => {
    const stated = ratingsState(t, "cs", "2026-11-10T09:30:00Z", 3);
    expect(stated).toContain("10. 11. 2026");
    expect(stated).toContain("3 šermíři");
  });

  it("states only the moment where nobody is missing", () => {
    const stated = ratingsState(t, "cs", "2026-11-10T09:30:00Z", 0);
    expect(stated).not.toContain("·");
    expect(stated).toContain("10. 11. 2026");
  });

  it("says nothing where nothing was fetched and nobody is bound", () => {
    expect(ratingsState(t, "cs", null, 0)).toBeNull();
  });
});
