// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, api, type ExportBandTab, type Queue, type SheetRow } from "../api";
import RosterTable from "../export/RosterTable";
import i18n from "../i18n";
import QueuePhase from "./QueuePhase";
import QueueRoster from "./QueueRoster";
import SeatingCard from "./SeatingCard";

// The Queue phase (spec `seating-queue`, Queue view for the organizer): the
// Export roster's rows, order and line, two arrows offered only where the
// server would act, refusals in words, and the settle action in the rail.

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

function row(id: string, name: string, fields: Partial<SheetRow> = {}): SheetRow {
  return {
    id,
    number: null,
    name,
    nationality: "CZ",
    club: null,
    hr_id: null,
    hr_name: null,
    hr_nationality: null,
    hr_club: null,
    disciplines: ["LS"],
    substitute_for: [],
    queued_since: {},
    state: "reserved",
    registration_id: Number(id.split(":")[1]),
    vs: null,
    paid: false,
    registered_at: "2026-03-01T08:00:00+00:00",
    total_amount: 1750,
    outstanding_amount: "1750.00",
    outstanding_currency: "CZK",
    problems: null,
    expires_at: "2026-03-12T10:00:00+00:00",
    paid_at: null,
    weapon_rentals: [],
    afterparty: false,
    aftersparring: false,
    notes: null,
    ...fields,
  } as SheetRow;
}

const queued = (id: string, name: string, moment: string, registeredAt = moment) =>
  row(id, name, {
    disciplines: [],
    substitute_for: ["LS"],
    queued_since: { LS: moment },
    registered_at: registeredAt,
    outstanding_amount: "0",
    expires_at: null,
  });

const paid = row("reg:1", "Paid One", { paid: true, outstanding_amount: "0" });
const owing = row("reg:2", "Owing Two");
const waiting = queued("reg:3", "Waiting Three", "2026-03-05T09:00:00+00:00");
const demoted = queued(
  "reg:4",
  "Demoted Four",
  "2026-04-01T22:00:00+00:00",
  "2026-02-01T08:00:00+00:00",
);
const ROWS = [demoted, paid, waiting, owing];

function roster(rows: SheetRow[], free: number): string {
  return renderToStaticMarkup(
    <QueueRoster
      rows={rows}
      slug="LS"
      capacity={2}
      free={free}
      timezone="Europe/Prague"
      busy={false}
      onPromote={() => {}}
      onReturn={() => {}}
    />,
  );
}

function names(html: string): string[] {
  const doc = new DOMParser().parseFromString(`<table>${html}</table>`, "text/html");
  return [...doc.querySelectorAll("tbody tr")].map((tr) =>
    tr.classList.contains("export-line") ? "—line—" : (tr.children[1]?.textContent ?? ""),
  );
}

beforeAll(async () => {
  await i18n.changeLanguage("cs");
});

describe("the Queue roster", () => {
  it("lists the rows, order and line the Export roster lists", () => {
    const exported = renderToStaticMarkup(
      <RosterTable
        rows={ROWS}
        slug="LS"
        capacity={2}
        lineKind="queue"
        seeded={false}
        edited={() => false}
        onRate={() => {}}
      />,
    );
    expect(names(roster(ROWS, 0))).toEqual(names(exported));
    expect(names(roster(ROWS, 0))).toEqual([
      "Paid One",
      "Owing Two",
      "—line—",
      "Waiting Three",
      "Demoted Four",
    ]);
  });

  it("states the money above the line and the queue moment below it", () => {
    const html = roster(ROWS, 0);
    expect(html).toContain("zaplaceno");
    expect(html).toContain("dluží 1");
    expect(html).toContain("do 12. 3. 2026");
    expect(html).toContain("1. registrace 5. 3. 2026 10:00");
    expect(html).toContain("2. ve frontě od 2. 4. 2026 00:00, přesun pro nezaplacení");
  });

  it("offers no promotion into a full discipline and no return of a paid seat", () => {
    const full = roster(ROWS, 0);
    expect(full).not.toContain("posunout na místo");
    // the one return offered is the unpaid seat's
    expect(full.match(/vrátit do fronty/g)).toHaveLength(1);

    const open = roster(ROWS, 1);
    expect(open.match(/posunout na místo/g)).toHaveLength(2);
  });

  it("gives a row with no registration no arrow, and says it holds no seat", () => {
    const imported = row("imp:9", "Imported Nine", { registration_id: null });
    const html = roster([imported], 1);
    expect(html).not.toContain("row-action");
    expect(html).toContain("zatím nedrží místo");
  });
});

