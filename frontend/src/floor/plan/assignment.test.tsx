// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../api";
import i18n from "../../i18n";
import { type Assignments, type FloorSetup, officialsApi } from "../floorApi";
import { AssignmentSection, useAssignments } from "./AssignmentSection";

// Obsazení (spec floor-officials): a seat is set and pinned here, and a hard
// rule refuses it by name.

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const t = i18n.getFixedT("cs");

const setup = {
  disciplines: [{ id: 1, slug: "LS", name: "Longsword", kind: "individual" }],
  persons: [],
  scope: { plan_schedule: true, multi_day: false, plan_officials: true },
  days: { stored: true, days: [] },
  pistes: [{ id: 5, name: "1", serves: [{ discipline_id: 1, reserve: false }] }],
  formats: [],
  officials: [
    {
      id: 8,
      name: "Eva",
      person_key: null,
      main: true,
      serves: [{ discipline_id: 1, reserve: false }],
      days: [],
      link_lost: false,
    },
    {
      id: 9,
      name: "Jan",
      person_key: null,
      main: true,
      serves: [{ discipline_id: 1, reserve: false }],
      days: [],
      link_lost: false,
    },
  ],
  params: { finals: "elimination", min_rest_minutes: 10 },
  preferences: { pool_size: "larger", club_weight: 10, nationality_weight: 3 },
} satisfies FloorSetup;

const data: Assignments = {
  published: true,
  blocks: [
    {
      key: "5:LS:pool:1",
      discipline_id: 1,
      piste_id: 5,
      day: "2099-12-05",
      start: "09:00",
      end: "10:30",
      activities: ["LS:pool:1"],
      seats: [{ id: 21, role: "referee", slot: 0, official_id: null, name: null, pinned: false }],
    },
  ],
  unmatched: [],
  conflicts: [],
};

/** The section with its data read as the Plan tab reads it, shared with
 *  the operations beside it. */
function Harness() {
  const { data: view, load } = useAssignments("cup");
  return <AssignmentSection slug="cup" setup={setup} data={view} load={load} />;
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

async function mount() {
  host = document.createElement("div");
  document.body.append(host);
  root = createRoot(host);
  act(() => root?.render(<Harness />));
  await settle();
}

function choose(value: string) {
  const select = host?.querySelector("select");
  if (!select) return;
  act(() => {
    Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value")?.set?.call(select, value);
    select.dispatchEvent(new Event("change", { bubbles: true }));
  });
}

beforeEach(() => void i18n.changeLanguage("cs"));

afterEach(() => {
  act(() => root?.unmount());
  host?.remove();
  host = null;
  vi.restoreAllMocks();
});

describe("Obsazení", () => {
  it("states an unfilled seat and pins the official chosen for it", async () => {
    vi.spyOn(officialsApi, "view").mockResolvedValue(data);
    const seat = vi.spyOn(officialsApi, "seat").mockResolvedValue(undefined);
    await mount();
    expect(host?.textContent).toContain(t("floor.officials.unfilled"));

    choose("8");
    await settle();

    expect(seat).toHaveBeenCalledWith("cup", 21, 8, true);
  });

  it("names the hard rule that refuses a seat", async () => {
    vi.spyOn(officialsApi, "view").mockResolvedValue(data);
    vi.spyOn(officialsApi, "seat").mockRejectedValue(new ApiError(409, "fencing"));
    await mount();

    choose("9");
    await settle();

    expect(host?.textContent).toContain(t("floor.officials.rules.fencing"));
  });
});
