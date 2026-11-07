// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter, Outlet, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, type Sheet, type SheetRow, type TournamentDetail } from "./api";
import Console from "./Console";
import i18n from "./i18n";

// The fencer list's Team column as the table draws it (spec `etl-console`, The
// teams a row entered): where it stands, what a row with two teams says, and
// that a tournament with no team discipline is not widened by it.

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

function tournament(teams: boolean, kinds: ("individual" | "team")[]): TournamentDetail {
  return {
    slug: "cup",
    display_name: "Cup",
    date: "2099-12-05",
    published_at: "2026-01-01T00:00:00Z",
    feature_schedule: false,
    feature_payments: false,
    feature_teams: teams,
    feature_extras: false,
    registrations_kept_by: "squire",
    is_event: false,
    disciplines: kinds.map((kind, index) => ({ slug: `D${index}`, kind })),
  } as unknown as TournamentDetail;
}

function row(name: string, teams: SheetRow["teams"]): SheetRow {
  return {
    id: `reg:${name}`,
    number: 1,
    name,
    nationality: "CZ",
    club: "Twerchhau",
    disciplines: [],
    substitute_for: [],
    conditional: [],
    queued_since: {},
    teams,
    state: "reserved",
    registration_id: 1,
    vs: null,
    paid: false,
    registered_at: null,
    total_amount: null,
    problems: null,
    weapon_rentals: [],
    afterparty: false,
  } as unknown as SheetRow;
}

let host: HTMLElement | null = null;

async function openConsole(detail: TournamentDetail, rows: SheetRow[]): Promise<HTMLElement> {
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

function headers(page: HTMLElement): string[] {
  return [...page.querySelectorAll(".sheet-table thead th")].map((th) => th.textContent ?? "");
}

afterEach(() => {
  host?.remove();
  host = null;
});

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("the fencer list's team column", () => {
  it("stands between the club and the phase's own columns", async () => {
    const page = await openConsole(tournament(true, ["team", "individual"]), [
      row("Jan Novák", [{ name: "Rudá růže", discipline: "LS" }]),
    ]);

    const labels = headers(page);
    const club = labels.indexOf(i18n.t("column.club"));
    expect(labels[club + 1]).toBe(i18n.t("column.team"));
    expect(labels[club + 2]).toBe(i18n.t("column.disciplines"));
  });

  it("states both teams of a row that entered two, each with its discipline", async () => {
    const page = await openConsole(tournament(true, ["team", "team"]), [
      row("Jan Novák", [
        { name: "Rudá růže", discipline: "LS" },
        { name: "Ulice 2", discipline: "SA" },
      ]),
    ]);

    const cell = [...page.querySelectorAll(".sheet-table tbody td")][4];
    expect(cell?.textContent).toBe("Rudá růže (LS)Ulice 2 (SA)");
  });

  it("drops the discipline where the tournament has only one team discipline", async () => {
    const page = await openConsole(tournament(true, ["team", "individual"]), [
      row("Jan Novák", [{ name: "Rudá růže", discipline: "D0" }]),
    ]);

    const cell = [...page.querySelectorAll(".sheet-table tbody td")][4];
    expect(cell?.textContent).toBe("Rudá růže");
  });

  it("reads a dash on a row that entered none", async () => {
    const page = await openConsole(tournament(true, ["team", "individual"]), [
      row("Jan Novák", []),
    ]);

    expect([...page.querySelectorAll(".sheet-table tbody td")][4]?.textContent).toBe("—");
  });

  it("does not widen a tournament with no team discipline", async () => {
    const page = await openConsole(tournament(true, ["individual"]), [row("Jan Novák", [])]);

    expect(headers(page)).not.toContain(i18n.t("column.team"));
  });
});
