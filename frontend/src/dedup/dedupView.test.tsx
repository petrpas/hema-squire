// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { type DedupGroup, type DedupMember, api } from "../api";
import i18n from "../i18n";
import type { OperationsView } from "../useOperations";
import DedupView from "./DedupView";

// The Deduplication phase: candidate groups with an editable conclusion, and
// no fencer table (spec `etl-console`, Deduplication candidate review).

const t = i18n.getFixedT("cs");

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let host: HTMLElement | null = null;

function member(over: Partial<DedupMember>): DedupMember {
  return {
    id: "imp:1",
    number: 12,
    name: "Jan Novák",
    nationality: "CZ",
    email: "jan@example.com",
    club: null,
    hr_id: null,
    hr_name: null,
    hr_nationality: null,
    hr_club: null,
    disciplines: ["SA"],
    weapon_rentals: [],
    afterparty: false,
    notes: null,
    problems: null,
    registered_at: "2026-04-03T10:12:00",
    ...over,
  };
}

const PAIR = [
  member({ id: "imp:1", number: 12, name: "Jan Novák", club: "Krkavci" }),
  member({ id: "imp:2", number: 27, name: "Novák Jan", disciplines: ["SA", "RAP"] }),
];

function group(over: Partial<DedupGroup> = {}): DedupGroup {
  return {
    key: "abc123",
    kind: "likely",
    verdict: "pending",
    decided_by: null,
    members: PAIR,
    recommendation: {
      fields: {
        name: "Jan Novák",
        nationality: "CZ",
        club: "Krkavci",
        email: "jan@example.com",
        hr_id: null,
        disciplines: ["SA", "RAP"],
        weapon_rentals: [],
        afterparty: false,
        notes: null,
        problems: null,
      },
      note: "pozdější záznam doplňuje klub",
    },
    conclusion: null,
    ...over,
  };
}

function view(): OperationsView {
  return { running: null, concluded: {}, refresh: () => {} };
}

async function mount(groups: DedupGroup[]) {
  vi.spyOn(api, "dedupGroups").mockResolvedValue(groups);
  host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  await act(async () => {
    root.render(<DedupView slug="cup" operations={view()} onChanged={() => {}} />);
  });
  return host;
}

function text() {
  return host?.textContent ?? "";
}

function button(label: string): HTMLButtonElement | undefined {
  return [...(host?.querySelectorAll("button") ?? [])].find(
    (element) => element.textContent?.trim() === label,
  ) as HTMLButtonElement | undefined;
}

async function click(element: Element | null | undefined) {
  await act(async () => {
    element?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  });
}

beforeEach(() => {
  vi.restoreAllMocks();
});

afterEach(() => {
  host?.remove();
  host = null;
});

describe("the candidate list", () => {
  it("states the members and the conclusion in the same columns", async () => {
    await mount([group()]);

    // both records, by their fixed numbers
    expect(text()).toContain("12");
    expect(text()).toContain("27");
    expect(text()).toContain("Novák Jan");
    // and the conclusion beneath them, with the merge note
    expect(text()).toContain(t("dedup.conclusion"));
    expect(text()).toContain("pozdější záznam doplňuje klub");
    const columns = [...(host?.querySelectorAll("thead th") ?? [])].map((th) => th.textContent);
    expect(columns).toContain(t("column.email"));
    expect(columns).toContain(t("column.disciplines"));
  });

  it("shows no fencer table", async () => {
    await mount([group()]);

    // the only tables on the phase belong to candidate groups
    const tables = [...(host?.querySelectorAll("table") ?? [])];
    expect(tables.length).toBe(1);
    expect(tables[0].className).toContain("dedup-table");
  });

  it("counts the groups awaiting a decision, and not the settled ones", async () => {
    await mount([
      group(),
      group({ key: "settled", kind: "surely", verdict: "merged", decided_by: "llm" }),
    ]);

    expect(text()).toContain(t("dedup.pending", { count: 1 }));
    expect(text()).toContain(t("dedup.settled"));
  });

  it("says so in one sentence and offers the run when nothing stands", async () => {
    await mount([]);

    expect(text()).toContain(t("dedup.empty"));
    expect(button(t("dedup.run"))).toBeDefined();
    expect(host?.querySelector("table")).toBeNull();
  });
});

