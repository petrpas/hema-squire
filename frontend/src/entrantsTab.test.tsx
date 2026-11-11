// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter, useLocation } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import {
  ApiError,
  type Availability,
  api,
  type EntrantRow,
  type Entrants,
  type FencerTournament,
  setToken,
} from "./api";
import i18n from "./i18n";
import { DisciplinesInfo } from "./TournamentFace";

// The detail page's Entrants tab: the public rosters, at an address of their
// own (spec public-entrants, fencer-home, routing).

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let host: HTMLElement | null = null;
let path = "";

function LocationProbe() {
  path = useLocation().pathname;
  return null;
}

function mount(at: string) {
  host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  act(() =>
    root.render(
      <MemoryRouter initialEntries={[at]}>
        <App />
        <LocationProbe />
      </MemoryRouter>,
    ),
  );
  return host;
}

async function settle() {
  await act(async () => {
    for (let i = 0; i < 8; i++) await Promise.resolve();
  });
}

function click(element: Element | null | undefined) {
  expect(element).toBeTruthy();
  act(() => (element as HTMLElement).dispatchEvent(new MouseEvent("click", { bubbles: true })));
}

const discipline = (slug: string, name: string, kind: "individual" | "team") => ({
  slug,
  name,
  ordinal: 1,
  weapon: "LS",
  gender: "open",
  material: "steel",
  kind,
  team_min: kind === "team" ? 2 : null,
  team_max: kind === "team" ? 4 : null,
  capacity: 2,
  fee: 800,
  fee_early: null,
  fee_eur: null,
  fee_early_eur: null,
  schedule_when: null,
  schedule_where: null,
  ruleset: null,
  identity_frozen: false,
});

const DETAIL = {
  slug: "spring-open",
  display_name: "Spring Open",
  subtitle: null,
  has_logo: false,
  date: "2099-05-01",
  city: null,
  address: null,
  description: null,
  qualification_open: true,
  qualification_criteria: null,
  registration_instructions: null,
  organizers: [],
  disciplines: [discipline("LS", "Longsword", "individual"), discipline("TM", "Teams", "team")],
  extra_items: [],
  discounts: [],
  local_currency: "CZK",
  eur_payments_enabled: false,
  currency_mode: "local",
  registration_opens: null,
  registration_opens_time: null,
  registration_closes: null,
  amendments_close: null,
  team_composition_deadline: null,
  timezone: "Europe/Prague",
  registration_opens_at: null,
  server_time: "2026-09-12T10:00:00Z",
  registrations_kept_by: "squire",
  external_registration_url: null,
  feature_schedule: false,
  feature_payments: true,
  feature_teams: true,
  feature_extras: false,
} as unknown as FencerTournament;

const AVAILABILITY = [
  { slug: "LS", kind: "individual", capacity: 2, taken: 2, entered: 1, free: 0, queue_length: 1 },
  { slug: "TM", kind: "team", capacity: 2, taken: 1, entered: 1, free: 1, queue_length: 0 },
] as unknown as Availability[];

const row = (number: number, name: string, over: Partial<EntrantRow> = {}): EntrantRow => ({
  number,
  name,
  nationality: "CZ",
  club: "Klub",
  hr_id: 100 + number,
  paid: "yes",
  faded: false,
  conditional: false,
  ...over,
});

const ENTRANTS: Entrants = {
  as_of: null,
  rosters: [
    {
      slug: "LS",
      name: "Longsword",
      kind: "individual",
      line: true,
      seated: [row(1, "Adéla"), row(2, "Boris", { paid: "no", faded: true })],
      queued: [row(1, "Cyril", { paid: null, conditional: true })],
    },
    {
      slug: "TM",
      name: "Teams",
      kind: "team",
      line: true,
      seated: [
        {
          number: 1,
          name: "Draci",
          paid: "yes",
          faded: false,
          members: [
            { name: "Eva", nationality: "CZE", club: "Klub X", hr_id: null },
            { name: "Jan", nationality: "SVK", club: "Klub X", hr_id: null },
          ],
        },
        { number: 2, name: "Vlci", paid: "yes", faded: false, members: [] },
      ],
      queued: [],
    },
    // a side event: its slug is its item id, which may read like a slug
    {
      slug: "LS",
      name: "Seminář",
      kind: "event",
      line: false,
      capacity: null,
      seated: [row(1, "Eva")],
      queued: [],
    },
  ],
};

function detailApi(entrants: Entrants = ENTRANTS, detail: FencerTournament = DETAIL) {
  vi.spyOn(api, "tournament").mockResolvedValue(detail);
  vi.spyOn(api, "availability").mockResolvedValue(AVAILABILITY);
  vi.spyOn(api, "entrants").mockResolvedValue(entrants);
  vi.spyOn(api, "openTournaments").mockResolvedValue([]);
  vi.spyOn(api, "heldTournaments").mockResolvedValue([]);
  vi.spyOn(api, "myTournaments").mockRejectedValue(new ApiError(401, "x"));
}

