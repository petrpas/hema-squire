// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "../../i18n";
import { publicFloorApi, resultsApi } from "../floorApi";
import { Itinerary } from "../public/Itinerary";
import { PublicResults } from "../public/PublicResults";
import ResultsTab from "./ResultsTab";

// Výsledky in the console and on the public page (specs floor-results,
// floor-public).

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const t = i18n.getFixedT("cs");

let host: HTMLElement | null = null;
let root: Root | null = null;

async function mount(node: React.ReactNode) {
  host = document.createElement("div");
  document.body.append(host);
  root = createRoot(host);
  act(() => root?.render(node));
  for (let i = 0; i < 4; i++) {
    await act(async () => {
      await Promise.resolve();
    });
  }
}

beforeEach(() => void i18n.changeLanguage("cs"));

afterEach(() => {
  act(() => root?.unmount());
  host?.remove();
  host = null;
  vi.restoreAllMocks();
});

const results = [
  {
    discipline_id: 1,
    slug: "LS",
    name: "Longsword",
    standing: [
      { place: 1, key: "a", name: "Adéla", club: "Brno", nationality: "CZ" },
      { place: 2, key: "b", name: "Boris", club: null, nationality: null },
    ],
    published_at: null,
  },
  { discipline_id: 2, slug: "SB", name: "Sabre", standing: null, published_at: null },
  { discipline_id: 3, slug: "RA", name: "Rapier", standing: null, published_at: null },
];

function panel(): Element | null | undefined {
  return host?.querySelector(
    `aside[aria-label="${t("rail.operations")} · ${t("floor.tabs.results")}"]`,
  );
}

describe("Výsledky", () => {
  it("shows one discipline at a time, its publish gate in the operations panel", async () => {
    vi.spyOn(resultsApi, "list").mockResolvedValue(results);
    const publish = vi.spyOn(resultsApi, "publish").mockResolvedValue(undefined);
    await mount(
      <MemoryRouter>
        <ResultsTab slug="cup" discipline="LS" />
      </MemoryRouter>,
    );

    const work = host?.querySelector(".floor-work");
    expect(work?.textContent).toContain("Adéla");
    expect(work?.querySelector("h2")?.textContent).not.toContain("Sabre");
    expect(work?.textContent).not.toContain(t("floor.results.publish"));
    const button = [...(panel()?.querySelectorAll("button") ?? [])].find(
      (b) => b.textContent === t("floor.results.publish"),
    );
    act(() => button?.click());

    expect(publish).toHaveBeenCalledWith("cup", 1);
  });

  it("states a discipline still waiting, with nothing to publish", async () => {
    vi.spyOn(resultsApi, "list").mockResolvedValue(results);
    await mount(
      <MemoryRouter>
        <ResultsTab slug="cup" discipline="SB" />
      </MemoryRouter>,
    );

    expect(host?.querySelector(".floor-work")?.textContent).toContain(
      t("floor.results.bracketOpen"),
    );
    expect(panel()?.textContent).toContain(t("floor.ops.idle.bracketOpen"));
    expect(panel()?.querySelector("button")).toBeNull();
  });

  it("opens at the discipline kept across the console where the address names none", async () => {
    vi.spyOn(resultsApi, "list").mockResolvedValue(results);
    await mount(
      <MemoryRouter>
        <ResultsTab slug="cup" fallback="RA" />
      </MemoryRouter>,
    );

    expect(host?.querySelector(".floor-strip [aria-selected=true]")?.textContent).toBe("Rapier");
  });
});

describe("the public floor", () => {
  it("lists the published standings", async () => {
    vi.spyOn(publicFloorApi, "results").mockResolvedValue([
      {
        discipline: "Longsword",
        slug: "LS",
        standing: [{ place: 1, name: "Adéla", club: "Brno", nationality: "CZ" }],
      },
    ]);
    await mount(<PublicResults slug="cup" />);

    expect(host?.textContent).toContain("Longsword");
    expect(host?.textContent).toContain("Adéla");
  });

  it("draws the fencer's own day only where there is one", async () => {
    vi.spyOn(publicFloorApi, "itinerary").mockResolvedValue([]);
    await mount(<Itinerary slug="cup" />);
    expect(host?.querySelector(".floor-itinerary")).toBeNull();
    act(() => root?.unmount());
    host?.remove();

    vi.spyOn(publicFloorApi, "itinerary").mockResolvedValue([
      {
        discipline: "Sabre",
        kind: "pool",
        number: 3,
        piste: "2",
        day: "2099-12-05",
        start: "10:00",
      },
    ]);
    await mount(<Itinerary slug="cup" />);

    expect(host?.textContent).toContain(t("floor.public.pool", { number: 3 }));
    expect(host?.textContent).toContain("10:00");
  });
});