describe("the Export roster", () => {
  it("offers no arrow on any row", () => {
    const html = renderToStaticMarkup(
      <RosterTable
        rows={ROWS}
        slug="LS"
        capacity={2}
        lineKind="queue"
        seeded={false}
        edited={() => false}
        onRate={() => {}}
      />,
    );
    expect(html).not.toContain("posunout na místo");
    expect(html).not.toContain("vrátit do fronty");
  });
});

const SUMMARY: Queue = {
  seating_deadline: "2026-10-01",
  seating_settled_at: null,
  pending_demotions: 11,
  pending_team_waitlistings: 4,
  disciplines: [{ slug: "LS", capacity: 2, taken: 2, free: 0 }],
};

let host: HTMLElement | null = null;

function mount(node: React.ReactNode) {
  host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  act(() => root.render(node));
  return host;
}

async function flush() {
  await act(async () => {
    for (let i = 0; i < 6; i++) await Promise.resolve();
  });
}

afterEach(() => {
  host?.remove();
  host = null;
  vi.restoreAllMocks();
});

describe("the seating rail card", () => {
  it("confirms settlement stating the registrations and the teams it will move", () => {
    const view = mount(
      <SeatingCard
        summary={SUMMARY}
        discipline={SUMMARY.disciplines[0] ?? null}
        timezone="Europe/Prague"
        busy={false}
        outcome={null}
        onSettle={() => {}}
      />,
    );
    const button = [...view.querySelectorAll("button")].find(
      (candidate) => candidate.textContent === "Uzavřít místa",
    );
    act(() => button?.click());
    const text = document.body.textContent ?? "";
    expect(text).toContain("11 registrací stále dluží peníze");
    expect(text).toContain("4 týmy přesunou na čekací listinu");
    expect(text).toContain("nelze vzít zpět");
  });

  it("states when seating settled and offers no action afterwards", () => {
    const view = mount(
      <SeatingCard
        summary={{ ...SUMMARY, seating_settled_at: "2026-09-20T08:00:00+00:00" }}
        discipline={null}
        timezone="Europe/Prague"
        busy={false}
        outcome={null}
        onSettle={() => {}}
      />,
    );
    expect(view.textContent).toContain("Místa uzavřena 20. 9. 2026");
    expect(view.querySelector("button")).toBeNull();
  });
});

describe("a refused arrow", () => {
  const TABS: ExportBandTab[] = [
    { kind: "fencers", key: "", label: "", capacity: null, line: null, count: 3, queued: 0 },
    { kind: "discipline", key: "LS", label: "LS", capacity: 2, line: "queue", count: 2, queued: 1 },
  ];

  beforeEach(() => {
    vi.spyOn(api, "exportTabs").mockResolvedValue(TABS);
    vi.spyOn(api, "queue").mockResolvedValue({
      ...SUMMARY,
      disciplines: [{ slug: "LS", capacity: 2, taken: 1, free: 1 }],
    });
    vi.spyOn(api, "exportTable").mockResolvedValue({
      ...TABS[1],
      rows: [paid, waiting],
    } as never);
  });

  it("is stated in words, not as the server's code", async () => {
    vi.spyOn(api, "admitSubstitute").mockRejectedValue(new ApiError(409, "discipline_full"));
    const onChanged = vi.fn();
    const view = mount(
      <QueuePhase
        slug="cup"
        timezone="Europe/Prague"
        revision={0}
        onChanged={onChanged}
        renderRail={(panel) => <aside>{panel}</aside>}
      />,
    );
    await flush();
    const promote = view.querySelector<HTMLButtonElement>("button[title^='Posunout']");
    expect(promote).not.toBeNull();
    act(() => promote?.click());
    await flush();
    expect(view.textContent).toContain("Disciplína je mezitím plná");
    expect(view.textContent).not.toContain("discipline_full");
    expect(onChanged).toHaveBeenCalled();
  });
});
