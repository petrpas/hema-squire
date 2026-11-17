// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { MemoryRouter, Outlet, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { type Account, api, type TournamentDetail } from "../api";
import i18n from "../i18n";
import FloorRoute from "./FloorRoute";
import { type FloorSetup, type FloorSummary, floorApi, planApi } from "./floorApi";

// The floor console's rail (spec floor-console): eight tabs in a fixed order,
// each an icon named only in its hint, the default tab following publication,
// a badge meaning "waiting" said in words, and the schedule panel becoming
// the rail's last tab below the canonical breakpoint, where a schedule is
// planned at all.

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const t = i18n.getFixedT("cs");

const tournament = {
  slug: "cup",
  display_name: "Cup",
  date: "2099-12-05",
  registrations_kept_by: "squire",
  is_event: false,
} as unknown as TournamentDetail;

const setup: FloorSetup = {
  disciplines: [{ id: 1, slug: "LS", name: "Longsword", kind: "individual" }],
  persons: [],
  scope: { plan_schedule: true, multi_day: false, plan_officials: false },
  days: {
    stored: false,
    days: [{ date: "2099-12-05", start: "09:00", end: "19:00", breaks: [], discipline_ids: [1] }],
  },
  pistes: [],
  formats: [],
  officials: [],
  params: { finals: "elimination", min_rest_minutes: 10 },
  preferences: { pool_size: "larger", club_weight: 10, nationality_weight: 3 },
};

function summary(fields: Partial<FloorSummary> = {}): FloorSummary {
  return {
    plan_published: false,
    badges: { setup: false },
    setup_missing: [],
    ...fields,
  };
}

function stubViewport(narrow: boolean) {
  vi.stubGlobal("matchMedia", () => ({
    matches: narrow,
    addEventListener: () => {},
    removeEventListener: () => {},
  }));
}

let host: HTMLElement | null = null;
let root: Root | null = null;

async function open(path: string, answer: FloorSummary = summary()) {
  vi.spyOn(api, "consoleTournament").mockResolvedValue(tournament);
  vi.spyOn(api, "account").mockResolvedValue({ id: 1 } as unknown as Account);
  vi.spyOn(floorApi, "summary").mockResolvedValue(answer);
  vi.spyOn(floorApi, "setup").mockResolvedValue(setup);
  vi.spyOn(floorApi, "roster").mockRejectedValue(new Error("not under test"));
  vi.spyOn(planApi, "state").mockRejectedValue(new Error("not under test"));
  host = document.createElement("div");
  document.body.append(host);
  root = createRoot(host);
  act(() =>
    root?.render(
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route element={<Outlet context={{ onLogout: () => {} }} />}>
            <Route path="organizer/:slug/floor" element={<FloorRoute />} />
            <Route path="organizer/:slug/floor/:tab" element={<FloorRoute />} />
          </Route>
        </Routes>
      </MemoryRouter>,
    ),
  );
  for (let i = 0; i < 4; i++) {
    await act(async () => {
      await Promise.resolve();
    });
  }
}

function tabs(): HTMLButtonElement[] {
  return [...(host?.querySelectorAll<HTMLButtonElement>(".floor-rail [role=tab]") ?? [])];
}

function selected(): string | undefined {
  return tabs().find((tab) => tab.getAttribute("aria-selected") === "true")?.id;
}

beforeEach(() => {
  void i18n.changeLanguage("cs");
  stubViewport(false);
});

afterEach(() => {
  act(() => root?.unmount());
  host?.remove();
  host = null;
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("the floor console's tabs", () => {
  it("offers all eight in their fixed order", async () => {
    await open("/organizer/cup/floor/data");

    expect(tabs().map((tab) => tab.getAttribute("aria-label"))).toEqual([
      t("floor.tabs.setup"),
      t("floor.tabs.data"),
      t("floor.tabs.plan"),
      t("floor.tabs.today"),
      t("floor.tabs.checkin"),
      t("floor.tabs.pools"),
      t("floor.tabs.bracket"),
      t("floor.tabs.results"),
    ]);
  });

  it("draws an icon and names the tab only in its hint", async () => {
    await open("/organizer/cup/floor/data");

    const today = tabs()[3];
    expect(today?.querySelector("svg")).not.toBeNull();
    expect(today?.querySelector(".floor-rail-hint")?.textContent).toBe(t("floor.tabs.today"));
  });

  it("lands on Setup before a plan is published", async () => {
    await open("/organizer/cup/floor");

    expect(selected()).toBe("floor-tab-setup");
  });

  it("lands on the overview once a plan is published, also from a tab that does not exist", async () => {
    await open("/organizer/cup/floor/nowhere", summary({ plan_published: true }));

    expect(selected()).toBe("floor-tab-today");
  });

  it("badges only the tab that waits", async () => {
    await open("/organizer/cup/floor/data", summary({ badges: { setup: true, data: false } }));

    const marked = tabs().filter((tab) => tab.querySelector(".floor-rail-badge") !== null);
    expect(marked.map((tab) => tab.id)).toEqual(["floor-tab-setup"]);
    expect(marked[0]?.getAttribute("aria-label")).toBe(
      `${t("floor.tabs.setup")}, ${t("floor.tabs.waiting")}`,
    );
  });

  it("draws the schedule beside the work on a wide screen", async () => {
    await open("/organizer/cup/floor/data");

    expect(tabs()).toHaveLength(8);
    expect(host?.querySelector(".floor-schedule")).not.toBeNull();
  });

  it("makes the schedule the last tab on a narrow screen", async () => {
    stubViewport(true);
    await open("/organizer/cup/floor/data");

    const last = tabs()[tabs().length - 1];
    expect(tabs()).toHaveLength(9);
    expect(last?.getAttribute("aria-label")).toBe(t("floor.tabs.schedule"));
    expect(host?.querySelector(".floor-schedule")).toBeNull();

    act(() => void last?.dispatchEvent(new MouseEvent("click", { bubbles: true })));

    expect(selected()).toBe("floor-tab-schedule");
    expect(host?.querySelector(".floor-schedule")).not.toBeNull();
    expect(host?.querySelector<HTMLElement>(".floor-work")?.hidden).toBe(true);
  });

  it("draws no schedule without one being planned", async () => {
    stubViewport(true);
    await open("/organizer/cup/floor/data", summary({ plan_schedule: false }));

    expect(tabs()).toHaveLength(8);
    expect(host?.querySelector(".floor-schedule")).toBeNull();
  });

  it("asks before leaving Setup with an unsaved piste", async () => {
    await open("/organizer/cup/floor/setup");
    const pistesTab = [
      ...(host?.querySelectorAll<HTMLButtonElement>(".setup-tabs [role=tab]") ?? []),
    ].find((tab) => tab.textContent === t("floor.setup.tabs.pistes"));
    act(() => void pistesTab?.dispatchEvent(new MouseEvent("click", { bubbles: true })));
    const add = [...(host?.querySelectorAll("button") ?? [])].find(
      (button) => button.textContent === t("floor.setup.pistes.add"),
    );
    act(() => void add?.dispatchEvent(new MouseEvent("click", { bubbles: true })));
    const data = tabs().find((tab) => tab.id === "floor-tab-data");

    act(() => void data?.dispatchEvent(new MouseEvent("click", { bubbles: true })));

    expect(host?.querySelector("dialog")?.textContent).toContain(t("console.leaveSetup.title"));
    expect(selected()).toBe("floor-tab-setup");
  });
});
