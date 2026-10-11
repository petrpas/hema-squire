// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api, type SetupSuggestions, type TournamentDetail } from "../api";
import i18n from "../i18n";
import { IdentitySection } from "./IdentitySection";
import { SaverRegistry } from "./shared";

// The external registration address is offered only where the organizer keeps
// the registrations; elsewhere it is hidden and its stored value kept (spec
// setup-navigation, "Setup offers no section for a registration Squire does
// not run").

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let host: HTMLElement | null = null;

const URL = "https://forms.example.org/x";
const suggestions = {
  cities: [],
  addresses: [],
  bank_accounts: [],
  organizers: [],
} as SetupSuggestions;

function render(keptBy: TournamentDetail["registrations_kept_by"], registry = new SaverRegistry()) {
  void i18n.changeLanguage("cs");
  const detail = {
    slug: "cup",
    display_name: "Cup",
    short_code: null,
    qualification_open: true,
    qualification_criteria: null,
    external_registration_url: URL,
    registrations_kept_by: keptBy,
  } as unknown as TournamentDetail;
  host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  act(() =>
    root.render(
      <IdentitySection
        detail={detail}
        slug="cup"
        onSaved={() => {}}
        registry={registry}
        suggestions={suggestions}
      />,
    ),
  );
  return host;
}

function offered(page: HTMLElement): boolean {
  return [...page.querySelectorAll("label span")].some(
    (span) => span.textContent === "Externí registrace",
  );
}

beforeEach(() => void vi.restoreAllMocks());
afterEach(() => {
  host?.remove();
  host = null;
});

describe("the external registration address in Setup", () => {
  it("is offered where the organizer keeps the registrations", () => {
    expect(offered(render("organizer"))).toBe(true);
  });

  it("is not offered where Squire keeps them", () => {
    expect(offered(render("squire"))).toBe(false);
  });

  it("keeps its stored value through a save while hidden", async () => {
    const update = vi.spyOn(api, "updateTournament").mockResolvedValue({} as never);
    const registry = new SaverRegistry();
    render("squire", registry);
    const saver = registry.forTab("tournament")[0]?.saver;
    await act(async () => {
      await saver?.flush();
    });
    expect(update).toHaveBeenCalledWith(
      "cup",
      expect.objectContaining({ external_registration_url: URL }),
    );
  });
});
