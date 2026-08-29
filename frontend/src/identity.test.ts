// @vitest-environment jsdom
import { describe, expect, it } from "vitest";

import type { SheetRow } from "./api";
import { PHASES, type Phase } from "./Console";
import { identityValue, usesHRIdentity } from "./identity";

// How a row is identified once matching has had its say (spec `etl-console`,
// HR identity in the phases after matching).

function row(fields: Partial<SheetRow>): SheetRow {
  return {
    id: "reg:1",
    name: "Lukáš Müller",
    nationality: "DE",
    club: "Berlin",
    hr_id: null,
    hr_name: null,
    hr_nationality: null,
    hr_club: null,
    ...fields,
  } as SheetRow;
}

const BOUND = row({
  hr_id: 8821,
  hr_name: "Lukas Mueller",
  hr_nationality: "DE",
  hr_club: "Berlin Schwert",
});

describe("usesHRIdentity", () => {
  it("holds for the phases after matching", () => {
    const after: Phase[] = ["dedup", "payments", "export"];
    expect(after.every(usesHRIdentity)).toBe(true);
  });

  it("does not hold for matching, which shows claim beside evidence", () => {
    expect(usesHRIdentity("matching")).toBe(false);
  });

  it("does not hold for any other phase", () => {
    const others = PHASES.filter((phase) => !usesHRIdentity(phase));
    expect(others).toEqual(["setup", "import", "fencers", "matching", "teams", "queue"]);
  });
});

describe("identityValue", () => {
  it("states the profile's values on a bound row", () => {
    expect(identityValue(BOUND, "name", true)).toEqual({
      text: "Lukas Mueller",
      declared: false,
    });
    expect(identityValue(BOUND, "nationality", true)).toEqual({ text: "DE", declared: false });
    expect(identityValue(BOUND, "club", true)).toEqual({
      text: "Berlin Schwert",
      declared: false,
    });
  });

  it("keeps an unbound row's own words, marked as declared", () => {
    const unbound = row({});
    expect(identityValue(unbound, "name", true)).toEqual({
      text: "Lukáš Müller",
      declared: true,
    });
    expect(identityValue(unbound, "club", true)).toEqual({ text: "Berlin", declared: true });
  });

  it("states an em dash where a bound profile carries no club", () => {
    const clubless = row({ hr_id: 8821, hr_name: "Lukas Mueller", hr_club: null });
    // not a fallback to the registered club: the profile is the authority
    expect(identityValue(clubless, "club", true)).toEqual({ text: "—", declared: false });
  });

  it("marks nothing where an unbound row has nothing to state", () => {
    const bare = row({ club: null });
    expect(identityValue(bare, "club", true)).toEqual({ text: "—", declared: false });
  });

  it("reads the row's own values, unmarked, off an HR-identity phase", () => {
    expect(identityValue(BOUND, "club", false)).toEqual({ text: "Berlin", declared: false });
    expect(identityValue(row({}), "club", false)).toEqual({ text: "Berlin", declared: false });
  });
});
