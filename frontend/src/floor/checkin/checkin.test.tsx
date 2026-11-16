// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "../../i18n";
import { checkinApi, type Desk, type Today } from "../floorApi";
import TodayTab from "../today/TodayTab";
import { POLL_MS } from "../usePolled";
import CheckinTab from "./CheckinTab";

// The desk and the overview (specs floor-checkin, floor-today).

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const t = i18n.getFixedT("cs");

const desk: Desk = {
  persons: [
    {
      key: "reg:1",
      name: "Adéla Nováková",
      club: "Brno",
      nationality: "CZ",
      local: false,
      arrived: false,
      entries: [
        { entry_key: "reg:1@1", discipline_id: 1, team: null, paid: false, withdrawn: false },
        { entry_key: "reg:1@2", discipline_id: 2, team: null, paid: true, withdrawn: false },
      ],
    },
    {
      key: "reg:2",
      name: "Boris",
      club: "Praha",
      nationality: null,
      local: false,
      arrived: true,
      entries: [
        { entry_key: "reg:2@2", discipline_id: 2, team: null, paid: true, withdrawn: false },
      ],
    },
  ],
  disciplines: [
    {
      id: 1,
      slug: "LS",
      name: "Longsword",
      kind: "individual",
      team_min: null,
      team_max: null,
      closed: false,
      closed_at: null,
      entered: 1,
      present: 0,
      n: null,
    },
    {
      id: 2,
      slug: "SB",
      name: "Sabre",
      kind: "individual",
      team_min: null,
      team_max: null,
      closed: false,
      closed_at: null,
      entered: 2,
      present: 1,
      n: null,
    },
  ],
  teams: [],
};

const today: Today = {
  rows: [
    {
      discipline_id: 2,
      slug: "SB",
      name: "Sabre",
      steps: { checkin: "closed", pools: "waiting", bracket: "waiting", results: "waiting" },
      slip: null,
    },
    {
      discipline_id: 1,
      slug: "LS",
      name: "Longsword",
      steps: { checkin: "open", pools: "waiting", bracket: "waiting", results: "waiting" },
      slip: null,
    },
  ],
  waiting: [{ tab: "checkin", discipline: "LS", code: "checkin_open" }],
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

async function render(node: React.ReactNode) {
  host = document.createElement("div");
  document.body.append(host);
  root = createRoot(host);
  act(() => root?.render(<MemoryRouter>{node}</MemoryRouter>));
  await settle();
}

beforeEach(() => void i18n.changeLanguage("cs"));

afterEach(() => {
  act(() => root?.unmount());
  host?.remove();
  host = null;
  vi.restoreAllMocks();
  vi.useRealTimers();
});

describe("the desk", () => {
  it("ticks a person once for every discipline", async () => {
    vi.spyOn(checkinApi, "desk").mockResolvedValue(desk);
    const arrive = vi.spyOn(checkinApi, "arrive").mockResolvedValue(undefined);
    await render(<CheckinTab slug="cup" />);

    const tick = host?.querySelector<HTMLInputElement>(
      `input[aria-label="${t("floor.checkin.tick", { name: "Adéla Nováková" })}"]`,
    );
    act(() => tick?.click());
    await settle();

    expect(arrive).toHaveBeenCalledWith("cup", "reg:1");
    expect(arrive).toHaveBeenCalledTimes(1);
  });

  it("shows unpaid and lists only the discipline at its address", async () => {
    vi.spyOn(checkinApi, "desk").mockResolvedValue(desk);
    await render(<CheckinTab slug="cup" discipline="LS" />);

    const names = [...(host?.querySelectorAll(".floor-desk tbody th") ?? [])].map(
      (th) => th.textContent,
    );
    expect(names).toEqual(["Adéla Nováková"]);
    expect(host?.textContent).toContain(t("floor.checkin.unpaid"));
  });

  it("states the close gate's impact before confirming", async () => {
    vi.spyOn(checkinApi, "desk").mockResolvedValue(desk);
    vi.spyOn(checkinApi, "impact").mockResolvedValue({
      n: 29,
      n_pool: 29,
      feasible: true,
      k: 5,
      sizes: [6, 5],
      published_k: 6,
      range: null,
      day: "2099-12-05",
      end_change: -25,
    });
    await render(<CheckinTab slug="cup" discipline="SB" />);

    const close = [...(host?.querySelectorAll("button") ?? [])].find(
      (b) => b.textContent === t("floor.checkin.close"),
    );
    act(() => close?.click());
    await settle();

    const text = host?.querySelector("dialog")?.textContent ?? "";
    expect(text).toContain("N = 29");
    expect(text).toContain(t("floor.checkin.impact.poolsInstead", { k: 5, was: 6 }));
    expect(text).toContain(t("floor.checkin.impact.earlier", { count: 25 }));
  });
});

describe("the overview", () => {
  it("states each step in words and links cells and waiting items to their step", async () => {
    vi.spyOn(checkinApi, "today").mockResolvedValue(today);
    await render(<TodayTab slug="cup" />);

    const sabre = [...(host?.querySelectorAll("tbody tr") ?? [])][0];
    const links = [...(sabre?.querySelectorAll("a") ?? [])];
    expect(links[0]?.textContent).toBe(t("floor.today.state.closed"));
    expect(links[1]?.getAttribute("href")).toBe("/organizer/cup/floor/pools/SB");
    const waiting = host?.querySelector(".rail-card a");
    expect(waiting?.getAttribute("href")).toBe("/organizer/cup/floor/checkin/LS");
  });

  it("refreshes every fifteen seconds and says when it last succeeded", async () => {
    vi.useFakeTimers();
    const fetch = vi
      .spyOn(checkinApi, "today")
      .mockResolvedValueOnce(today)
      .mockRejectedValueOnce(new Error("offline"));
    await render(<TodayTab slug="cup" />);
    expect(fetch).toHaveBeenCalledTimes(1);

    await act(async () => {
      vi.advanceTimersByTime(POLL_MS);
    });
    await settle();

    expect(fetch).toHaveBeenCalledTimes(2);
    // the last data stays, and the failure is stated in words
    expect(host?.querySelector("tbody")).not.toBeNull();
    expect(host?.textContent).toContain(t("floor.today.stale", { time: "" }).split(";")[0] ?? "");
  });
});
