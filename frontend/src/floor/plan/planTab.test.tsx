// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "../../i18n";
import {
  type FloorSetup,
  floorApi,
  type PlanActivity,
  type PlanState,
  planApi,
  type Variant,
} from "../floorApi";
import { ScheduleGrid } from "../schedule/ScheduleGrid";
import PlanTab from "./PlanTab";

// The Plan tab (spec floor-plan): choosing a variant, the publish gate's
// obstacles, and the schedule grid's change marks.

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const t = i18n.getFixedT("cs");

const setup: FloorSetup = {
  disciplines: [
    { id: 1, slug: "LS", name: "Longsword", kind: "individual" },
    { id: 2, slug: "SB", name: "Sabre", kind: "individual" },
  ],
  persons: [],
  days: { stored: true, days: [{ date: "2099-12-05", start: "09:00", end: "19:00", breaks: [] }] },
  pistes: [
    { id: 11, name: "1", reserve: false, tag: null, days: ["2099-12-05"] },
    { id: 12, name: "2", reserve: false, tag: null, days: ["2099-12-05"] },
  ],
  formats: [],
  officials: [],
  params: {
    finals_last: true,
    prefer_larger_pools: true,
    club_weight: 10,
    nationality_weight: 3,
    min_rest_minutes: 10,
  },
};

function activity(id: string, piste: number, start: string, end: string): PlanActivity {
  return {
    id,
    discipline_id: 1,
    kind: "pool",
    ordinal: Number(id.split(":")[2] ?? 1),
    round: 0,
    piste_id: piste,
    day: "2099-12-05",
    start,
    end,
    final: false,
    size: 5,
  };
}

const metrics = {
  last_end: { "2099-12-05": "12:00" },
  exclusion_load: 0,
  collisions: 0,
  shortage: 0,
  average_pool: 5,
};

function variant(key: string, k: number): Variant {
  return {
    key,
    choices: [{ discipline_id: 1, k, day: "2099-12-05", sizes: [5, 5] }],
    metrics,
    activities: [activity("LS:pool:1", 11, "09:00", "09:45")],
  };
}

function plan(fields: Partial<PlanState> = {}): PlanState {
  return {
    working: null,
    published: null,
    history: [],
    diff: [],
    pins: [],
    obstacles: [],
    sensitivity: null,
    setup_missing: [],
    ...fields,
  };
}

let host: HTMLElement | null = null;
let root: Root | null = null;

async function settle() {
  for (let i = 0; i < 4; i++) {
    await act(async () => {
      await Promise.resolve();
    });
  }
}

async function mount(state: PlanState) {
  vi.spyOn(planApi, "state").mockResolvedValue(state);
  vi.spyOn(floorApi, "setup").mockResolvedValue(setup);
  host = document.createElement("div");
  document.body.append(host);
  root = createRoot(host);
  act(() => root?.render(<PlanTab slug="cup" onChanged={() => {}} />));
  await settle();
}

function button(text: string): HTMLButtonElement | undefined {
  return [...(host?.querySelectorAll("button") ?? [])].find((b) => b.textContent === text);
}

beforeEach(() => void i18n.changeLanguage("cs"));

afterEach(() => {
  act(() => root?.unmount());
  host?.remove();
  host = null;
  vi.restoreAllMocks();
});

describe("the Plan tab", () => {
  it("chooses the second variant as the working version", async () => {
    await mount(plan());
    vi.spyOn(planApi, "variants").mockResolvedValue({
      variants: [variant("1:2@0", 2), variant("1:3@0", 3)],
      infeasible: null,
      capped: [],
      empty: [],
    });
    const choose = vi.spyOn(planApi, "choose").mockResolvedValue(undefined);

    act(() => button(t("floor.plan.variants.ask"))?.click());
    await settle();
    const chooseButtons = [...(host?.querySelectorAll("button") ?? [])].filter(
      (b) => b.textContent === t("floor.plan.variants.choose"),
    );
    expect(chooseButtons).toHaveLength(2);
    expect(host?.textContent).toContain(t("floor.plan.variants.default"));

    act(() => chooseButtons[1]?.click());
    await settle();

    expect(choose).toHaveBeenCalledWith("cup", "1:3@0");
  });

  it("lists the obstacles and holds the publish gate shut", async () => {
    const working = {
      version: 2,
      status: "working" as const,
      created_at: "2099-12-01T10:00:00Z",
      choices: [],
      metrics,
      activities: [],
    };
    await mount(plan({ working, obstacles: ["shortage:1:2"] }));

    const publish = button(t("floor.plan.working.publish"));

    expect(host?.textContent).toContain(
      t("floor.plan.obstacles.shortage", { a: "Longsword", b: "Sabre" }),
    );
    expect(publish?.disabled).toBe(true);
  });

  it("names the pin that leaves no variant", async () => {
    await mount(plan());
    vi.spyOn(planApi, "variants").mockResolvedValue({
      variants: [],
      infeasible: {
        reason: "pin",
        subject: { kind: "day", target: "2", day: "2099-12-05" },
        minutes: 0,
        detail: "",
      },
      capped: [],
      empty: [],
    });

    act(() => button(t("floor.plan.variants.ask"))?.click());
    await settle();

    expect(host?.textContent).toContain(
      t("floor.plan.infeasible.pin.day", { name: "Sabre", day: "2099-12-05" }),
    );
  });
});

describe("the schedule grid", () => {
  it("states a moved, an added and a removed activity in words", () => {
    host = document.createElement("div");
    document.body.append(host);
    root = createRoot(host);
    act(() =>
      root?.render(
        <ScheduleGrid
          day="2099-12-05"
          activities={[
            activity("LS:pool:1", 12, "10:20", "11:05"),
            activity("LS:pool:3", 11, "09:00", "09:45"),
          ]}
          removed={[activity("LS:pool:2", 11, "10:00", "10:45")]}
          changes={[
            {
              activity: "LS:pool:1",
              kind: "moved",
              before: [11, "2099-12-05", "10:40"],
              after: [12, "2099-12-05", "10:20"],
            },
            {
              activity: "LS:pool:3",
              kind: "added",
              before: null,
              after: [11, "2099-12-05", "09:00"],
            },
            {
              activity: "LS:pool:2",
              kind: "removed",
              before: [11, "2099-12-05", "10:00"],
              after: null,
            },
          ]}
          setup={setup}
        />,
      ),
    );

    const marks = [...(host?.querySelectorAll(".floor-grid-mark") ?? [])].map((m) =>
      m.textContent?.trim(),
    );
    expect(marks.sort()).toEqual(
      [
        t("floor.schedule.change.added"),
        t("floor.schedule.change.moved"),
        t("floor.schedule.change.removed"),
      ].sort(),
    );
  });
});
