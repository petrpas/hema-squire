import { describe, expect, it } from "vitest";

import { ApiError } from "./api";
import { apiErrors, checkMoney, checkPercent, checkString, checkUrl } from "./validation";

describe("checkString", () => {
  it("accepts a value within bounds", () => {
    expect(checkString("name", "OrganizerIn.name", "Prague Open")).toBeNull();
  });

  it("rejects a value past maxLength", () => {
    const error = checkString("name", "OrganizerIn.name", "x".repeat(300));
    expect(error).toEqual({ field: "name", code: "too_long", params: { max: 200 } });
  });

  it("rejects an empty required value", () => {
    const error = checkString("name", "OrganizerIn.name", "   ", { required: true });
    expect(error).toEqual({ field: "name", code: "required", params: {} });
  });

  it("rejects a pasted zero-width joiner", () => {
    const error = checkString("name", "OrganizerIn.name", "a‍joined");
    expect(error).toEqual({ field: "name", code: "forbidden_characters", params: {} });
  });
});

describe("checkMoney", () => {
  it("accepts a value at the CZK ceiling", () => {
    expect(checkMoney("fee", "10000", "CZK")).toBeNull();
  });

  it("rejects a value over the CZK ceiling", () => {
    const error = checkMoney("fee", "95000", "CZK");
    expect(error).toEqual({ field: "fee", code: "out_of_range", params: { min: 0, max: 10000 } });
  });

  it("rejects the same figure over the EUR ceiling", () => {
    const error = checkMoney("fee_eur", "5000", "EUR");
    expect(error).toEqual({ field: "fee_eur", code: "out_of_range", params: { min: 0, max: 1000 } });
  });

  it("rejects a negative value", () => {
    const error = checkMoney("fee", "-5", "CZK");
    expect(error?.code).toBe("out_of_range");
  });
});

describe("checkPercent", () => {
  it("rejects a value above 100", () => {
    const error = checkPercent("amount_tolerance_percent", "150");
    expect(error).toEqual({
      field: "amount_tolerance_percent",
      code: "out_of_range",
      params: { min: 0, max: 100 },
    });
  });
});

describe("checkUrl", () => {
  it("accepts an https link", () => {
    expect(checkUrl("ruleset_url", "DisciplineIn.ruleset_url", "https://example.com/rules")).toBeNull();
  });

  it("rejects a javascript: scheme", () => {
    const error = checkUrl("ruleset_url", "DisciplineIn.ruleset_url", "javascript:alert(1)");
    expect(error).toEqual({ field: "ruleset_url", code: "bad_link_scheme", params: {} });
  });

  it("rejects a link without a scheme", () => {
    const error = checkUrl("ruleset_url", "DisciplineIn.ruleset_url", "example.com/rules");
    expect(error).toEqual({ field: "ruleset_url", code: "bad_url", params: {} });
  });
});

describe("apiErrors", () => {
  it("maps the envelope shape to a flat list", () => {
    const err = new ApiError(422, {
      errors: [{ field: "slug", code: "slug_taken", params: {} }],
    });
    expect(apiErrors(err)).toEqual([{ field: "slug", code: "slug_taken", params: {} }]);
  });

  it("returns an empty list for a bare-string detail", () => {
    const err = new ApiError(404, "discipline_not_found");
    expect(apiErrors(err)).toEqual([]);
  });

  it("returns an empty list for a non-ApiError", () => {
    expect(apiErrors(new Error("boom"))).toEqual([]);
  });
});
