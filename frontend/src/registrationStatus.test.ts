import { describe, expect, it } from "vitest";

import type { TournamentDetail } from "./api";
import { amendmentOpen, registrationStatus } from "./openingMoment";

/** Only the fields the two gate functions read; the rest of the payload has
 *  no bearing on the window. */
function tournament(overrides: Partial<TournamentDetail> = {}): TournamentDetail {
  return {
    date: "2026-12-05",
    timezone: "Europe/Prague",
    registration_opens: null,
    registration_opens_time: null,
    registration_opens_at: null,
    registration_closes: null,
    amendments_close: null,
    server_time: "2026-09-01T12:00:00Z",
    ...overrides,
  } as TournamentDetail;
}

const at = (iso: string) => Date.parse(iso);

describe("registrationStatus — the opening edge is an instant", () => {
  const opensAtSix = tournament({
    registration_opens: "2026-09-01",
    registration_opens_time: "18:00:00",
    // 18:00 Prague in September is 16:00Z
    registration_opens_at: "2026-09-01T16:00:00Z",
  });

  it("is shut one minute before the named hour", () => {
    expect(registrationStatus(opensAtSix, at("2026-09-01T15:59:00Z"))).toBe("opens_on");
  });

  it("is open at the named minute", () => {
    expect(registrationStatus(opensAtSix, at("2026-09-01T16:00:00Z"))).toBe("open");
  });

  it("is open one minute after", () => {
    expect(registrationStatus(opensAtSix, at("2026-09-01T16:01:00Z"))).toBe("open");
  });

  it("opens on publication when no opening date is set", () => {
    expect(registrationStatus(tournament(), at("2026-01-01T00:00:00Z"))).toBe("open");
  });
});

describe("registrationStatus — the closing edge is a whole local day", () => {
  const closesEndOfSeptember = tournament({ registration_closes: "2026-09-30" });

  it("accepts late in the evening, local to the tournament", () => {
    // 23:30 Prague on the closing date
    expect(registrationStatus(closesEndOfSeptember, at("2026-09-30T21:30:00Z"))).toBe("open");
  });

  it("closes once the local day has turned", () => {
    // 00:30 Prague the next day
    expect(registrationStatus(closesEndOfSeptember, at("2026-09-30T22:30:00Z"))).toBe("closed");
  });

  it("falls back to the tournament date with no close set", () => {
    expect(registrationStatus(tournament(), at("2026-12-06T12:00:00Z"))).toBe("closed");
  });
});

describe("amendmentOpen", () => {
  it("follows registration when no amendments close is set", () => {
    const t = tournament({ registration_closes: "2026-09-30" });
    expect(amendmentOpen(t, at("2026-09-30T21:30:00Z"))).toBe(true);
    expect(amendmentOpen(t, at("2026-09-30T22:30:00Z"))).toBe(false);
  });

  it("closes on its own boundary, as a whole local day", () => {
    const t = tournament({ registration_closes: "2026-10-30", amendments_close: "2026-09-30" });
    expect(amendmentOpen(t, at("2026-09-30T21:30:00Z"))).toBe(true);
    expect(amendmentOpen(t, at("2026-09-30T22:30:00Z"))).toBe(false);
  });

  it("is shut while registration has not opened", () => {
    const t = tournament({
      registration_opens: "2026-09-01",
      registration_opens_at: "2026-09-01T16:00:00Z",
    });
    expect(amendmentOpen(t, at("2026-09-01T15:59:00Z"))).toBe(false);
  });
});
