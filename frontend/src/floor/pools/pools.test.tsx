// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "../../i18n";
import { type DrawPool, type PoolsView, poolsApi, ringApi } from "../floorApi";
import RingScreen from "../ring/RingScreen";
import { DrawView } from "./DrawView";
import { PoolSheet } from "./PoolSheet";

// The draw, the sheet and the piste screen (specs floor-draw, floor-pools,
// floor-ring).

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const t = i18n.getFixedT("cs");

const pool: DrawPool = {
  number: 1,
  wave: 1,
  piste_id: 3,
  planned_start: null,
  members: [
    { key: "a", seed: 1 },
    { key: "b", seed: 3 },
    { key: "c", seed: 5 },
  ],
  bouts: [
    {
      id: 11,
      ordinal: 1,
      a: "a",
      b: "b",
      score_a: null,
      score_b: null,
      outcome_a: null,
      outcome_b: null,
      note: null,
      recorded_by: null,
      version: 0,
    },
    {
      id: 12,
      ordinal: 2,
      a: "b",
      b: "c",
      score_a: null,
      score_b: null,
      outcome_a: null,
      outcome_b: null,
      note: null,
      recorded_by: null,
      version: 0,
    },
  ],
};

const view: PoolsView = {
  state: "waiting",
  checkin_closed: true,
  names: { a: "Adéla", b: "Boris", c: "Cyril" },
  draw: {
    score: { snake: 1, club: 10, nationality: 0.5, wave: 0, total: 11.5 },
    previous_score: null,
    announced_at: null,
    closed_at: null,
    pools: [pool],
  },
};

let host: HTMLElement | null = null;
let root: Root | null = null;

async function settle() {
  for (let i = 0; i < 4; i++) {
    await act(async () => {
      await Promise.resolve();
    });
  }
}

function mount(node: React.ReactNode) {
  host = document.createElement("div");
  document.body.append(host);
  root = createRoot(host);
  act(() => root?.render(node));
}

function input(label: string): HTMLInputElement | null | undefined {
  return host?.querySelector<HTMLInputElement>(`input[aria-label="${label}"]`);
}

function type(element: HTMLInputElement | null | undefined, value: string) {
  if (!element) return;
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
  act(() => {
    setter?.call(element, value);
    element.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

beforeEach(() => void i18n.changeLanguage("cs"));

afterEach(() => {
  act(() => root?.unmount());
  host?.remove();
  host = null;
  vi.restoreAllMocks();
});

describe("the draw", () => {
  it("swaps the two fencers picked and shows the score broken down", async () => {
    const swap = vi.spyOn(poolsApi, "swap").mockResolvedValue(undefined);
    mount(
      <DrawView
        slug="cup"
        discipline={2}
        view={view}
        name={(k) => view.names[k] ?? k}
        pistes={new Map()}
        onChanged={() => {}}
      />,
    );
    const buttons = [...(host?.querySelectorAll(".floor-pool button") ?? [])];

    act(() => (buttons[1] as HTMLButtonElement).click());
    act(() => (buttons[2] as HTMLButtonElement).click());
    await settle();

    expect(swap).toHaveBeenCalledWith("cup", 2, "b", "c");
    expect(host?.textContent).toContain(t("floor.pools.club"));
  });
});

describe("the sheet", () => {
  it("saves a whole paper sheet at once", async () => {
    const transcribe = vi.spyOn(poolsApi, "transcribe").mockResolvedValue(undefined);
    mount(
      <PoolSheet
        slug="cup"
        discipline={2}
        pool={pool}
        name={(k) => view.names[k] ?? k}
        locked={false}
        onChanged={() => {}}
      />,
    );

    type(input(t("floor.pools.scoreOf", { name: "Adéla" })), "5");
    type(host?.querySelectorAll<HTMLInputElement>('input[type="number"]')[1], "3");
    type(host?.querySelectorAll<HTMLInputElement>('input[type="number"]')[2], "2");
    type(host?.querySelectorAll<HTMLInputElement>('input[type="number"]')[3], "5");
    const save = [...(host?.querySelectorAll("button") ?? [])].find((b) =>
      b.textContent?.startsWith(t("floor.pools.saveSheet", { count: 2 }).slice(0, 10)),
    );
    act(() => save?.click());
    await settle();

    expect(transcribe).toHaveBeenCalledWith("cup", 2, [
      {
        id: 11,
        score_a: 5,
        score_b: 3,
        outcome_a: "win",
        outcome_b: "loss",
        note: null,
        version: 0,
      },
      {
        id: 12,
        score_a: 2,
        score_b: 5,
        outcome_a: "loss",
        outcome_b: "win",
        note: null,
        version: 0,
      },
    ]);
  });
});

describe("the piste screen", () => {
  function open(hash: string) {
    mount(
      <MemoryRouter initialEntries={[`/floor/ring/3${hash}`]}>
        <Routes>
          <Route path="floor/ring/:piste" element={<RingScreen />} />
        </Routes>
      </MemoryRouter>,
    );
  }

  it("states that a revoked link is no longer valid", async () => {
    const { ApiError } = await import("../../api");
    vi.spyOn(ringApi, "current").mockRejectedValue(new ApiError(404, "ring_key_invalid"));
    open("#old-key-0001");
    await settle();

    expect(host?.textContent).toContain(t("floor.ring.invalid"));
  });

  it("records the current bout with the key from the fragment", async () => {
    vi.spyOn(ringApi, "current").mockResolvedValue({
      piste: "3",
      pool: {
        discipline_id: 2,
        number: 1,
        members: [],
        bouts: [
          {
            id: 11,
            ordinal: 1,
            a: "Adéla",
            b: "Boris",
            score_a: null,
            score_b: null,
            outcome_a: null,
            outcome_b: null,
            version: 0,
          },
        ],
      },
    });
    const record = vi.spyOn(ringApi, "record").mockResolvedValue(undefined);
    open("#key-0123456789");
    await settle();

    const plus = host?.querySelector<HTMLButtonElement>(
      `button[aria-label="${t("floor.ring.plus", { name: "Adéla" })}"]`,
    );
    for (let i = 0; i < 5; i++) act(() => plus?.click());
    const recordButton = [...(host?.querySelectorAll("button") ?? [])].find(
      (b) => b.textContent === t("floor.ring.record"),
    );
    act(() => recordButton?.click());
    await settle();

    expect(record).toHaveBeenCalledWith("key-0123456789", 11, {
      score_a: 5,
      score_b: 0,
      outcome_a: "win",
      outcome_b: "loss",
      version: 0,
    });
  });
});
