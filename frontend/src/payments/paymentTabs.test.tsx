// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";

import i18n from "../i18n";
import PaymentTabs, { type PaymentTab } from "./PaymentTabs";

// The payments phase's two bands and the one line beside them (spec
// `payments-console`, Payment resolution views / A line beside the tab band
// states one thing about the open table).

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

function tabs(overrides: Partial<React.ComponentProps<typeof PaymentTabs>> = {}) {
  return mount(
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

function bands() {
  return [...(host?.querySelectorAll(".stage-control") ?? [])];
}

function tabNamed(label: string) {
  return [...(host?.querySelectorAll("button[role=tab]") ?? [])].find((button) =>
    button.textContent?.startsWith(label),
  ) as HTMLButtonElement | undefined;
}

it("shows one band until the money is being read", () => {
  tabs({ open: "fencers" });
  expect(bands()).toHaveLength(1);
  expect(tabNamed(t("payments.tabs.fencers"))?.getAttribute("aria-selected")).toBe("true");
});

it("shows the second band once the money is chosen", () => {
  tabs({ open: "uncredited", uncreditedCount: 7 });
  expect(bands()).toHaveLength(2);
  // the first band still offers the fencers, and reads as being on the payments
  expect(tabNamed(t("payments.tabs.payments"))?.getAttribute("aria-selected")).toBe("true");
  expect(tabNamed(t("payments.tabs.fencers"))?.getAttribute("aria-selected")).toBe("false");
});

it("states each money table's count, and none for the fencers", () => {
  tabs({ open: "credited", creditedCount: 14, uncreditedCount: 3 });
  expect(tabNamed(t("payments.tabs.credited"))?.textContent).toContain("14");
  expect(tabNamed(t("payments.tabs.uncredited"))?.textContent).toContain("3");
  // a count means outstanding work; a roster size among them would read as more
  expect(tabNamed(t("payments.tabs.fencers"))?.querySelector(".tab-count")).toBeNull();
});

it("keeps an empty table's tab, with its zero", () => {
  tabs({ open: "credited", creditedCount: 0, uncreditedCount: 0 });
  expect(tabNamed(t("payments.tabs.uncredited"))?.textContent).toContain("0");
});

it("marks a table that could not be read at all", () => {
  tabs({ open: "credited", creditedCount: null, uncreditedFailed: true, uncreditedCount: null });
  const failed = tabNamed(t("payments.tabs.uncredited"));
  expect(failed?.querySelector(".tab-mark")).not.toBeNull();
  // no count to show, and a tab merely missing its number states nothing
  expect(failed?.querySelector(".tab-count")).toBeNull();
});

it("hands the payments tab back to the caller rather than choosing a table", () => {
  const onOpen = vi.fn();
  const onOpenPayments = vi.fn();
  tabs({ open: "fencers", onOpen, onOpenPayments });

  act(() => tabNamed(t("payments.tabs.payments"))?.click());

  // which of the two money tables opens is the console's to answer: it knows
  // which was last read
  expect(onOpenPayments).toHaveBeenCalled();
  expect(onOpen).not.toHaveBeenCalled();
});

it("draws the note beside the bands when there is something to say", () => {
  tabs({ open: "uncredited", uncreditedCount: 7, note: "z toho 3 návrhy párování" });
  expect(host?.querySelector(".queue-tab-note")?.textContent).toBe("z toho 3 návrhy párování");
});

it("draws no note where there is nothing to say", () => {
  tabs({ open: "uncredited", uncreditedCount: 7, note: null });
  // a line stating a zero is noise about a thing that did not happen
  expect(host?.querySelector(".queue-tab-note")).toBeNull();
});

it("moves between a band's tabs with the arrow keys", () => {
  const onOpen = vi.fn();
  tabs({ open: "credited", onOpen, creditedCount: 1, uncreditedCount: 1 });

  const credited = tabNamed(t("payments.tabs.credited"));
  act(() => {
    credited?.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }));
  });

  expect(onOpen).toHaveBeenCalledWith<[PaymentTab]>("uncredited");
});
