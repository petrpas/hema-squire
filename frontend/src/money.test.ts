import { describe, expect, it } from "vitest";
import { formatMoney, formatTransactionAmount } from "./money";

/** A tournament's currency is a closed enum the app holds a unit for; a bank
 *  transaction's is whatever the statement said. The boundary between the two
 *  is `formatTransactionAmount`, and what matters is that it never presents an
 *  unfamiliar code as though the amount had no currency. */
describe("a bank transaction's amount", () => {
  it("writes out a currency the app has no unit for", () => {
    const shown = formatTransactionAmount(120050, "USD");
    expect(shown).toContain("USD");
    expect(shown).not.toContain("undefined");
  });

  it("still writes the unit for one it does", () => {
    expect(formatTransactionAmount(120000, "CZK")).toBe(formatMoney(1200, "CZK"));
    expect(formatTransactionAmount(120000, "EUR")).toBe(formatMoney(1200, "EUR"));
  });

  it("reads the stored amount as cents", () => {
    expect(formatTransactionAmount(5, "USD")).toContain("0,05");
    // the grouping separator is whatever the cs locale uses, so it is matched
    // rather than spelled
    expect(formatTransactionAmount(120050, "USD")).toMatch(/^1.200,5 USD$/);
  });
});
