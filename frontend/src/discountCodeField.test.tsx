// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";

import { DiscountCodeField, DiscountCodeLine } from "./DiscountCodeField";
import i18n from "./i18n";
import { slugify } from "./slugify";

// What a fencer sees of a code (spec fencer-home, The code field).

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const t = i18n.getFixedT(i18n.language);
let host: HTMLElement | null = null;

function mount(element: React.ReactElement) {
  host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  act(() => root.render(element));
  return host;
}

afterEach(() => {
  host?.remove();
  host = null;
});

function field(overrides: Partial<React.ComponentProps<typeof DiscountCodeField>> = {}) {
  return mount(
    <DiscountCodeField
      value="trener"
      onChange={vi.fn()}
      onApply={vi.fn()}
      disabled={false}
      refused={false}
      {...overrides}
    />,
  );
}

it("hands the code over only when asked", () => {
  const onApply = vi.fn();
  const button = field({ onApply }).querySelector("button") as HTMLButtonElement;
  expect(onApply).not.toHaveBeenCalled();
  act(() => button.click());
  expect(onApply).toHaveBeenCalledOnce();
});

it("cannot apply nothing", () => {
  const button = field({ value: "  " }).querySelector("button") as HTMLButtonElement;
  expect(button.disabled).toBe(true);
});

it("says a refused code does not apply, in one plain line", () => {
  expect(field({ refused: true }).textContent).toContain(t("discountCode.refused"));
});

it("states what an accepted code took off", () => {
  const html = mount(
    <DiscountCodeLine
      applied={{
        name: "Trenéři",
        effect: { kind: "fixed", value: 200 },
        applied: true,
        deducted: 200,
        deducted_eur: null,
      }}
      detail={{ local_currency: "CZK", eur_payments_enabled: false }}
    />,
  );
  expect(html.textContent).toContain("Trenéři");
  expect(html.textContent).toContain("200");
});

it("derives a code from a name", () => {
  expect(slugify("Trenéři HEMA")).toBe("treneri-hema");
  expect(slugify("  Člen — Klub!  ")).toBe("clen-klub");
});
