// @vitest-environment jsdom
import { renderToStaticMarkup } from "react-dom/server";
import { expect, it, vi } from "vitest";

import type { DiscountCodeRedemption } from "../api";
import i18n from "../i18n";
import DiscountCodesTable, { usesLine } from "./DiscountCodesTable";
import PaymentTabs from "./PaymentTabs";

// The third table of the payments phase (spec payments-console, The codes
// table says who holds what).

const t = i18n.getFixedT(i18n.language);

function tabs(overrides: Partial<React.ComponentProps<typeof PaymentTabs>> = {}) {
  return renderToStaticMarkup(
    <PaymentTabs
      open="fencers"
      onOpen={vi.fn()}
      onOpenPayments={vi.fn()}
      creditedCount={0}
      uncreditedCount={0}
      {...overrides}
    />,
  );
}

it("offers no codes tab without a code", () => {
  expect(tabs()).not.toContain(t("payments.tabs.codes"));
});

it("offers a codes tab with no count beside the other two", () => {
  const html = tabs({ codes: true });
  expect(html).toContain(t("payments.tabs.codes"));
  expect(html).toContain(t("payments.tabs.payments"));
  expect(html).not.toContain("tab-count");
});

it("reading the codes opens no money band", () => {
  const html = tabs({ open: "codes", codes: true });
  expect(html).not.toContain(t("payments.tabs.credited"));
});

it("offers no money where Squire does not collect", () => {
  const html = tabs({ open: "codes", codes: true, money: false });
  expect(html).not.toContain(t("payments.tabs.payments"));
  expect(html).toContain(t("payments.tabs.registrations"));
});

it("states uses against the limit, past it too, and alone without one", () => {
  expect(usesLine({ id: 1, name: "Trenéři", max_uses: 10, uses: 3 })).toBe("Trenéři 3 / 10");
  expect(usesLine({ id: 1, name: "Jednorázový", max_uses: 1, uses: 2 })).toBe("Jednorázový 2 / 1");
  expect(usesLine({ id: 1, name: "Klub", max_uses: null, uses: 4 })).toBe("Klub 4");
});

it("lists who holds a code and what it took off", () => {
  const row: DiscountCodeRedemption = {
    registration_id: 1,
    fencer: "Jana Nováková",
    name: "Trenéři",
    code: "treneri",
    deducted: 200,
    currency: "CZK",
    paid: false,
  };
  const html = renderToStaticMarkup(<DiscountCodesTable rows={[row]} />);
  expect(html).toContain("Jana Nováková");
  expect(html).toContain("treneri");
  expect(html).toContain("200");
});
