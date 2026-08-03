import { describe, expect, it } from "vitest";

import { formatForLocale, parseDecimal, parseInteger } from "./numeric";

// Mirrors the backend cases in backend/tests/test_fieldtypes.py so both
// layers are proven to agree (design `add-field-validation`, task 4.5).

describe("parseDecimal", () => {
  it.each([
    ["25,5", 25.5],
    ["25.5", 25.5],
    ["1 250", 1250],
    ["1 250", 1250],
    ["1 250", 1250],
    ["0", 0],
    ["-5", -5],
  ])("accepts %s", (raw, expected) => {
    const result = parseDecimal(raw);
    expect(result.ok).toBe(true);
    if (result.ok) expect(result.value).toBe(expected);
  });

  it.each(["2,5,5", "12a", ".5", "5.", "", "1,2.3", "abc", "  "])(
    "rejects %s as not_a_number",
    (raw) => {
      const result = parseDecimal(raw);
      expect(result).toEqual({ ok: false, code: "not_a_number" });
    },
  );
});

describe("parseInteger", () => {
  it("accepts a whole value with either separator", () => {
    expect(parseInteger("4")).toEqual({ ok: true, value: 4 });
    expect(parseInteger("4,0")).toEqual({ ok: true, value: 4 });
    expect(parseInteger("4.0")).toEqual({ ok: true, value: 4 });
    expect(parseInteger("1 250")).toEqual({ ok: true, value: 1250 });
  });

  it("rejects a fraction as must_be_whole", () => {
    expect(parseInteger("3,5")).toEqual({ ok: false, code: "must_be_whole" });
  });

  it("rejects malformed input as not_a_number", () => {
    expect(parseInteger("2,5,5")).toEqual({ ok: false, code: "not_a_number" });
  });
});

describe("formatForLocale", () => {
  it("writes back with the Czech decimal comma", () => {
    expect(formatForLocale(25.5, "cs")).toBe("25,5");
  });

  it("writes back with the English decimal point", () => {
    expect(formatForLocale(25.5, "en")).toBe("25.5");
  });
});
