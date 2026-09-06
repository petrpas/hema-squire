// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { api } from "../api";
import i18n from "../i18n";
import ClearPaymentsPanel from "./ClearPaymentsPanel";

// Undoing an import of money (spec `payments-clearing`). What the organizer is
// told before committing is as much the feature as the action: that it cannot
// be undone, that a re-import will read the file afresh, and — where money has
// been credited — that it cannot be done at all.

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const t = i18n.getFixedT("cs");

let host: HTMLElement | null = null;

function mount(element: React.ReactElement) {
  host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  act(() => root.render(element));
  return host;
}

function buttonNamed(text: string) {
  return [...(host?.querySelectorAll("button") ?? [])].find(
    (button) => button.textContent?.trim() === text,
  ) as HTMLButtonElement | undefined;
}

async function settle() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

function totals(payments: number, credited = 0) {
  vi.spyOn(api, "clearablePayments").mockResolvedValue({ payments, credited });
}

function render(reload = 0) {
  return mount(<ClearPaymentsPanel slug="cup" reload={reload} onCleared={() => {}} />);
}

beforeEach(() => void vi.restoreAllMocks());
afterEach(() => {
  host?.remove();
  host = null;
});

it("states how many payments it would remove", async () => {
  totals(43);
  render();
  await settle();

  expect(host?.querySelector(".rail-count")?.textContent).toBe("(43)");
});

it("offers nothing when the tournament has taken no money", async () => {
  totals(0);
  render();
  await settle();

  expect(host?.textContent).toBe("");
});

it("asks before clearing, and says the file will be read afresh", async () => {
  totals(43);
  const clear = vi.spyOn(api, "clearPayments");
  render();
  await settle();

  act(() => void buttonNamed(t("payments.clear.action"))?.click());

  expect(clear).not.toHaveBeenCalled();
  expect(host?.textContent).toContain("43");
  // the half nothing else on screen would explain
  expect(host?.textContent).toContain(t("payments.clear.confirm.reread"));
  expect(host?.textContent).toContain(t("payments.clear.confirm.final"));
});

it("clears once confirmed and reports what went", async () => {
  totals(43);
  const clear = vi.spyOn(api, "clearPayments").mockResolvedValue({ payments: 43 });
  const onCleared = vi.fn();
  mount(<ClearPaymentsPanel slug="cup" reload={0} onCleared={onCleared} />);
  await settle();

  act(() => void buttonNamed(t("payments.clear.action"))?.click());
  act(() => void buttonNamed(t("payments.clear.confirm.confirm"))?.click());
  await settle();

  expect(clear).toHaveBeenCalledWith("cup");
  expect(onCleared).toHaveBeenCalled();
  expect(host?.textContent).toContain(t("payments.clear.result", { count: 43 }));
});

it("cancelling leaves the payments alone", async () => {
  totals(43);
  const clear = vi.spyOn(api, "clearPayments");
  render();
  await settle();

  act(() => void buttonNamed(t("payments.clear.action"))?.click());
  act(() => void buttonNamed(t("common.cancel"))?.click());

  expect(clear).not.toHaveBeenCalled();
});

it("states that credited money makes clearing unavailable, instead of failing on click", async () => {
  totals(43, 4);
  render();
  await settle();

  expect(buttonNamed(t("payments.clear.action"))).toBeUndefined();
  expect(host?.textContent).toContain(
    t("payments.clear.blockedByCredit", { count: 4 }),
  );
});

it("says so when the clear fails", async () => {
  totals(43);
  vi.spyOn(api, "clearPayments").mockRejectedValue(new Error("nope"));
  render();
  await settle();

  act(() => void buttonNamed(t("payments.clear.action"))?.click());
  act(() => void buttonNamed(t("payments.clear.confirm.confirm"))?.click());
  await settle();

  expect(host?.querySelector(".login-error")?.textContent).toBe(
    t("payments.clear.failed"),
  );
});

it("follows the console when the money moves", async () => {
  const counts = vi.spyOn(api, "clearablePayments").mockResolvedValue({
    payments: 1,
    credited: 0,
  });
  host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  const view = (reload: number) => (
    <ClearPaymentsPanel slug="cup" reload={reload} onCleared={() => {}} />
  );
  act(() => root.render(view(0)));
  await settle();
  expect(counts).toHaveBeenCalledTimes(1);

  act(() => root.render(view(1)));
  await settle();

  expect(counts).toHaveBeenCalledTimes(2);
});
