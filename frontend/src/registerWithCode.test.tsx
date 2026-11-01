// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import {
  ApiError,
  type Availability,
  api,
  type DiscountBreakdown,
  type PricePreview,
  type TournamentDetail,
} from "./api";
import i18n from "./i18n";
import { AVAILABILITY, DETAIL } from "./publicDetailFixture";
import { RegistrationForm } from "./TournamentFace";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let host: HTMLElement | null = null;

// The code on the register form, end to end against a stubbed server (spec
// fencer-home, The code field). The server's answer is what the form states.

beforeEach(async () => {
  await i18n.changeLanguage("cs");
});

afterEach(() => {
  host?.remove();
  host = null;
  vi.restoreAllMocks();
});

const applied: DiscountBreakdown = {
  name: "Studenti",
  effect: { kind: "percent", value: 10 },
  applied: true,
  deducted: 80,
  deducted_eur: null,
};

function priced(total: number): PricePreview {
  return { total, currency: "CZK", eur_total: null, discounts: [], applied_code: null };
}

function typeCode(page: HTMLElement, value: string) {
  const input = [...page.querySelectorAll("label")]
    .find((label) => label.textContent === "Kód")
    ?.querySelector("input") as HTMLInputElement;
  act(() => {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set?.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

function apply(page: HTMLElement) {
  const button = [...page.querySelectorAll("button")].find((b) => b.textContent === "Uplatnit");
  act(() => button?.click());
}

async function form() {
  const page = document.createElement("div");
  document.body.append(page);
  host = page;
  await act(async () => {
    createRoot(page).render(
      <MemoryRouter>
        <RegistrationForm
          detail={
            {
              ...DETAIL,
              accepts_discount_codes: true,
              disciplines: [...DETAIL.disciplines, { ...DETAIL.disciplines[0], slug: "SB" }],
            } as unknown as TournamentDetail
          }
          availability={[...AVAILABILITY, { ...AVAILABILITY[0], slug: "SB" } as Availability]}
          mode={{ kind: "preview" }}
        />
      </MemoryRouter>,
    );
  });
  const discipline = page.querySelector<HTMLInputElement>("input[type=checkbox]:not([disabled])");
  act(() => discipline?.click());
  await afterPreview();
  return page;
}

async function afterPreview() {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 350));
  });
}

it("states what an accepted code took off, and the total with it", async () => {
  vi.spyOn(api, "pricePreview").mockResolvedValue(priced(800));
  vi.spyOn(api, "pricePreviewWithCode").mockResolvedValue({
    ...priced(720),
    applied_code: applied,
  });
  const page = await form();

  typeCode(page, "studenti");
  apply(page);
  await afterPreview();

  expect(page.textContent).toContain("Studenti: −80 Kč");
  expect(page.querySelector(".form-total")?.textContent).toContain("720");
});

it("keeps pricing the code when the selection changes", async () => {
  vi.spyOn(api, "pricePreview").mockResolvedValue(priced(800));
  const withCode = vi.spyOn(api, "pricePreviewWithCode").mockResolvedValue({
    ...priced(720),
    applied_code: applied,
  });
  const page = await form();
  typeCode(page, "studenti");
  apply(page);
  await afterPreview();
  const calls = withCode.mock.calls.length;

  const another = page.querySelectorAll<HTMLInputElement>(
    "input[type=checkbox]:not([disabled])",
  )[1];
  act(() => another?.click());
  await afterPreview();

  expect(withCode.mock.calls.length).toBe(calls + 1);
});

it("says a refused code does not apply and leaves the total alone", async () => {
  vi.spyOn(api, "pricePreview").mockResolvedValue(priced(800));
  vi.spyOn(api, "pricePreviewWithCode").mockRejectedValue(new ApiError(422, "code_unavailable"));
  const page = await form();

  typeCode(page, "nikdy");
  apply(page);
  await afterPreview();
  await afterPreview();

  expect(page.textContent).toContain("Tento kód neplatí.");
  expect(page.querySelector(".form-total")?.textContent).toContain("800");
});
