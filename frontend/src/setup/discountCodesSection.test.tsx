// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { api, type DiscountCode, type TournamentDetail } from "../api";
import i18n from "../i18n";
import { DiscountCodesSection } from "./DiscountCodesSection";
import { SaverRegistry } from "./shared";

// Defining a code in Setup (spec discount-codes, An organizer defines discount
// codes; A code in use cannot change what it means).

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let host: HTMLElement | null = null;

beforeEach(async () => {
  await i18n.changeLanguage("cs");
});

afterEach(() => {
  host?.remove();
  host = null;
  vi.restoreAllMocks();
});

const detail = {
  local_currency: "CZK",
  currency_mode: "local",
  eur_payments_enabled: false,
} as TournamentDetail;

async function mount(codes: DiscountCode[]) {
  vi.spyOn(api, "listDiscountCodes").mockResolvedValue(codes);
  host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  await act(async () => {
    root.render(<DiscountCodesSection detail={detail} slug="cup" registry={new SaverRegistry()} />);
  });
  return host;
}

function type(input: HTMLInputElement, value: string) {
  const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
  act(() => {
    set?.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

function button(page: HTMLElement, label: string) {
  return [...page.querySelectorAll("button")].find((b) => b.textContent?.includes(label));
}

function inputs(page: HTMLElement) {
  return [...page.querySelectorAll<HTMLInputElement>("input.cell-input")];
}

it("prefills the code from the name until the organizer types in it", async () => {
  const page = await mount([]);
  act(() => button(page, "Přidat kód")?.click());
  const [name, code] = inputs(page) as [HTMLInputElement, HTMLInputElement];

  type(name, "Trenéři HEMA");
  expect(code.value).toBe("treneri-hema");

  type(code, "vlastni");
  type(name, "Něco jiného");
  expect(code.value).toBe("vlastni");
});

it("locks what a used code means and leaves its name and limit open", async () => {
  const page = await mount([
    {
      id: 1,
      name: "Trenéři",
      code: "treneri",
      max_uses: 10,
      effect: { kind: "fixed", value: 200 },
      scope: [],
      uses: 1,
      locked: true,
    },
  ]);

  const [name, code, limit, value] = inputs(page) as [
    HTMLInputElement,
    HTMLInputElement,
    HTMLInputElement,
    HTMLInputElement,
  ];
  expect([name.disabled, limit.disabled]).toEqual([false, false]);
  expect([code.disabled, value.disabled]).toEqual([true, true]);
  expect(page.querySelector("button.row-action")).toBeNull();
});

it("offers categories only once a percentage asks for them", async () => {
  const page = await mount([
    {
      id: 1,
      name: "Studenti",
      code: "studenti",
      max_uses: null,
      effect: { kind: "percent", value: 20 },
      scope: [],
      uses: 0,
      locked: false,
    },
  ]);
  expect(page.querySelector(".code-scope")).toBeNull();

  const scope = page.querySelectorAll("select")[1] as HTMLSelectElement;
  act(() => {
    Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value")?.set?.call(
      scope,
      "categories",
    );
    scope.dispatchEvent(new Event("change", { bubbles: true }));
  });

  expect(page.querySelector(".code-scope")).not.toBeNull();
});
