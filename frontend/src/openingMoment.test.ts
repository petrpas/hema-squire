import { describe, expect, it } from "vitest";

import {
  COUNTDOWN_WINDOW_MS,
  correctedNow,
  formatCountdown,
  openingMomentMs,
  serverSkewMs,
  withinCountdownWindow,
} from "./openingMoment";

describe("serverSkewMs", () => {
  it("measures how far the device clock trails the server's", () => {
    const device = Date.parse("2026-09-01T12:00:00Z");
    expect(serverSkewMs("2026-09-01T12:00:03Z", device)).toBe(3000);
  });

  it("is negative when the device runs fast", () => {
    const device = Date.parse("2026-09-01T12:05:00Z");
    expect(serverSkewMs("2026-09-01T12:00:00Z", device)).toBe(-300_000);
  });

  it("falls back to no correction rather than NaN on an unparseable stamp", () => {
    expect(serverSkewMs("not a time", 1000)).toBe(0);
  });

  it("applies to a device reading", () => {
    expect(correctedNow(-300_000, 1_000_000)).toBe(700_000);
  });
});

describe("openingMomentMs", () => {
  it("parses the resolved instant", () => {
    expect(openingMomentMs("2026-09-01T16:00:00Z")).toBe(Date.parse("2026-09-01T16:00:00Z"));
  });

  it("is null when the tournament opens on publication", () => {
    expect(openingMomentMs(null)).toBeNull();
  });
});

describe("withinCountdownWindow", () => {
  it("holds inside the last day", () => {
    expect(withinCountdownWindow(4 * 60 * 60 * 1000)).toBe(true);
    expect(withinCountdownWindow(COUNTDOWN_WINDOW_MS)).toBe(true);
  });

  it("does not hold six weeks out, nor once the moment has passed", () => {
    expect(withinCountdownWindow(COUNTDOWN_WINDOW_MS + 1)).toBe(false);
    expect(withinCountdownWindow(0)).toBe(false);
    expect(withinCountdownWindow(-1)).toBe(false);
  });
});

describe("formatCountdown", () => {
  it("reads MM:SS under an hour", () => {
    expect(formatCountdown(90_000)).toBe("01:30");
    expect(formatCountdown(9_000)).toBe("00:09");
  });

  it("reads H:MM:SS above one", () => {
    expect(formatCountdown(4 * 3600_000 + 11 * 60_000 + 58_000)).toBe("4:11:58");
  });

  it("keeps a fixed width as the digits change", () => {
    // the line must not reflow while it ticks (design D7)
    const widths = new Set([59_000, 9_000, 1_000].map((ms) => formatCountdown(ms).length));
    expect(widths.size).toBe(1);
  });

  it("stops at zero rather than going negative", () => {
    expect(formatCountdown(0)).toBe("00:00");
    expect(formatCountdown(-5_000)).toBe("00:00");
  });
});