describe("the conclusion", () => {
  it("offers each member's value and sends the one chosen", async () => {
    const decide = vi.spyOn(api, "dedupDecide").mockResolvedValue({ status: "merged" });
    await mount([group()]);

    // the conclusion's name cell opens onto the spellings the records carry
    const cell = host?.querySelector(".conclusion-row .conclusion-value");
    await click(cell);
    const choice = [...(host?.querySelectorAll(".conclusion-choice") ?? [])].find(
      (element) => element.textContent === "Novák Jan",
    );
    expect(choice).toBeDefined();
    await click(choice);
    await click(button(t("dedup.accept")));

    expect(decide).toHaveBeenCalledTimes(1);
    const [, key, accept, fields] = decide.mock.calls[0];
    expect(key).toBe("abc123");
    expect(accept).toBe(true);
    expect((fields as Record<string, unknown>).name).toBe("Novák Jan");
  });

  it("sends the note and the fields together, in one decision", async () => {
    const decide = vi.spyOn(api, "dedupDecide").mockResolvedValue({ status: "merged" });
    await mount([group()]);

    const note = host?.querySelector("textarea") as HTMLTextAreaElement;
    expect(note.value).toBe("pozdější záznam doplňuje klub");
    await click(button(t("dedup.accept")));

    expect(decide).toHaveBeenCalledTimes(1);
    expect(decide.mock.calls[0][4]).toBe("pozdější záznam doplňuje klub");
  });

  it("does not open the identity of a group a profile stands behind", async () => {
    const bound = PAIR.map((one) => ({
      ...one,
      hr_id: 41277,
      hr_name: "Jan Novak",
      hr_nationality: "CZ",
      hr_club: "Krkavci",
    }));
    await mount([group({ kind: "same_id", members: bound })]);

    // the identity is the profile's and is rebound on Matching, not here; the
    // cells that do open are the merge's own fields
    const cells = [...(host?.querySelectorAll(".conclusion-row td") ?? [])];
    expect(cells[0].querySelector(".conclusion-value")).toBeNull();
    expect(cells[0].textContent).toBe("Jan Novak");
    expect(host?.querySelector(".conclusion-row .conclusion-list")).not.toBeNull();
  });

  it("never opens the HR id", async () => {
    await mount([group()]);

    const header = [...(host?.querySelectorAll("thead th") ?? [])].findIndex(
      (th) => th.textContent === t("column.hr_id"),
    );
    const cells = [...(host?.querySelectorAll(".conclusion-row td") ?? [])];
    expect(cells[header - 1].querySelector(".conclusion-value")).toBeNull();
  });
});

describe("a settled group", () => {
  it("states that the machine decided it and offers the opposite verdict", async () => {
    const decide = vi.spyOn(api, "dedupDecide").mockResolvedValue({ status: "rejected" });
    await mount([
      group({ kind: "surely", verdict: "merged", decided_by: "llm",
              conclusion: { fields: { name: "Jan Novák" }, note: "auto-merged" } }),
    ]);

    expect(text()).toContain(t("dedup.verdict.merged"));
    expect(text()).toContain(t("dedup.by.llm"));
    // one action reaches the opposite verdict
    await click(button(t("dedup.reject")));
    expect(decide).toHaveBeenCalledWith("cup", "abc123", false, undefined, undefined);
  });

  it("keeps its conclusion closed until it is reopened", async () => {
    await mount([
      group({ verdict: "merged", decided_by: "organizer",
              conclusion: { fields: { name: "Jan Novák" }, note: "sloučeno" } }),
    ]);

    expect(host?.querySelector(".conclusion-value")).toBeNull();
    await click(button(t("dedup.reopen")));
    expect(host?.querySelector(".conclusion-value")).not.toBeNull();
  });

  it("offers a merge to a group kept separate", async () => {
    await mount([group({ verdict: "separate", decided_by: "organizer" })]);

    expect(text()).toContain(t("dedup.verdict.separate"));
    expect(button(t("dedup.accept"))).toBeDefined();
    expect(button(t("dedup.reject"))).toBeUndefined();
  });
});
