import { describe, expect, it } from "vitest";

import { registeredMoment } from "./momentText";

describe("registeredMoment", () => {
  it("states the day and the clock of an offset-bearing moment in the tournament's zone", () => {
    // mid-March is still UTC+1 in Prague, whatever zone the reader sits in
    expect(registeredMoment("2026-03-14T13:32:52+00:00", "Europe/Prague")).toBe(
      "14. 3. 2026 14:32",
    );
  });

  it("reads one instant the same however it was written", () => {
    const prague = registeredMoment("2026-03-14T15:32:52+02:00", "Europe/Prague");
    expect(registeredMoment("2026-03-14T13:32:52Z", "Europe/Prague")).toBe(prague);
  });

  it("separates two moments on one day", () => {
    const morning = registeredMoment("2026-03-14T07:05:00Z", "Europe/Prague");
    const evening = registeredMoment("2026-03-14T19:48:00Z", "Europe/Prague");
    expect(morning).toBe("14. 3. 2026 08:05");
    expect(evening).toBe("14. 3. 2026 20:48");
  });

  it("shows a zone-less stamp as the wall clock it states, unshifted", () => {
    expect(registeredMoment("2026-03-14T15:32:52", "Pacific/Auckland")).toBe("14. 3. 2026 15:32");
  });

  it("accepts a zone-less stamp written with a space instead of a T", () => {
    expect(registeredMoment("2026-03-14 09:07", "Europe/Prague")).toBe("14. 3. 2026 09:07");
  });

  it("gives the em dash when nothing was recorded", () => {
    expect(registeredMoment(null, "Europe/Prague")).toBe("—");
  });

  it("falls back to the reader's zone when the tournament's is unknown to Intl", () => {
    const unknown = registeredMoment("2026-03-14T13:32:52Z", "Mars/Olympus");
    expect(unknown).toBe(registeredMoment("2026-03-14T13:32:52Z", null));
  });

  it("falls back to the reader's zone before the tournament's has arrived", () => {
    expect(registeredMoment("2026-03-14T13:32:52Z", null)).toMatch(/^\d+\. \d+\. 2026 \d{2}:\d{2}$/);
  });

  it("gives an unreadable stamp back rather than showing Invalid Date", () => {
    expect(registeredMoment("last tuesday", "Europe/Prague")).toBe("last tuesday");
    expect(registeredMoment("2026-13-99T99:99:99Z", "Europe/Prague")).toBe("2026-13-99T99:99:99Z");
  });
});
