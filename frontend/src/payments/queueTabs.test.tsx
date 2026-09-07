// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it } from "vitest";

import i18n from "../i18n";
import QueueCard from "./QueueCard";
import QueueTabs, { QueueTabStrip, useSheetVisible } from "./QueueTabs";

// The payments phase reads one table at a time behind a strip of tabs (spec
// `payments-console`). The fencer list leads — it is what the phase is for —
// and every queue's tab states its own count, because work in a queue nobody
// is looking at must still be visible.

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const t = i18n.getFixedT("cs");

let host: HTMLElement | null = null;
let root: ReturnType<typeof createRoot> | null = null;

function mount(element: React.ReactElement) {
  host = document.createElement("div");
  document.body.append(host);
  root = createRoot(host);
  act(() => root!.render(element));
  return host;
}

/** Re-render into the same root, the way a background reload reaches the
 *  queues — a second `createRoot` would remount and hide the state under
 *  test. */
function rerender(element: React.ReactElement) {
  act(() => root!.render(element));
}

async function settle() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

function tabNamed(text: string) {
  return [...(host?.querySelectorAll('[role="tab"]') ?? [])].find((tab) =>
    tab.textContent?.startsWith(text),
  ) as HTMLButtonElement | undefined;
}

/** Stands in for the fencer table: shown exactly when its own tab is read. */
function Sheet() {
  return useSheetVisible() ? <p>tabulka</p> : null;
}

function phase(counts: [number | null, number | null]) {
  return (
    <QueueTabs primary="Stav">
      <QueueTabStrip />
      <QueueCard title="první" count={counts[0]}>
        <p>tělo první</p>
      </QueueCard>
      <QueueCard title="druhá" count={counts[1]}>
        <p>tělo druhé</p>
      </QueueCard>
      <Sheet />
    </QueueTabs>
  );
}

afterEach(() => {
  host?.remove();
  host = null;
});

it("leads with the fencer table and opens on it", async () => {
  mount(phase([2, 7]));
  await settle();

  const labels = [...(host?.querySelectorAll('[role="tab"]') ?? [])].map((tab) => tab.textContent);
  expect(labels[0]).toContain("Stav");
  expect(tabNamed("Stav")?.getAttribute("aria-selected")).toBe("true");
  expect(host?.textContent).toContain("tabulka");
});

it("gives the table no count of its own", async () => {
  mount(phase([2, 7]));
  await settle();

  expect(tabNamed("Stav")?.querySelector(".tab-count")).toBeNull();
  expect([...(host?.querySelectorAll(".tab-count") ?? [])].map((n) => n.textContent)).toEqual([
    "2",
    "7",
  ]);
});

it("shows one thing at a time", async () => {
  mount(phase([2, 7]));
  await settle();

  act(() => void tabNamed("druhá")?.click());

  expect(host?.textContent).toContain("tělo druhé");
  expect(host?.textContent).not.toContain("tabulka");
  expect(host?.textContent).not.toContain("tělo první");
});

it("states every queue's count, so work nobody is looking at is visible", async () => {
  mount(phase([0, 7]));
  await settle();

  expect(tabNamed("první")?.textContent).toContain("0");
  expect(tabNamed("druhá")?.textContent).toContain("7");
});

it("keeps the tab it is put on when a queue's count changes", async () => {
  // nothing moves the organizer on its own; a queue that gains or loses work
  // says so on its own tab
  mount(phase([2, 7]));
  await settle();
  act(() => void tabNamed("první")?.click());
  expect(host?.textContent).toContain("tělo první");

  rerender(phase([0, 9]));
  await settle();

  expect(tabNamed("první")?.getAttribute("aria-selected")).toBe("true");
});

it("says an open queue is empty rather than showing a blank panel", async () => {
  mount(phase([0, 7]));
  await settle();

  act(() => void tabNamed("první")?.click());

  expect(host?.textContent).toContain(t("payments.queue.empty"));
  expect(host?.textContent).not.toContain("tělo první");
});

it("marks a queue that could not be read, and keeps its failure to itself", async () => {
  mount(
    <QueueTabs primary="Stav">
      <QueueTabStrip />
      <QueueCard title="první" count={null} failed>
        <p>tělo první</p>
      </QueueCard>
      <QueueCard title="druhá" count={3}>
        <p>tělo druhé</p>
      </QueueCard>
      <Sheet />
    </QueueTabs>,
  );
  await settle();

  // it holds no count, so nothing would draw the organizer to it but the mark
  expect(tabNamed("první")?.querySelector(".tab-mark")).not.toBeNull();
  expect(tabNamed("druhá")?.querySelector(".tab-mark")).toBeNull();
  expect(host?.textContent).toContain("tabulka");

  act(() => void tabNamed("první")?.click());

  expect(host?.textContent).toContain(t("payments.queue.failed"));
});

it("carries the title and the count once, on the tab", async () => {
  mount(phase([4, 0]));
  await settle();
  act(() => void tabNamed("první")?.click());

  // a heading under the tab would say the same thing twice
  expect(host?.querySelector('[role="tabpanel"] h2')).toBeNull();
});

it("shows the table where there are no tabs at all", () => {
  mount(<Sheet />);

  expect(host?.textContent).toContain("tabulka");
});

it("still draws its own heading outside the tabs", () => {
  mount(
    <QueueCard title="sama" count={3}>
      <p>tělo</p>
    </QueueCard>,
  );

  expect(host?.querySelector("h2")?.textContent).toBe("sama");
  expect(host?.querySelector(".rail-count")?.textContent).toBe("3");
});

it("falls back to the table when the chosen tab is no longer there", async () => {
  // a blank phase is the worst failure this can have, so an active tab that
  // names nothing resolves to the list rather than to nothing
  mount(phase([2, 7]));
  await settle();
  act(() => void tabNamed("druhá")?.click());
  expect(host?.textContent).not.toContain("tabulka");

  rerender(
    <QueueTabs primary="Stav">
      <Sheet />
    </QueueTabs>,
  );
  await settle();

  expect(host?.textContent).toContain("tabulka");
});
