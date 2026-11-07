// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, type RosterMember, type TeamEntry } from "./api";
import i18n from "./i18n";
import TeamsTab from "./TeamsTab";

// The entrant's editor sends the identity the server gave each member, so a
// rename and a reorder are read as the same four people rather than as four
// removals and four additions (spec team-disciplines, A roster member keeps
// its identity across saves).

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

function member(id: number, name: string): RosterMember {
  return { id, name, hr_id: null, club: null, nationality: null };
}

function team(members: RosterMember[]): TeamEntry {
  return {
    id: 5,
    slug: "LS",
    name: "Wolves",
    waitlisted: false,
    fee: 3000,
    fee_eur: null,
    team_min: 3,
    team_max: 4,
    members,
    prefill: null,
  };
}

let host: HTMLElement | null = null;

async function openTab(entry: TeamEntry): Promise<HTMLElement> {
  host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  act(() => root.render(<TeamsTab slug="cup" teams={[entry]} onTeamUpdated={() => {}} />));
  await act(async () => {
    await Promise.resolve();
  });
  return host;
}

function nameFields(page: HTMLElement): HTMLInputElement[] {
  return [...page.querySelectorAll<HTMLInputElement>(".team-row .cell-input")];
}

/** React tracks a controlled input's value on the node, so a plain assignment
 *  is swallowed; the prototype's own setter is what an actual keystroke
 *  reaches (the idiom of `disciplineDialog.test.tsx`). */
function type(input: HTMLInputElement, value: string) {
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
  if (setter === undefined) throw new Error("no value setter");
  act(() => {
    setter.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

function buttonsTitled(page: HTMLElement, title: string): HTMLButtonElement[] {
  return [...page.querySelectorAll<HTMLButtonElement>(`.team-row button[title="${title}"]`)];
}

afterEach(() => {
  host?.remove();
  host = null;
});

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("the entrant's roster editor", () => {
  it("sends the ids it was given after a rename and a reorder", async () => {
    const update = vi.spyOn(api, "updateRoster").mockResolvedValue(team([]) as never);
    const page = await openTab(team([member(11, "A"), member(22, "B"), member(33, "C")]));

    // rename the first, then move the last one to the top
    const field = nameFields(page)[0];
    if (field === undefined) throw new Error("no name field");
    type(field, "Alice");
    const moveUp = buttonsTitled(page, i18n.t("actions.moveUp"))[2];
    await act(async () => moveUp?.click());

    const save = [...page.querySelectorAll<HTMLButtonElement>("button")].find(
      (button) => button.textContent === i18n.t("roster.saveAll"),
    );
    await act(async () => save?.click());

    expect(update).toHaveBeenCalledTimes(1);
    expect(update.mock.calls[0]?.[2]).toEqual([
      { id: 11, name: "Alice", hr_id: null, club: null, nationality: null },
      { id: 33, name: "C", hr_id: null, club: null, nationality: null },
      { id: 22, name: "B", hr_id: null, club: null, nationality: null },
    ]);
  });

  it("sends no id for a member the roster does not have yet", async () => {
    const update = vi.spyOn(api, "updateRoster").mockResolvedValue(team([]) as never);
    const page = await openTab(team([member(11, "A")]));

    const add = [...page.querySelectorAll<HTMLButtonElement>("button")].find(
      (button) => button.textContent === i18n.t("roster.add"),
    );
    await act(async () => add?.click());
    const typed = document.querySelector<HTMLInputElement>(".modal input");
    if (typed === null) throw new Error("no dialog field");
    type(typed, "Newcomer");
    const confirm = [...document.querySelectorAll<HTMLButtonElement>(".modal button")].find(
      (button) => button.textContent === i18n.t("roster.confirmPlain"),
    );
    await act(async () => confirm?.click());

    const save = [...page.querySelectorAll<HTMLButtonElement>("button")].find(
      (button) => button.textContent === i18n.t("roster.saveAll"),
    );
    await act(async () => save?.click());

    expect(update.mock.calls[0]?.[2]).toEqual([
      { id: 11, name: "A", hr_id: null, club: null, nationality: null },
      { id: null, name: "Newcomer", hr_id: null, club: null, nationality: null },
    ]);
  });
});
