// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it } from "vitest";

import BalanceCell from "./BalanceCell";
import i18n from "./i18n";

// The three facts sharing the Payments table's balance column, only one of
// which is a debt (spec payments, The tolerance decides the state, not this
// figure).

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const t = i18n.getFixedT(i18n.language);

let host: HTMLElement | null = null;

function cell(amount: string, currency: "CZK" | "EUR" | null = "CZK") {
  host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  act(() => root.render(<BalanceCell amount={amount} currency={currency} />));
  return (host.textContent ?? "").replace(/\s/g, " ");
}

afterEach(() => {
  host?.remove();
  host = null;
});

it("states a shortfall as the figure it is", () => {
  // a euro transfer the payer's bank converted lands under the local price; the
  // tolerance accepts it and the organizer is still owed the truth
  expect(cell("40.00")).toBe("40 Kč");
});

it("names an overpayment rather than printing a minus sign", () => {
  const shown = cell("-200.00");
  expect(shown).toBe(t("console.overpaid", { amount: "200 Kč" }).replace(/\s/g, " "));
  // the sign carried the whole meaning before, in a column read for debts
  expect(shown).not.toContain("-");
  expect(shown).not.toContain("−");
});

it("says nothing at all where nothing is outstanding", () => {
  // a column of "0 Kč" is a column of noise: every finished row looks like a
  // row with a figure to read
  expect(cell("0.00")).toBe("");
  expect(cell("0")).toBe("");
});

it("reads unitless until the tournament's currency has arrived", () => {
  expect(cell("40.00", null)).toBe("40.00");
  expect(cell("-200.00", null)).toBe(t("console.overpaid", { amount: "200" }).replace(/\s/g, " "));
});

it("writes an unparseable figure back rather than swallowing it", () => {
  // a balance the reader cannot see is worse than one they cannot explain
  expect(cell("nonsense")).toBe("nonsense");
});