function tabLabels(page: HTMLElement): string[] {
  return [...page.querySelectorAll(".detail-tabs > *")].map((tab) => tab.textContent ?? "");
}

function cells(tr: Element): string[] {
  return [...tr.querySelectorAll("td")].map((td) => td.textContent ?? "");
}

beforeEach(async () => {
  vi.restoreAllMocks();
  setToken(null);
  await i18n.changeLanguage("en");
});

afterEach(() => {
  host?.remove();
  host = null;
});

describe("the Entrants tab", () => {
  it("stands second, after Tournament and before the registration tab", async () => {
    detailApi();
    const page = mount("/t/spring-open");
    await settle();

    expect(tabLabels(page)).toEqual([
      i18n.t("detail.tabs.tournament"),
      i18n.t("detail.tabs.entrants"),
      i18n.t("detail.tabs.register"),
    ]);
  });

  it("opens at the discipline its address names", async () => {
    detailApi();
    const page = mount("/t/spring-open/entrants/TM");
    await settle();

    const active = page.querySelector(".detail-tabs .active");
    expect(active?.textContent).toBe(i18n.t("detail.tabs.entrants"));
    expect(page.querySelector(".entrants-band .active")?.textContent).toContain("Teams");
    expect(page.querySelector(".entrant-team")?.textContent).toBe("Draci");
  });

  it("opens at the first discipline where the address names none", async () => {
    detailApi();
    const page = mount("/t/spring-open/entrants");
    await settle();

    expect(page.querySelector(".entrants-band .active")?.textContent).toContain("Longsword");
  });

  it("returns the address to the tournament's own when left", async () => {
    detailApi();
    const page = mount("/t/spring-open/entrants/LS");
    await settle();

    const tournament = [...page.querySelectorAll(".detail-tabs button")].find(
      (b) => b.textContent === i18n.t("detail.tabs.tournament"),
    );
    click(tournament);
    await settle();

    expect(path).toBe("/t/spring-open");
    expect(page.querySelector(".entrants")).toBeNull();
  });

  it("selecting a discipline changes the address", async () => {
    detailApi();
    const page = mount("/t/spring-open/entrants/LS");
    await settle();

    const teams = [...page.querySelectorAll(".entrants-band a")].find((a) =>
      a.textContent?.startsWith("Teams"),
    );
    click(teams);
    await settle();

    expect(path).toBe("/t/spring-open/entrants/TM");
  });

  it("opens a side event at its own address, apart from a discipline of the same slug", async () => {
    detailApi();
    const page = mount("/t/spring-open/entrants/events/LS");
    await settle();

    expect(page.querySelector(".entrants-band .active")?.textContent).toBe("Seminář");
    const names = [...page.querySelectorAll(".entrants-table tbody tr")].map(
      (tr) => tr.querySelectorAll("td")[1]?.textContent,
    );
    expect(names).toEqual(["Eva"]);
    expect(page.querySelector(".export-line")).toBeNull();
  });

  it("labels a capped side event's line with its capacity", async () => {
    detailApi({
      as_of: null,
      rosters: ENTRANTS.rosters.map((r) =>
        r.kind === "event" ? { ...r, line: true, capacity: 10 } : r,
      ),
    });
    const page = mount("/t/spring-open/entrants/events/LS");
    await settle();

    expect(page.querySelector(".export-line")?.textContent).toBe(
      i18n.t("export.line.limit", { capacity: 10 }),
    );
  });

  it("an unknown side event is not found", async () => {
    detailApi();
    const page = mount("/t/spring-open/entrants/events/99");
    await settle();

    expect(page.textContent).toContain(i18n.t("notFound.title"));
  });

  it("an unknown discipline is not found", async () => {
    detailApi();
    const page = mount("/t/spring-open/entrants/nope");
    await settle();

    expect(page.textContent).toContain(i18n.t("notFound.title"));
  });
});

describe("an event's Entrants tab", () => {
  const item = (id: number, name: string, category: string) => ({
    id,
    name,
    category,
    price: 300,
    price_eur: null,
    max_qty: 1,
    capacity: null,
  });
  const event = (items: ReturnType<typeof item>[]) =>
    ({
      ...DETAIL,
      is_event: true,
      disciplines: [],
      feature_extras: true,
      extra_items: items,
    }) as unknown as FencerTournament;
  const offersEntrants = (page: HTMLElement) =>
    page.querySelector('.detail-tabs a[href="/t/spring-open/entrants"]') !== null;

  it("is offered for a seminar nobody has taken yet", async () => {
    detailApi(
      { as_of: null, rosters: [] },
      event([item(7, "Seminar", "seminar"), item(8, "Party", "afterparty")]),
    );
    const page = mount("/t/spring-open");
    await settle();

    expect(offersEntrants(page)).toBe(true);
  });

  it("is offered for other program", async () => {
    detailApi({ as_of: null, rosters: [] }, event([item(7, "Castle tour", "other_action")]));
    const page = mount("/t/spring-open");
    await settle();

    expect(offersEntrants(page)).toBe(true);
  });

  it("is not offered for an afterparty and goods alone", async () => {
    detailApi(
      { as_of: null, rosters: [] },
      event([
        item(8, "Party", "afterparty"),
        item(9, "Shirt", "merch"),
        item(10, "Sword", "rental"),
      ]),
    );
    const page = mount("/t/spring-open");
    await settle();

    expect(offersEntrants(page)).toBe(false);
  });
});

