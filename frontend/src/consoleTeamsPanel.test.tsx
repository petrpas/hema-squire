// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, type ConsoleTeam, type ConsoleTeamDiscipline } from "./api";
import i18n from "./i18n";
import TeamsPanel from "./TeamsPanel";

// The organizer's teams view (spec team-disciplines, Organizer's teams view):
// it states a bound member's HEMA Ratings identifier, it edits a roster and
// shows the log beside it, and it offers no admission and no cancellation.

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

function team(overrides: Partial<ConsoleTeam> = {}): ConsoleTeam {
  return {
    id: 5,
    name: "Wolves",
    entering_fencer: "F1",
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

function discipline(teams: ConsoleTeam[]): ConsoleTeamDiscipline {
  return { slug: "LS", name: "Longsword", team_min: 3, team_max: 4, teams };
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
  it("states a bound member's HEMA Ratings identifier and shows an unbound one plainly", async () => {
    const page = await openPanel([discipline([team()])]);

    const rows = [...page.querySelectorAll(".detail-list .muted")].map((li) => li.textContent);
    expect(rows[0]).toBe("Bound Person · #4321 · Brno HEMA · CZ");
    expect(rows[1]).toBe("Unknown Person");
  });

  it("offers no admission and no cancellation, and says admission is on the Queue phase", async () => {
    const page = await openPanel([
      discipline([team({ waitlisted: true, waitlist_position: 2, below_minimum: true })]),
    ]);

    // the team's own row offers the roster editor and the history, and
    // nothing else: no admission, no return to the waitlist, no cancellation
    const rowControls = [...page.querySelectorAll<HTMLButtonElement>("li .detail-row button")].map(
      (button) => button.textContent,
    );
    expect(rowControls).toEqual([i18n.t("teams.editRoster"), i18n.t("teams.log.show")]);
    expect(page.textContent).toContain(i18n.t("teams.admittedOnQueue"));
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
