// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, type ConsoleTeam, type ConsoleTeamDiscipline } from "./api";
import i18n from "./i18n";
import TeamsPanel from "./TeamsPanel";

// The organizer's teams view (spec team-disciplines, Organizer's teams view):
// a table of the tournament's teams, each with its roster reachable from its
// row; it states a bound member's HEMA Ratings identifier, it edits a roster
// and shows the log beside it, it cancels one team, and it offers no
// admission — which is the Queue phase's, as a waitlisted row says.

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

function team(overrides: Partial<ConsoleTeam> = {}): ConsoleTeam {
  return {
    id: 5,
    name: "Wolves",
    entering_fencer: "F1",
    entering_email: "f1@example.org",
    items: [],
    items_shared_with: [],
    paid: false,
    waitlisted: false,
    waitlist_position: null,
    members: [
      { id: 11, name: "Bound Person", hr_id: 4321, club: "Brno HEMA", nationality: "CZ" },
      { id: 22, name: "Unknown Person", hr_id: null, club: null, nationality: null },
    ],
    removed_members: [],
    log: [],
    below_minimum: false,
    ...overrides,
  };
}

function discipline(teams: ConsoleTeam[], slug = "LS", name = "Longsword"): ConsoleTeamDiscipline {
  return { slug, name, team_min: 3, team_max: 4, teams };
}

let host: HTMLElement | null = null;

async function openPanel(disciplines: ConsoleTeamDiscipline[]): Promise<HTMLElement> {
  vi.spyOn(api, "consoleTeams").mockResolvedValue(disciplines as never);
  host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  act(() => root.render(<TeamsPanel slug="cup" />));
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
  return host;
}

function click(page: HTMLElement, label: string) {
  const button = [...page.querySelectorAll<HTMLButtonElement>("button")].find(
    (candidate) => candidate.textContent === label,
  );
  if (button === undefined) throw new Error(`no button labelled ${label}`);
  return act(async () => button.click());
}

