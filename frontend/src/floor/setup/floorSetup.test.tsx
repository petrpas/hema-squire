// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "../../i18n";
import { type FloorFormatOut, type FloorSetup, floorApi } from "../floorApi";
import FloorSetupTab from "./FloorSetupTab";

// Floor Setup's tabs (spec floor-setup): which tabs scope shows, where Setup
// opens, drafts kept across tabs, the day dialog moving a discipline, the
// team points sentence and the take-over offered by weapon.

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const t = i18n.getFixedT("cs");

function format(discipline_id: number, fields: Partial<FloorFormatOut> = {}): FloorFormatOut {
  return {
    discipline_id,
    pool_min: 5,
    pool_max: 7,
    advance: null,
    third_place: true,
    referees_pool: 1,
    referees_elim: 1,
    slot_pool_bout: 4,
    slot_elim_bout: 6,
    pause_between_pools: 10,
    slot_team_match: null,
    points_pool: null,
    points_elim: null,
    points_team_bout: null,
    takes_pools_from: null,
    stored: true,
    missing: [],
    ...fields,
  };
}

function setup(fields: Partial<FloorSetup> = {}): FloorSetup {
  return {
    disciplines: [
      { id: 1, slug: "LS", name: "Longsword", kind: "individual", weapon: "LS" },
      { id: 2, slug: "SB", name: "Sabre", kind: "individual", weapon: "SB" },
      { id: 3, slug: "LT", name: "Longsword Teams", kind: "team", weapon: "ls", team_min: 3 },
    ],
    persons: [],
    scope: { plan_schedule: true, multi_day: true, plan_officials: false },
    days: {
      stored: true,
      days: [
        { date: "2099-12-05", start: "09:00", end: "19:00", breaks: [], discipline_ids: [1, 3] },
        { date: "2099-12-06", start: "09:00", end: "19:00", breaks: [], discipline_ids: [2] },
      ],
    },
    pistes: [],
    formats: [format(1), format(2), format(3, { slot_team_match: 25, points_team_bout: 5 })],
    officials: [],
    params: { finals: "elimination", min_rest_minutes: 10 },
    preferences: { pool_size: "larger", club_weight: 10, nationality_weight: 3 },
    ...fields,
  };
}

let host: HTMLElement | null = null;
let root: Root | null = null;
let dirty = false;

async function mount(answer: FloorSetup, missing: string[] = []) {
  vi.spyOn(floorApi, "setup").mockResolvedValue(answer);
  host = document.createElement("div");
  document.body.append(host);
  root = createRoot(host);
  act(() =>
    root?.render(
      <FloorSetupTab
        slug="cup"
        missing={missing}
        onSaved={() => {}}
        onDirtyChange={(value) => {
          dirty = value;
        }}
      />,
    ),
  );
  for (let i = 0; i < 3; i++) {
    await act(async () => {
      await Promise.resolve();
    });
  }
}

function tabs(): HTMLButtonElement[] {
  return [...(host?.querySelectorAll<HTMLButtonElement>(".setup-tabs [role=tab]") ?? [])];
}

function tab(label: string): HTMLButtonElement | undefined {
  return tabs().find((button) => button.textContent?.startsWith(label));
}

function visible(): HTMLElement | null {
  return host?.querySelector<HTMLElement>("[role=tabpanel]:not([hidden])") ?? null;
}

function click(element: Element | null | undefined) {
  act(() => void element?.dispatchEvent(new MouseEvent("click", { bubbles: true })));
}

function buttonIn(scope: Element | null | undefined, label: string) {
  return [...(scope?.querySelectorAll("button") ?? [])].find((b) => b.textContent === label);
}

beforeEach(() => {
  void i18n.changeLanguage("cs");
  dirty = false;
});

afterEach(() => {
  act(() => root?.unmount());
  host?.remove();
  host = null;
  vi.restoreAllMocks();
});

describe("floor Setup's tabs", () => {
  it("offers what scope plans, in order", async () => {
    await mount(setup());

    expect(tabs().map((button) => button.textContent)).toEqual([
      t("floor.setup.tabs.scope"),
      t("floor.setup.tabs.schedule"),
      t("floor.setup.tabs.formats"),
      t("floor.setup.tabs.pistes"),
      t("floor.setup.tabs.params"),
    ]);
  });

  it("offers only scope and disciplines without a schedule", async () => {
    await mount(
      setup({ scope: { plan_schedule: false, multi_day: false, plan_officials: false } }),
    );

    expect(tabs().map((button) => button.textContent)).toEqual([
      t("floor.setup.tabs.scope"),
      t("floor.setup.tabs.formats"),
    ]);
  });

  it("opens where something is missing, and marks that tab", async () => {
    await mount(setup(), ["format:2"]);

    expect(tab(t("floor.setup.tabs.formats"))?.getAttribute("aria-selected")).toBe("true");
    expect(tab(t("floor.setup.tabs.formats"))?.querySelector(".tab-mark")).not.toBeNull();
  });

  it("keeps an unsaved edit across a tab switch and marks it", async () => {
    await mount(setup());
    click(tab(t("floor.setup.tabs.params")));
    const rest = visible()?.querySelector<HTMLInputElement>("#floor-param-min-rest");
    act(() => {
      if (rest) {
        const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
        setter?.call(rest, "25");
        rest.dispatchEvent(new Event("input", { bubbles: true }));
      }
    });

    click(tab(t("floor.setup.tabs.pistes")));
    click(tab(t("floor.setup.tabs.params")));

    expect(visible()?.querySelector<HTMLInputElement>("#floor-param-min-rest")?.value).toBe("25");
    expect(tab(t("floor.setup.tabs.params"))?.querySelector(".tab-dirty-mark")).not.toBeNull();
    expect(dirty).toBe(true);
  });
});

describe("the schedule tab", () => {
  it("moves a discipline ticked in another day's dialog", async () => {
    await mount(setup());
    click(tab(t("floor.setup.tabs.schedule")));
    const sunday = visible()?.querySelectorAll("tbody tr")[1];
    click(buttonIn(sunday, t("floor.setup.edit")));
    const longsword = [...(host?.querySelectorAll("dialog label") ?? [])].find((label) =>
      label.textContent?.startsWith("Longsword"),
    );
    expect(longsword?.textContent).toContain("(teď");

    click(longsword?.querySelector("input"));
    click(buttonIn(host?.querySelector("dialog"), t("floor.setup.done")));

    const rows = [...(visible()?.querySelectorAll("tbody tr") ?? [])];
    expect(rows[0]?.textContent).not.toContain("Longsword,");
    expect(rows[1]?.textContent).toContain("Longsword");
    expect(dirty).toBe(true);
  });
});

describe("the disciplines tab", () => {
  it("states a team's points per bout and the match total", async () => {
    await mount(setup());
    click(tab(t("floor.setup.tabs.formats")));

    expect(visible()?.textContent).toContain(t("floor.setup.formats.teamTotal", { total: 45 }));
  });

  it("offers a take-over from the same weapon only", async () => {
    await mount(setup());
    click(tab(t("floor.setup.tabs.formats")));
    const teams = [...(visible()?.querySelectorAll(".floor-format") ?? [])].find(
      (section) => section.querySelector("h3")?.textContent === "Longsword Teams",
    );
    const options = [...(teams?.querySelectorAll("select option") ?? [])].map((o) => o.textContent);

    expect(options).toEqual([t("floor.setup.formats.ownPools"), "Longsword"]);
  });
});
