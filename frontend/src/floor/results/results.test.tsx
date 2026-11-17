// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
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

describe("Výsledky", () => {
  it("offers publishing once the standing exists, and states a discipline still waiting", async () => {
    vi.spyOn(resultsApi, "list").mockResolvedValue([
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
    ]);
    const publish = vi.spyOn(resultsApi, "publish").mockResolvedValue(undefined);
    await mount(<ResultsTab slug="cup" />);

    expect(host?.textContent).toContain(t("floor.results.bracketOpen"));
    const button = [...(host?.querySelectorAll("button") ?? [])].find(
      (b) => b.textContent === t("floor.results.publish"),
    );
    act(() => button?.click());

    expect(publish).toHaveBeenCalledWith("cup", 1);
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
