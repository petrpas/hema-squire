// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api, type SetupSuggestions, type TournamentDetail } from "../api";
import i18n from "../i18n";
import { IdentitySection } from "./IdentitySection";
import { SaverRegistry } from "./shared";

// Beside the logo, the organizer chooses the cover tint or leaves it to follow
// the logo (spec tournament-admin, The organizer chooses the cover tint).

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let host: HTMLElement | null = null;

const suggestions = {
  cities: [],
  addresses: [],
  bank_accounts: [],
  organizers: [],
} as SetupSuggestions;

function render(over: Partial<TournamentDetail>, registry: SaverRegistry) {
  void i18n.changeLanguage("cs");
  const detail = {
    slug: "cup",
    display_name: "Cup",
    short_code: null,
    has_logo: true,
    logo_tint: "warm",
    cover_tint: null,
    qualification_open: true,
    qualification_criteria: null,
    registrations_kept_by: "squire",
    ...over,
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

function option(page: HTMLElement, text: string): HTMLInputElement | null {
  const label = [...page.querySelectorAll("label")].find((l) => l.textContent === text);
  return label?.querySelector("input") ?? null;
}

async function save(registry: SaverRegistry) {
  await act(async () => {
    await registry.forTab("tournament")[0]?.saver.flush();
  });
}

beforeEach(() => void vi.restoreAllMocks());
afterEach(() => {
  host?.remove();
  host = null;
});

describe("the cover tint in Setup", () => {
  it("names what following the logo gives, and stands there by default", () => {
    const page = render({}, new SaverRegistry());
    expect(option(page, "Podle loga (žlutá)")?.checked).toBe(true);
  });

  it("saves a chosen tint with the identity section", async () => {
    const update = vi.spyOn(api, "updateTournament").mockResolvedValue({} as never);
    const registry = new SaverRegistry();
    const page = render({}, registry);
    act(() => option(page, "modrá")?.click());
    await save(registry);
    expect(update).toHaveBeenCalledWith("cup", expect.objectContaining({ cover_tint: "blue" }));
  });

  it("returns a chosen tint to following the logo", async () => {
    const update = vi.spyOn(api, "updateTournament").mockResolvedValue({} as never);
    const registry = new SaverRegistry();
    const page = render({ cover_tint: "green" }, registry);
    expect(option(page, "zelená")?.checked).toBe(true);
    act(() => option(page, "Podle loga (žlutá)")?.click());
    await save(registry);
    expect(update).toHaveBeenCalledWith("cup", expect.objectContaining({ cover_tint: null }));
  });
});