afterEach(() => {
  host?.remove();
  host = null;
});

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("the organizer's teams view", () => {
  it("reads as a table of teams, one row each, with its roster behind the row", async () => {
    const page = await openPanel([
      discipline([
        team(),
        team({
          id: 6,
          name: "Bears",
          entering_fencer: "F2",
          paid: true,
          members: [
            { id: 31, name: "A", hr_id: null, club: null, nationality: null },
            { id: 32, name: "B", hr_id: null, club: null, nationality: null },
            { id: 33, name: "C", hr_id: null, club: null, nationality: null },
          ],
        }),
      ]),
    ]);

    const headers = [...page.querySelectorAll("thead th")].map((th) => th.textContent);
    expect(headers).toEqual([
      "",
      i18n.t("teams.column.team"),
      i18n.t("teams.column.enteringFencer"),
      i18n.t("teams.column.email"),
      i18n.t("teams.column.items"),
      i18n.t("teams.column.members"),
      i18n.t("teams.column.paid"),
      "",
    ]);
    const first = [...(page.querySelectorAll("tbody tr")[0]?.querySelectorAll("td") ?? [])].map(
      (td) => td.textContent,
    );
    // the count's cell carries the roster's toggle, named for assistive
    // technology alone
    expect(first.slice(0, 7)).toEqual([
      "1",
      "Wolves",
      "F1",
      "f1@example.org",
      "",
      `2${i18n.t("teams.roster.show")}`,
      i18n.t("export.no"),
    ]);
    // one discipline: no tabs to choose it by
    expect(page.querySelector("[role=tablist]")).toBeNull();
    // the second team's paid cell states its own registration's standing
    const second = [...(page.querySelectorAll("tbody tr")[1]?.querySelectorAll("td") ?? [])].map(
      (td) => td.textContent,
    );
    expect(second[6]).toBe(i18n.t("export.yes"));
    // two of a minimum of three: the count alone, marked as outside the bounds
    const count = page.querySelectorAll("tbody tr")[0]?.querySelector("td:nth-child(6) span");
    expect(count?.className).toContain("member-count-off");
    // a count the bounds admit carries no mark
    const okCount = page.querySelectorAll("tbody tr")[1]?.querySelector("td:nth-child(6) span");
    expect(okCount?.textContent).toBe("3");
    expect(okCount?.className).not.toContain("member-count-off");

    // the roster is not printed under every row
    expect(page.textContent).not.toContain("Bound Person");
  });

  it("states what the entering registration bought, and whom it is shared with", async () => {
    const page = await openPanel([
      discipline([
        team({ items: ["Meč x2", "Afterparty"], items_shared_with: ["Bears"] }),
        team({
          id: 6,
          name: "Bears",
          items: ["Meč x2", "Afterparty"],
          items_shared_with: ["Wolves"],
        }),
        team({ id: 7, name: "Hawks", items: ["Afterparty"] }),
      ]),
    ]);

    const itemCells = [...page.querySelectorAll("tbody tr")].map((tr) => tr.children[4]);
    expect(itemCells[0]?.textContent).toContain("Meč x2, Afterparty");
    // a registration that entered two teams cannot say whose the items are:
    // each team says so behind a marker
    const marker = itemCells[0]?.querySelector("button");
    expect(marker?.textContent).toBe("[i]");
    await act(async () => marker?.click());
    expect(itemCells[0]?.textContent).toContain(
      i18n.t("teams.itemsShared", { count: 1, teams: "Bears" }),
    );
    // a registration with one team has nothing to share
    expect(itemCells[2]?.textContent).toBe("Afterparty");
  });

  it("chooses the discipline by a tab where there are two or more", async () => {
    const page = await openPanel([
      discipline([team()]),
      discipline([team({ id: 7, name: "Hawks" }), team({ id: 8, name: "Owls" })], "SB", "Sabre"),
    ]);

    const tabs = [...page.querySelectorAll("[role=tab]")];
    expect(tabs.map((tab) => tab.textContent)).toEqual(["Longsword1", "Sabre2"]);
    const names = () =>
      [...page.querySelectorAll("tbody tr td:nth-child(2) strong")].map((n) => n.textContent);
    expect(names()).toEqual(["Wolves"]);

    await act(async () => (tabs[1] as HTMLButtonElement).click());
    expect(names()).toEqual(["Hawks", "Owls"]);
  });

  it("states a bound member's HEMA Ratings identifier and shows an unbound one plainly", async () => {
    const page = await openPanel([discipline([team()])]);
    await click(page, i18n.t("teams.roster.show"));

    const rows = [...page.querySelectorAll(".detail-list .muted")].map((li) => li.textContent);
    expect(rows[0]).toBe("Bound Person · HR 4321 · Brno HEMA · CZ");
    expect(rows[1]).toBe("Unknown Person");
  });

  it("offers no admission, and says admission is on the Queue phase", async () => {
    const page = await openPanel([
      discipline([team({ waitlisted: true, waitlist_position: 2, below_minimum: true })]),
    ]);

    // the row offers the roster and the cancellation of this one team, and
    // nothing else: no admission, no return to the waitlist
    const rowControls = [...page.querySelectorAll<HTMLButtonElement>("tbody tr button")].map(
      (button) => button.title || button.textContent,
    );
    expect(rowControls).toEqual([i18n.t("teams.roster.show"), i18n.t("teams.cancel.action")]);
    expect(page.textContent).toContain(i18n.t("teams.admittedOnQueue"));
  });

  it("stands the waitlisted teams below the capacity line, and draws none without them", async () => {
    const page = await openPanel([
      discipline([
        team({ id: 7, name: "Hawks", waitlisted: true, waitlist_position: 1 }),
        team(),
        team({ id: 8, name: "Owls", waitlisted: true, waitlist_position: 2 }),
      ]),
    ]);

    const rows = [...page.querySelectorAll("tbody tr")].map((tr) =>
      tr.classList.contains("export-line")
        ? "line"
        : `${tr.querySelector(".col-gutter")?.textContent} ${tr.querySelector("strong")?.textContent}`,
    );
    // below the line the count starts again: each team's place on the waitlist
    expect(rows).toEqual(["1 Wolves", "line", "1 Hawks", "2 Owls"]);

    host?.remove();
    const plain = await openPanel([discipline([team()])]);
    expect(plain.querySelector(".export-line")).toBeNull();
  });

  it("cancels one team through the console's own route and drops it from the table", async () => {
    const cancel = vi.spyOn(api, "cancelTeam").mockResolvedValue({
      previous_total: "6000",
      total: "3000",
      notified: true,
    } as never);
    const remaining = discipline([team({ id: 6, name: "Bears", entering_fencer: "F2" })]);
    const page = await openPanel([
      discipline([team(), team({ id: 6, name: "Bears", entering_fencer: "F2" })]),
    ]);
    // the cancellation repriced a registration and freed a place, so the view
    // is read again: what else it moved is the server's to state
    vi.spyOn(api, "consoleTeams").mockResolvedValue([remaining] as never);

    const button = [...page.querySelectorAll<HTMLButtonElement>("tbody tr button")].find(
      (candidate) => candidate.title === i18n.t("teams.cancel.action"),
    );
    await act(async () => button?.click());
    // it says what will happen before it is confirmed, and the confirmation is
    // the destructive button rather than the default
    expect(document.body.textContent).toContain(i18n.t("teams.cancel.irreversible"));
    expect(document.body.textContent).toContain(i18n.t("teams.cancel.meaning"));
    expect(document.body.textContent).toContain(i18n.t("teams.cancel.roster", { count: 2 }));
    expect(document.body.textContent).toContain(i18n.t("teams.cancel.place"));
    expect(document.body.textContent).toContain(i18n.t("teams.cancel.mail"));
    await act(async () => {
      [...document.querySelectorAll<HTMLButtonElement>(".modal-actions button")]
        .find((candidate) => candidate.textContent === i18n.t("teams.cancel.confirm"))
        ?.click();
      await Promise.resolve();
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(cancel).toHaveBeenCalledWith("cup", 5);
    const names = [...page.querySelectorAll("tbody tr td:nth-child(2)")].map(
      (td) => td.textContent,
    );
    expect(names).toEqual(["Bears"]);
  });

  it("saves a roster through the console's own route and keeps the log beside it", async () => {
    const saved = team({
      members: [
        { id: 11, name: "Bound Person", hr_id: 4321, club: "Brno HEMA", nationality: "CZ" },
      ],
      removed_members: [
        {
          id: 22,
          name: "Unknown Person",
          hr_id: null,
          club: null,
          nationality: null,
          removed_at: "2026-11-07T10:00:00Z",
          removed_by: "Organizer",
        },
      ],
      log: [
        {
          id: 1,
          member_id: 22,
          member_name: "Unknown Person",
          kind: "removed",
          field: null,
          before: null,
          after: null,
          actor: "Organizer",
          by_organizer: true,
          after_deadline: true,
          created_at: "2026-11-07T10:00:00Z",
        },
      ],
    });
    const update = vi.spyOn(api, "consoleUpdateRoster").mockResolvedValue(saved as never);
    const page = await openPanel([discipline([team()])]);

    await click(page, i18n.t("teams.roster.show"));
    await click(page, i18n.t("teams.editRoster"));
    const remove = [...page.querySelectorAll<HTMLButtonElement>("button[title]")].filter(
      (button) => button.title === i18n.t("actions.delete"),
    )[1];
    await act(async () => remove?.click());
    await click(page, i18n.t("teams.editor.save"));

    expect(update).toHaveBeenCalledWith("cup", 5, [
      { id: 11, name: "Bound Person", hr_id: 4321, club: "Brno HEMA", nationality: "CZ" },
    ]);
    // the saved team replaces the old one: one member, and the log it carries
    await click(page, i18n.t("teams.log.show"));
    expect(page.textContent).toContain(i18n.t("teams.log.removed", { member: "Unknown Person" }));
    expect(page.textContent).toContain(i18n.t("teams.log.afterDeadline"));
  });

  it("restores a removed member rather than asking for it to be re-typed", async () => {
    const update = vi.spyOn(api, "consoleUpdateRoster").mockResolvedValue(team() as never);
    const page = await openPanel([
      discipline([
        team({
          removed_members: [
            {
              id: 22,
              name: "Unknown Person",
              hr_id: null,
              club: null,
              nationality: null,
              removed_at: "2026-11-07T10:00:00Z",
              removed_by: "Organizer",
            },
          ],
          members: [
            { id: 11, name: "Bound Person", hr_id: 4321, club: "Brno HEMA", nationality: "CZ" },
          ],
        }),
      ]),
    ]);

    await click(page, i18n.t("teams.roster.show"));
    await click(page, i18n.t("teams.editRoster"));
    await click(page, i18n.t("teams.editor.restore"));
    await click(page, i18n.t("teams.editor.save"));

    // the member returns by its own identity, not as a new name
    expect(update).toHaveBeenCalledWith("cup", 5, [
      { id: 11, name: "Bound Person", hr_id: 4321, club: "Brno HEMA", nationality: "CZ" },
      { id: 22, name: "Unknown Person", hr_id: null, club: null, nationality: null },
    ]);
  });
});
