// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { OpenDiscipline, OpenTournament } from "./api";
import CapacityMeter from "./CapacityMeter";
import i18n from "./i18n";
import NextOpening from "./NextOpening";
import TournamentCard from "./TournamentCard";

// The night-skin home card and its parts (change add-fencer-night-skin): the
// cover tint follows the slug, the status block states registration's state,
// the meter is a static figure, and the next-opening strip shows only while
// it is worth watching.

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let host: HTMLElement | null = null;
let root: Root | null = null;

function render(node: React.ReactNode): HTMLElement {
  host = document.createElement("div");
  document.body.append(host);
  root = createRoot(host);
  act(() => root?.render(<MemoryRouter>{node}</MemoryRouter>));
  return host;
}

function tournament(over: Partial<OpenTournament> = {}): OpenTournament {
  return {
    slug: "brno-open",
    display_name: "Brno Open",
    subtitle: null,
    has_logo: false,
    logo_tint: null,
    cover_tint: null,
    short_code: null,
    date: "2026-11-20",
    city: "Brno",
    description: null,
    qualification_open: true,
    qualification_criteria: null,
    local_currency: "CZK",
    organizers: [],
    registration_status: "open",
    registration_opens_on: null,
    registration_opens_at: null,
    timezone: "Europe/Prague",
    server_time: new Date().toISOString(),
    registration_closes_on: "2026-11-15",
    entrant_count: 0,
    club_count: 0,
    disciplines: [],
    ...over,
  };
}

function discipline(over: Partial<OpenDiscipline> = {}): OpenDiscipline {
  return {
    slug: "LS",
    name: "Longsword Open",
    fee: 500,
    fee_eur: null,
    taken: 0,
    entered: 0,
    capacity: 32,
    queue_length: 0,
    ...over,
  };
}

beforeEach(async () => {
  await i18n.changeLanguage("cs");
});

afterEach(() => {
  act(() => root?.unmount());
  host?.remove();
  host = null;
  root = null;
  vi.useRealTimers();
});

const card = (over: Partial<OpenTournament> = {}) => (
  <ul>
    <TournamentCard tournament={tournament(over)} tab="open" position={1} />
  </ul>
);

describe("the card's cover", () => {
  it("wears the same tint for the same slug, every render", () => {
    const first = render(card()).querySelector(".home-card-cover")?.getAttribute("data-tint");
    const second = render(card({ display_name: "Renamed" }))
      .querySelector(".home-card-cover")
      ?.getAttribute("data-tint");
    expect(first).toMatch(/^(blue|green|yellow)$/);
    expect(second).toBe(first);
  });

  it("follows the logo's band over the slug, warm wearing yellow", () => {
    const slugTint = render(card()).querySelector(".home-card-cover")?.getAttribute("data-tint");
    const other = slugTint === "green" ? "blue" : "green";
    const tint = (logo_tint: OpenTournament["logo_tint"]) =>
      render(card({ has_logo: true, logo_tint }))
        .querySelector(".home-card-cover")
        ?.getAttribute("data-tint");
    expect(tint(other)).toBe(other);
    expect(tint("warm")).toBe("yellow");
    expect(tint(null)).toBe(slugTint);
  });

  it("wears the tint the organizer chose over the logo's band and the slug", () => {
    const tint = render(card({ has_logo: true, logo_tint: "warm", cover_tint: "blue" }))
      .querySelector(".home-card-cover")
      ?.getAttribute("data-tint");
    expect(tint).toBe("blue");
  });

  it("states open registration with its closing day, and rings the plate", () => {
    const page = render(card());
    expect(page.querySelector(".status-block")?.textContent).toBe("registraceotevřenado 15. 11.");
    expect(page.querySelector(".home-card-plate")?.getAttribute("data-ring")).toBe("open");
  });

  it("omits the closing line where there is no closing day", () => {
    const lines = render(card({ registration_closes_on: null })).querySelectorAll(
      ".status-block > span",
    );
    expect(lines).toHaveLength(2);
  });

  it("states nothing for a registration the organizer keeps, and never closed", () => {
    const page = render(card({ registration_status: "elsewhere", registration_closes_on: null }));
    expect(page.querySelector(".status-block")).toBeNull();
    expect(page.querySelector(".home-card-plate")?.getAttribute("data-ring")).toBe("rest");
  });

  it("shows the monogram where there is no logo", () => {
    const page = render(card({ display_name: "Brněnská šavle 2027" }));
    expect(page.querySelector(".home-card-plate")?.textContent).toBe("BŠ");
  });

  it("prefers the organizer's short code to the monogram", () => {
    const page = render(card({ display_name: "Pražský dlouhý meč 2027", short_code: "PDM" }));
    expect(page.querySelector(".home-card-plate")?.textContent).toBe("PDM");
  });
});

