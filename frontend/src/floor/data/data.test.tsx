// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../../api";
import i18n from "../../i18n";
import {
  checkinApi,
  type DataSheet,
  type FloorSetup,
  floorApi,
  type SheetRow,
  sheetApi,
} from "../floorApi";
import DataTab from "./DataTab";

// The Data sheet (spec floor-data): the office's columns in the server's
// seeding order, corrected cells marked, a withdrawn row struck through with
// its "Vrátit", read-only once check-in closed, and the ratings refresh in the
// panel fetching for the floor rather than the office.

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const t = i18n.getFixedT("cs");

const setup = {
  disciplines: [
    { id: 1, slug: "LS", name: "Longsword", kind: "individual" },
    { id: 2, slug: "SB", name: "Sabre", kind: "individual" },
  ],
} as unknown as FloorSetup;

function person(name: string, fields: Partial<SheetRow> = {}): SheetRow {
  const key = `reg:${name}`;
  return {
    person: key,
    entry_key: `${key}@2`,
    name,
    club: "Brno",
    nationality: "CZ",
    hr_id: 11,
    rating: null,
    rank: null,
    local: false,
    edited: [],
    paid: true,
    withdrawn: false,
    added: false,
    ...fields,
  };
}

function sheet(fields: Partial<DataSheet> = {}): DataSheet {
  return {
    discipline: { id: 2, slug: "SB", name: "Sabre", kind: "individual" },
    closed_at: null,
    fetched_at: null,
    missing: 2,
    count: 1,
    rows: [
      person("Boris", { rating: 1700, rank: 12, edited: ["rating"] }),
      person("Adéla", { withdrawn: true }),
    ],
    teams: [],
    persons: [],
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

async function mount(answer: DataSheet) {
  vi.spyOn(floorApi, "setup").mockResolvedValue(setup);
  vi.spyOn(sheetApi, "view").mockResolvedValue(answer);
  host = document.createElement("div");
  document.body.append(host);
  root = createRoot(host);
  act(() =>
    root?.render(
      <MemoryRouter>
        <DataTab slug="cup" discipline="SB" keptByOrganizer={false} />
      </MemoryRouter>,
    ),
  );
  await settle();
}

function click(element: Element | null | undefined) {
  act(() => void element?.dispatchEvent(new MouseEvent("click", { bubbles: true })));
}

function button(text: string): HTMLButtonElement | undefined {
  return [...(host?.querySelectorAll<HTMLButtonElement>("button") ?? [])].find(
    (candidate) => candidate.textContent === text,
  );
}

beforeEach(() => {
  void i18n.changeLanguage("cs");
  vi.stubGlobal("matchMedia", () => ({
    matches: false,
    addEventListener: () => {},
    removeEventListener: () => {},
  }));
});

afterEach(() => {
  act(() => root?.unmount());
  host?.remove();
  host = null;
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("the Data sheet", () => {
  it("states the office's columns in the order the server seeds", async () => {
    await mount(sheet());

    const headings = [...(host?.querySelectorAll("thead th") ?? [])].map((th) => th.textContent);
    expect(headings).toEqual([
      "",
      t("export.column.name"),
      t("export.column.nat"),
      t("export.column.club"),
      t("export.column.hr_id"),
      t("export.column.rating"),
      t("export.column.rank"),
      t("export.column.paid"),
      t("export.column.action"),
    ]);
    const names = [...(host?.querySelectorAll("tbody tr") ?? [])].map(
      (tr) => tr.querySelectorAll("td")[1]?.textContent,
    );
    expect(names).toEqual(["Boris", "Adéla"]);
    expect(host?.querySelector(".floor-strip [aria-selected=true]")?.textContent).toBe("Sabre");
    const profile = host?.querySelector<HTMLAnchorElement>("tbody tr a.sheet-hr-link");
    expect(profile?.href).toBe("https://hemaratings.com/fighters/details/11/");
  });

  it("marks a corrected cell and strikes a withdrawn row through", async () => {
    const undo = vi.spyOn(checkinApi, "undoWithdrawal").mockResolvedValue();
    await mount(sheet());

    const [boris, adela] = [...(host?.querySelectorAll("tbody tr") ?? [])];
    expect(boris?.querySelector(".cell-edited")?.textContent).toBe("1700");
    expect(adela?.className).toBe("row-deleted");

    click(button(t("floor.data.restore")));
    await settle();

    expect(undo).toHaveBeenCalledWith("cup", "reg:Adéla@2");
  });

  it("refreshes the ratings for the floor, never through the office's snapshot", async () => {
    const office = vi.spyOn(api, "ratingsSnapshot");
    const refresh = vi.spyOn(sheetApi, "refresh").mockResolvedValue({ ratings: 1, fencers: 2 });
    await mount(sheet());
    const panel = host?.querySelector("aside.rail");
    expect(panel?.textContent).toContain(t("export.ratingsState.never"));

    click(panel?.querySelector("button.icon-action"));
    await settle();

    expect(refresh).toHaveBeenCalledWith("cup", 2);
    expect(office).not.toHaveBeenCalled();
    expect(panel?.textContent).toContain(t("export.ratingsDone", { ratings: 1, fencers: 2 }));
  });

  it("adds a team from the panel, its members named as a registrant names them", async () => {
    const member = (name: string) => ({ ...person(name), person: `reg:${name}` });
    await mount(
      sheet({
        discipline: { id: 2, slug: "SB", name: "Sabre", kind: "team" },
        rows: [],
        teams: [
          {
            key: "team:1",
            name: "Draci",
            paid: true,
            withdrawn: false,
            added: false,
            members: [member("Eva")],
          },
        ],
        persons: [
          { key: "reg:Eva", name: "Eva", club: null },
          { key: "reg:Ota", name: "Ota", club: null },
        ],
      }),
    );
    const panel = host?.querySelector("aside.rail");
    const add = [...(panel?.querySelectorAll("button") ?? [])].find(
      (candidate) => candidate.textContent === t("floor.data.addTeam"),
    );
    expect(add).toBeDefined();

    click(add);

    // members are named as a registrant names them, never picked from a list:
    // one found in HEMA Ratings who is already on the floor is bound by HR ID
    expect(document.querySelector(".floor-add-people")).toBeNull();
    const named = vi.spyOn(sheetApi, "addTeam").mockResolvedValue({ key: "floorteam:1" });
    const inDialog = (text: string) =>
      [...document.querySelectorAll<HTMLButtonElement>("dialog button")].find(
        (candidate) => candidate.textContent === text,
      );
    click(inDialog(t("roster.add")));
    await settle();
    // the member dialog opens over the add dialog: its field is the last one
    const fields = [...document.querySelectorAll<HTMLInputElement>("dialog input")];
    const nameField = fields[fields.length - 1];
    act(() => {
      if (nameField === undefined) return;
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set?.call(
        nameField,
        "Jana",
      );
      nameField.dispatchEvent(new Event("input", { bubbles: true }));
    });
    click(inDialog(t("roster.confirmPlain")));
    await settle();
    const teamField = document.querySelector<HTMLInputElement>(".floor-add input");
    act(() => {
      if (teamField === null) return;
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set?.call(
        teamField,
        "Brno B",
      );
      teamField.dispatchEvent(new Event("input", { bubbles: true }));
    });
    click(inDialog(t("floor.data.addTeam")));
    await settle();

    expect(named).toHaveBeenCalledWith("cup", 2, "Brno B", [
      { person: { name: "Jana", hr_id: null, club: null, nationality: null } },
    ]);
  });

  it("is the snapshot, read-only, once check-in closed", async () => {
    await mount(sheet({ closed_at: "2099-12-05T09:30:00Z" }));

    expect(host?.querySelector(".cell-editable")).toBeNull();
    expect(button(t("floor.data.add"))).toBeUndefined();
    expect(button(t("floor.data.restore"))).toBeUndefined();
    const panel = host?.querySelector("aside.rail");
    expect(panel?.querySelector("button.icon-action")).toBeNull();
    expect(panel?.textContent).toContain("Prezence uzavřena");
  });
});
