// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter, Outlet, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import Console, { type Phase } from "./Console";
import { type Sheet, type Tournament, api } from "./api";
// the console renders in the deployment language, which is Czech in tests
import cs from "./i18n/cs.json";

// A draft's console draws every phase and none of them acts, each stating that
// its work begins at publication (spec etl-console, The console states what it
// is waiting for on a draft).

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const WAIT = cs.console.awaitsPublication;

function tournamentAt(published: string | null) {
  return {
    slug: "cup",
    display_name: "Cup",
    date: "2026-12-05",
    published_at: published,
    feature_schedule: false,
    feature_payments: true,
    feature_teams: true,
    feature_extras: false,
  } as unknown as Tournament;
}

const emptySheet = { rows: [], edits: [] } as unknown as Sheet;

let host: HTMLElement | null = null;

function mount(tournament: Tournament, phase: Phase) {
  host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  const path = `/t/cup/console/${phase}`;
  act(() =>
    root.render(
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route element={<Outlet context={{ onLogout: () => {} }} />}>
            <Route
              path={path}
              element={<Console tournament={tournament} phase={phase} />}
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

function text() {
  return host?.textContent ?? "";
}

beforeEach(() => {
  vi.restoreAllMocks();
  vi.spyOn(api, "account").mockResolvedValue({ display_name: "O" } as never);
  vi.spyOn(api, "sheet").mockResolvedValue(emptySheet);
  vi.spyOn(api, "operations").mockResolvedValue({ running: null, concluded: [] } as never);
});

afterEach(() => {
  host?.remove();
  host = null;
});

const DRAFT_PHASES: Phase[] = [
  "import",
  "fencers",
  "matching",
  "dedup",
  "payments",
  "export",
  "teams",
  "queue",
];

describe("a draft's phases", () => {
  beforeEach(() => {
    vi.spyOn(api, "tournament").mockResolvedValue(tournamentAt(null) as never);
  });

  it.each(DRAFT_PHASES)("states its wait on %s, in place of its body", async (phase) => {
    mount(tournamentAt(null), phase);
    await settle();

    expect(text()).toContain(WAIT);
    expect(host?.querySelector(".sheet-table")).toBeNull();
  });

  it("draws the whole phase strip, in the usual order", async () => {
    mount(tournamentAt(null), "import");
    await settle();

    const labels = [...(host?.querySelectorAll(".step-label") ?? [])].map(
      (step) => step.textContent,
    );
    expect(labels).toEqual([
      cs.phase.setup,
      cs.phase.import,
      cs.phase.fencers,
      cs.phase.matching,
      cs.phase.dedup,
      cs.phase.payments,
      cs.phase.export,
      cs.phase.teams,
      cs.phase.queue,
    ]);
  });

  it("opens the phase its URL names rather than redirecting", async () => {
    mount(tournamentAt(null), "matching");
    await settle();

    const active = host?.querySelector(".step.active .step-label");
    expect(active?.textContent).toBe(cs.phase.matching);
    expect(text()).toContain(WAIT);
  });

  it("states the wait once on Payments, not once per view", async () => {
    mount(tournamentAt(null), "payments");
    await settle();

    const said = text().split(WAIT).length - 1;
    expect(said).toBe(1);
  });

  it("offers no hand-entry control on Fencers", async () => {
    mount(tournamentAt(null), "fencers");
    await settle();

    expect(host?.querySelector(".manual-entry")).toBeNull();
    expect(text()).toContain(WAIT);
  });

  it("leaves Setup alone", async () => {
    vi.spyOn(api, "tournament").mockResolvedValue({
      ...tournamentAt(null),
      organizers: [],
      disciplines: [],
      extra_items: [],
      discounts: [],
      setup_missing: [],
    } as never);

    mount(tournamentAt(null), "setup");
    await settle();

    expect(text()).not.toContain(WAIT);
  });
});

describe("once published", () => {
  it("shows the phase's own body again", async () => {
    const published = tournamentAt("2026-09-01T00:00:00Z");
    vi.spyOn(api, "tournament").mockResolvedValue(published as never);

    mount(published, "fencers");
    await settle();

    expect(text()).not.toContain(WAIT);
    expect(host?.querySelector(".sheet-scroll")).not.toBeNull();
  });
});
