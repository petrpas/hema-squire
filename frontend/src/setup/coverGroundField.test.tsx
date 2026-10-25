// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api, type SetupSuggestions, type TournamentDetail } from "../api";
import i18n from "../i18n";
import { IdentitySection } from "./IdentitySection";
import { SaverRegistry } from "./shared";

// Beside the logo, the organizer chooses the cover's ground — a tint or a photo
// — or leaves it to follow the logo (spec tournament-admin, The organizer
// chooses the cover ground).

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
    has_cover_photo: false,
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

describe("the cover ground in Setup", () => {
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

  it("saves red with the identity section", async () => {
    const update = vi.spyOn(api, "updateTournament").mockResolvedValue({} as never);
    const registry = new SaverRegistry();
    const page = render({}, registry);
    act(() => option(page, "červená")?.click());
    await save(registry);
    expect(update).toHaveBeenCalledWith("cup", expect.objectContaining({ cover_tint: "red" }));
  });

  it("selects an uploaded photo, and the section's save wears it", async () => {
    const upload = vi.spyOn(api, "uploadCoverPhoto").mockResolvedValue({} as never);
    const update = vi.spyOn(api, "updateTournament").mockResolvedValue({} as never);
    const registry = new SaverRegistry();
    const page = render({}, registry);
    expect(page.querySelector(".cover-photo-preview")).toBeNull();
    const input = page.querySelector<HTMLInputElement>(".cover-photo-control input[type=file]");
    const file = new File(["x"], "photo.jpg", { type: "image/jpeg" });
    Object.defineProperty(input, "files", { value: [file] });
    await act(async () => {
      input?.dispatchEvent(new Event("change", { bubbles: true }));
    });
    expect(upload).toHaveBeenCalledWith("cup", file);
    expect(update).not.toHaveBeenCalled();
    expect(option(page, "fotka")?.checked).toBe(true);
    expect(page.querySelector(".cover-photo-preview")).not.toBeNull();
    await save(registry);
    expect(update).toHaveBeenCalledWith("cup", expect.objectContaining({ cover_tint: "photo" }));
  });

  it("offers the upload, not the choice, while no photo is stored", () => {
    const page = render({}, new SaverRegistry());
    const input = page.querySelector<HTMLInputElement>(".cover-photo-control input[type=file]");
    const opened = vi.fn();
    input?.addEventListener("click", opened);
    act(() => option(page, "fotka")?.click());
    expect(opened).toHaveBeenCalled();
    expect(option(page, "Podle loga (žlutá)")?.checked).toBe(true);
  });

  it("keeps a stored photo choosable after a tint is chosen over it", async () => {
    const update = vi.spyOn(api, "updateTournament").mockResolvedValue({} as never);
    const registry = new SaverRegistry();
    const page = render({ cover_tint: "yellow", has_cover_photo: true }, registry);
    expect(page.querySelector(".cover-photo-preview")).not.toBeNull();
    act(() => option(page, "fotka")?.click());
    await save(registry);
    expect(update).toHaveBeenCalledWith("cup", expect.objectContaining({ cover_tint: "photo" }));
  });
});