describe("an individual roster", () => {
  it("fades the unpaid, draws the line and leaves a queued row's Paid empty", async () => {
    detailApi();
    const page = mount("/t/spring-open/entrants/LS");
    await settle();

    const rows = [...page.querySelectorAll(".entrants-table tbody tr")];
    expect(rows.map((tr) => tr.className)).toEqual(["", "muted", "export-line", ""]);
    // the sixth column is Paid
    expect(cells(rows[1]!)[5]).toBe(i18n.t("export.no"));
    expect(rows[2]?.textContent).toBe(i18n.t("export.line.queue"));
    const queued = cells(rows[3]!);
    expect(queued[0]).toBe("1");
    expect(queued[1]).toContain(i18n.t("entrants.conditional"));
    expect(queued[5]).toBe("");
  });

  it("leads an HRID to the fighter's HEMA Ratings profile", async () => {
    detailApi();
    const page = mount("/t/spring-open/entrants/LS");
    await settle();

    const link = page.querySelector<HTMLAnchorElement>(".entrants-table tbody a");
    expect(link?.textContent).toBe("101");
    expect(link?.href).toBe("https://hemaratings.com/fighters/details/101/");
    expect(link?.target).toBe("_blank");
  });

  it("names each discipline in the band without a count", async () => {
    detailApi();
    const page = mount("/t/spring-open/entrants/LS");
    await settle();

    expect([...page.querySelectorAll(".entrants-band a")].map((a) => a.textContent)).toEqual([
      "Longsword",
      "Teams",
      "Seminář",
    ]);
  });

  it("draws no line where the roster has none", async () => {
    detailApi({
      as_of: "2026-08-30T09:15:00Z",
      rosters: ENTRANTS.rosters.map((r) => ({ ...r, line: false, queued: [] }) as typeof r),
    });
    const page = mount("/t/spring-open/entrants/LS");
    await settle();

    expect(page.querySelector(".export-line")).toBeNull();
    // an organizer-kept roster dates itself
    expect(page.querySelector(".entrants .rail-hint")?.textContent).toContain("30.");
  });
});

describe("a team roster", () => {
  const rows = (page: HTMLElement) =>
    [...page.querySelectorAll(".entrants-table tbody tr")].map((tr) => cells(tr).join("|"));

  it("folds each team's members away, and says when none are named", async () => {
    detailApi();
    const page = mount("/t/spring-open/entrants/TM");
    await settle();

    // the team states the club all its members share, and no nationality,
    // since theirs differ
    expect(rows(page)).toEqual([
      `1|Draci||Klub X||${i18n.t("export.yes")}`,
      `2|Vlci||||${i18n.t("export.yes")}`,
      `|${i18n.t("entrants.membersPending")}`,
      i18n.t("export.line.capacity"),
    ]);
    // a team nobody is named to has nothing to open
    expect(page.querySelectorAll(".entrant-team-toggle")).toHaveLength(1);
  });

  it("opens a team onto its members and folds it again", async () => {
    detailApi();
    const page = mount("/t/spring-open/entrants/TM");
    await settle();

    const toggle = page.querySelector(".entrant-team-toggle");
    click(toggle);
    expect(toggle?.getAttribute("aria-expanded")).toBe("true");
    expect(rows(page).slice(0, 3)).toEqual([
      `1|Draci||Klub X||${i18n.t("export.yes")}`,
      "|Eva|CZE|Klub X||",
      "|Jan|SVK|Klub X||",
    ]);

    click(toggle);
    expect(rows(page)).toHaveLength(4);
  });
});

describe("the information screen's counts", () => {
  it("lead to each discipline's roster", async () => {
    detailApi();
    const page = mount("/t/spring-open");
    await settle();

    const links = [...page.querySelectorAll(".detail-list a")].map((a) => a.getAttribute("href"));
    expect(links).toEqual(["/t/spring-open/entrants/LS", "/t/spring-open/entrants/TM"]);
  });

  it("state who is shown above the line, not the seats held", async () => {
    detailApi();
    const page = mount("/t/spring-open");
    await settle();

    // two seats held, one of them by a row the organizer took out of the table
    const longsword = page.querySelector(".detail-list a");
    expect(longsword?.textContent).toBe(i18n.t("detail.fencersCount", { taken: 1, capacity: 2 }));
  });

  it("lead nowhere in the Setup preview", () => {
    host = document.createElement("div");
    document.body.append(host);
    const root = createRoot(host);
    act(() =>
      root.render(
        <MemoryRouter>
          <DisciplinesInfo detail={DETAIL} availability={AVAILABILITY} />
        </MemoryRouter>,
      ),
    );

    expect(host.querySelector("a")).toBeNull();
  });
});