describe("the card's foot", () => {
  it("counts fencers and clubs in their plural forms", () => {
    const page = render(card({ entrant_count: 4, club_count: 2 }));
    expect(page.querySelector(".home-card-counts")?.textContent).toBe("4 šermíři · 2 kluby");
  });

  it("states no count before anyone is seated", () => {
    expect(render(card()).querySelector(".home-card-counts")).toBeNull();
  });
});

describe("familiar faces", () => {
  const people = [
    { initials: "KV", label: "Kateřina V." },
    { initials: "JN", label: "Jana N." },
  ];

  it("names each face and counts clubmates", () => {
    const page = render(
      card({ familiar: { basis: "club", country: null, total: 5, ranked: false, people } }),
    );
    const faces = page.querySelectorAll(".familiar-face");
    expect([...faces].map((face) => face.getAttribute("aria-label"))).toEqual([
      "Kateřina V.",
      "Jana N.",
    ]);
    expect(page.querySelector(".familiar-note")?.textContent).toBe("5 z tvého klubu");
  });

  it("claims a ranking only where the order follows one", () => {
    const note = (ranked: boolean) =>
      render(
        card({ familiar: { basis: "country", country: "CZ", total: 4, ranked, people } }),
      ).querySelector(".familiar-note")?.textContent;
    expect(note(true)).toBe("nejvýš hodnocení z CZ");
    expect(note(false)).toBe("4 z CZ");
  });

  it("leaves the foot to the counts without an account", () => {
    const page = render(card({ entrant_count: 3, club_count: 2 }));
    expect(page.querySelector(".familiar")).toBeNull();
    expect(page.querySelector(".home-card-counts")?.textContent).toBe("3 šermíři · 2 kluby");
  });
});

describe("the capacity meter", () => {
  it("states the figure as text and hides the track", () => {
    const page = render(
      <ul>
        <CapacityMeter discipline={discipline({ entered: 24 })} />
      </ul>,
    );
    expect(page.querySelector(".meter-figure")?.textContent).toBe("24/32");
    expect(page.querySelector(".meter-track")?.getAttribute("aria-hidden")).toBe("true");
    expect(page.querySelector<HTMLElement>(".meter-fill")?.style.width).toBe("75%");
  });

  it("states a full discipline with its queue instead of the fraction", () => {
    const page = render(
      <ul>
        <CapacityMeter discipline={discipline({ entered: 32, queue_length: 3 })} />
      </ul>,
    );
    expect(page.querySelector(".meter")?.hasAttribute("data-full")).toBe(true);
    expect(page.querySelector(".meter-figure")?.textContent).toBe("plno · +3 čekají");
  });
});

describe("the next registration opening", () => {
  const opensIn = (ms: number) =>
    tournament({
      registration_status: "opens_on",
      registration_closes_on: null,
      registration_opens_on: new Date(Date.now() + ms).toISOString().slice(0, 10),
      registration_opens_at: new Date(Date.now() + ms).toISOString(),
    });
  const DAY = 24 * 60 * 60 * 1000;

  it("is not rendered when the opening is more than a week away", () => {
    const page = render(<NextOpening announced={[opensIn(8 * DAY)]} onOpened={() => {}} />);
    expect(page.querySelector(".next-opening")).toBeNull();
  });

  it("names the soonest opening within the week", () => {
    const later = { ...opensIn(5 * DAY), slug: "later", display_name: "Later" };
    const page = render(<NextOpening announced={[later, opensIn(3 * DAY)]} onOpened={() => {}} />);
    expect(page.querySelector(".next-opening-name")?.textContent).toContain("Brno Open");
  });

  it("counts down inside the last day and gives way at the moment", () => {
    vi.useFakeTimers();
    const onOpened = vi.fn();
    const page = render(<NextOpening announced={[opensIn(3000)]} onOpened={onOpened} />);
    expect(page.querySelector(".next-opening-figure")?.textContent).toBe("00:03");
    act(() => {
      vi.advanceTimersByTime(4000);
    });
    expect(page.querySelector(".next-opening")).toBeNull();
    expect(onOpened).toHaveBeenCalledTimes(1);
  });
});
