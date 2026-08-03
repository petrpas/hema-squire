import { describe, expect, it } from "vitest";

import { type RosterMember, type TeamEntry } from "./api";
import { rosterChanged, summarizeSaves } from "./roster";

function member(overrides: Partial<RosterMember> = {}): RosterMember {
  return { name: "Alice", hr_id: null, club: null, nationality: null, ...overrides };
}

function team(overrides: Partial<TeamEntry> = {}): TeamEntry {
  return {
    id: 1,
    slug: "longsword",
    name: "Team A",
    waitlisted: false,
    fee: 0,
    fee_eur: null,
    team_min: 1,
    team_max: 5,
    members: [],
    prefill: null,
    ...overrides,
  };
}

describe("rosterChanged", () => {
  it("reports no change for an identical roster", () => {
    const saved = [member({ name: "Alice" }), member({ name: "Bob" })];
    const draft = [member({ name: "Alice" }), member({ name: "Bob" })];
    expect(rosterChanged(saved, draft)).toBe(false);
  });

  it("reports a change on a renamed member", () => {
    const saved = [member({ name: "Alice" })];
    const draft = [member({ name: "Alicia" })];
    expect(rosterChanged(saved, draft)).toBe(true);
  });

  it("reports a change on reordered members", () => {
    const saved = [member({ name: "Alice" }), member({ name: "Bob" })];
    const draft = [member({ name: "Bob" }), member({ name: "Alice" })];
    expect(rosterChanged(saved, draft)).toBe(true);
  });

  it("reports a change on an added member", () => {
    const saved = [member({ name: "Alice" })];
    const draft = [member({ name: "Alice" }), member({ name: "Bob" })];
    expect(rosterChanged(saved, draft)).toBe(true);
  });

  it("reports a change on a removed member", () => {
    const saved = [member({ name: "Alice" }), member({ name: "Bob" })];
    const draft = [member({ name: "Alice" })];
    expect(rosterChanged(saved, draft)).toBe(true);
  });

  it("reports a change on a rebound member", () => {
    const saved = [member({ name: "Alice", hr_id: null, club: null, nationality: null })];
    const draft = [member({ name: "Alice", hr_id: 1234, club: "HEMA Club", nationality: "CZ" })];
    expect(rosterChanged(saved, draft)).toBe(true);
  });
});

describe("summarizeSaves", () => {
  it("splits saved and failed teams from a partial failure", () => {
    const teamA = team({ id: 1, name: "Team A" });
    const teamB = team({ id: 2, name: "Team B" });
    const updatedA = { ...teamA, members: [member({ name: "Alicia" })] };

    const { saved, failed } = summarizeSaves([
      { team: teamA, result: { status: "fulfilled", value: updatedA } },
      { team: teamB, result: { status: "rejected", reason: new Error("network") } },
    ]);

    expect(saved).toEqual([updatedA]);
    expect(failed).toEqual(["Team B"]);
  });
});
