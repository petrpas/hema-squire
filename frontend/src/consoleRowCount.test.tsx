// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter, Outlet, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, type Sheet, type SheetRow, type TournamentDetail } from "./api";
import Console from "./Console";
import i18n from "./i18n";

// The counting column left of the fencer's own number (spec `etl-console`,
// Position in the list): the organizer reads it to learn how many fencers
// stand, which the fixed number cannot answer — it names a fencer, carries
// gaps, and stands out of sequence where a backdated row was numbered late.

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const detail = {
  slug: "cup",
  display_name: "Cup",
  date: "2099-12-05",
  published_at: "2026-01-01T00:00:00Z",
  feature_schedule: false,
  feature_payments: false,
  feature_teams: false,
  feature_extras: false,
  registrations_kept_by: "squire",
  is_event: false,
  disciplines: [{ slug: "D0", kind: "individual" }],
} as unknown as TournamentDetail;

function row(name: string, number: number | null, fields: Partial<SheetRow> = {}): SheetRow {
  return {
    id: `reg:${name}`,
    number,
    name,
    nationality: "CZ",
    club: "Twerchhau",
    disciplines: [],
    substitute_for: [],
    conditional: [],
    queued_since: {},
    teams: [],
    state: "reserved",
    registration_id: 1,
    vs: null,
    paid: false,
    registered_at: null,
    total_amount: null,
    problems: null,
    weapon_rentals: [],
    afterparty: false,
    ...fields,
  } as unknown as SheetRow;
}

let host: HTMLElement | null = null;

async function openConsole(rows: SheetRow[]): Promise<HTMLElement> {
  vi.spyOn(api, "account").mockResolvedValue({ display_name: "O" } as never);
  vi.spyOn(api, "consoleTournament").mockResolvedValue(detail as never);
  vi.spyOn(api, "sheet").mockResolvedValue({ rows, edits: [] } as unknown as Sheet);
  vi.spyOn(api, "operations").mockResolvedValue({ running: null, concluded: [] } as never);
  host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  act(() =>
    root.render(
      <MemoryRouter initialEntries={["/t/cup/console/fencers"]}>
        <Routes>
          <Route element={<Outlet context={{ onLogout: () => {} }} />}>
            <Route
              path="/t/cup/console/fencers"
              element={<Console tournament={detail} phase="fencers" />}
            />
          </Route>
        </Routes>
      </MemoryRouter>,
    ),
  );
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
  });
  return host;
}

/** The two leading cells of every row: the count, then the fencer's number. */
function leading(page: HTMLElement): [string, string][] {
  return [...page.querySelectorAll(".sheet-table tbody tr")].map((tr) => {
    const cells = [...tr.querySelectorAll("td")];
    return [cells[0]?.textContent ?? "", cells[1]?.textContent ?? ""];
  });
}

afterEach(() => {
  host?.remove();
  host = null;
});

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("the fencer list's counting column", () => {
  it("stands left of the fencer's number and counts from one", async () => {
    const page = await openConsole([row("A", 7), row("B", 12), row("C", 3)]);

    const labels = [...page.querySelectorAll(".sheet-table thead th")].map((th) => th.textContent);
    // the count is the table's gutter and carries no heading; the fixed
    // number's column is headed ID and each number marked #
    expect(labels[0]).toBe("");
    expect(labels[1]).toBe(i18n.t("column.number"));
    // the count runs 1, 2, 3 whatever numbers the fencers carry
    expect(leading(page)).toEqual([
      ["1", "#7"],
      ["2", "#12"],
      ["3", "#3"],
    ]);
  });

  it("leaves a removed row out of the count, which counts the fencers who stand", async () => {
    const page = await openConsole([
      row("A", 1),
      row("B", 2, { _deleted: true, _removed_in: "fencers" }),
      row("C", 3),
    ]);

    // the struck-through row keeps its own number and takes no place in the
    // count: the last number read is how many fencers the tournament has
    expect(leading(page)).toEqual([
      ["1", "#1"],
      ["", "#2"],
      ["2", "#3"],
    ]);
  });
});
