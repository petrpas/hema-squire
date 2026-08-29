// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter, Outlet, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import Console from "./Console";
import { type Sheet, type Tournament, api } from "./api";

// The fencer list follows a concluded operation: nothing the organizer does
// (spec `etl-console`, The fencer list follows a concluded operation).

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const tournament = {
  slug: "cup",
  display_name: "Cup",
  date: "2026-12-05",
  feature_schedule: false,
  feature_payments: false,
  feature_teams: false,
  feature_extras: false,
} as unknown as Tournament;

const emptySheet = { rows: [], edits: [] } as unknown as Sheet;

let host: HTMLElement | null = null;

function mount() {
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
              element={<Console tournament={tournament} phase="fencers" />}
            />
          </Route>
        </Routes>
      </MemoryRouter>,
    ),
  );
}

async function settle() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
  });
}

beforeEach(() => {
  vi.restoreAllMocks();
  vi.spyOn(api, "account").mockResolvedValue({ display_name: "O" } as never);
  vi.spyOn(api, "tournament").mockResolvedValue(tournament as never);
});

afterEach(() => {
  host?.remove();
  host = null;
  vi.useRealTimers();
});

describe("the console and its running work", () => {
  it("reloads the fencer list when an operation lands, with no user action", async () => {
    vi.useFakeTimers();
    const sheet = vi.spyOn(api, "sheet").mockResolvedValue(emptySheet);
    vi.spyOn(api, "operations")
      .mockResolvedValueOnce({
        running: {
          id: 1,
          kind: "match",
          status: "running",
          total: 4,
          done: 1,
          started_at: "2026-04-01T14:32:00Z",
          finished_at: null,
          outcome: {},
        },
        concluded: [],
      })
      .mockResolvedValue({ running: null, concluded: [] });

    mount();
    await act(async () => {});
    expect(sheet).toHaveBeenCalledTimes(1);

    // the poll notices the landing and the list reloads itself
    await act(async () => {
      vi.advanceTimersByTime(2000);
    });
    expect(sheet).toHaveBeenCalledTimes(2);
  });

  it("carries the indicator on a phase that did not start the work", async () => {
    vi.spyOn(api, "sheet").mockResolvedValue(emptySheet);
    vi.spyOn(api, "operations").mockResolvedValue({
      running: {
        id: 1,
        kind: "parse",
        status: "running",
        total: 220,
        done: 60,
        started_at: "2026-04-01T14:32:00Z",
        finished_at: null,
        outcome: {},
      },
      concluded: [],
    });

    mount();
    await settle();

    // Fencers is not the phase that started the import, and still says so
    expect(host?.querySelector(".operation-indicator")?.textContent).toContain("220");
  });

  it("shows no indicator when nothing is running", async () => {
    vi.spyOn(api, "sheet").mockResolvedValue(emptySheet);
    vi.spyOn(api, "operations").mockResolvedValue({ running: null, concluded: [] });

    mount();
    await settle();

    expect(host?.querySelector(".operation-indicator")).toBeNull();
  });
});
