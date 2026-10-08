// @vitest-environment jsdom
import { act, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api, type TournamentDetail } from "./api";
import i18n from "./i18n";
import SetupPanel from "./SetupPanel";
import type { SaverRegistry } from "./setup/shared";

// Below the width at which the preview fits beside the settings, it becomes
// the settings bar's last tab rather than falling below them (spec
// setup-preview, Setup phase shows settings and preview side by side;
// setup-navigation, The preview tab holds no settings).
//
// The settings sections are stubbed: what is under test is where the preview
// is and what the bar offers, not what any section edits. The fencer-facing
// form is stubbed by one stateful checkbox, which is enough to tell a preview
// that kept its state from one that was mounted afresh.

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const t = i18n.getFixedT(i18n.language);

vi.mock("./TournamentFace", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./TournamentFace")>()),
  InfoHeader: () => <p className="stub-face">face</p>,
  DisciplinesInfo: () => null,
  DiscountList: () => null,
  OtherActionsInfo: () => null,
  RegistrationForm: () => {
    const [ticked, setTicked] = useState(false);
    return (
      <input
        type="checkbox"
        className="stub-form"
        checked={ticked}
        onChange={(event) => setTicked(event.target.checked)}
      />
    );
  },
}));

// hoisted with the vi.mock calls that use it
const { nothing } = vi.hoisted(() => ({ nothing: () => null }));
vi.mock("./setup/IdentitySection", () => ({ IdentitySection: nothing, VsSeriesSection: nothing }));
vi.mock("./setup/OrganizersSection", () => ({ OrganizersSection: nothing }));
vi.mock("./setup/ExtraItemsSection", () => ({ ExtraItemsSection: nothing }));
vi.mock("./setup/TimelineSection", () => ({ TimelineSection: nothing }));
vi.mock("./setup/PaymentModeSection", () => ({ PaymentModeSection: nothing }));
vi.mock("./setup/BankAccountSection", () => ({ BankAccountSection: nothing }));
vi.mock("./setup/CurrencySection", () => ({ CurrencySection: nothing }));
vi.mock("./setup/DiscountsSection", () => ({ DiscountsSection: nothing }));
vi.mock("./setup/LegacyFeesSection", () => ({ LegacyFeesSection: nothing }));
vi.mock("./setup/SettingsSection", () => ({ SettingsSection: nothing }));
vi.mock("./setup/TeamSection", () => ({ TeamSection: nothing }));
vi.mock("./setup/DangerZoneSection", () => ({ DangerZoneSection: nothing }));
vi.mock("./setup/PublishSection", () => ({ PublishSection: nothing }));
// DISCIPLINES holds one unsaved change, so its unsaved marker can be looked for
vi.mock("./setup/DisciplinesSection", () => ({
  DisciplinesSection: ({ registry }: { registry: SaverRegistry }) => {
    useEffect(() => {
      registry.set("disciplines", "disciplines", {
        pendingCount: 1,
        touchesPrice: false,
        validate: () => 0,
        focusFirstInvalid: () => {},
        flush: async () => [],
      });
    }, [registry]);
    return null;
  },
}));

/** A `matchMedia` whose one query can be flipped, firing its listeners as a
 *  resized window would. */
function stubViewport(narrow: boolean) {
  const listeners = new Set<() => void>();
  const list = {
    matches: narrow,
    addEventListener: (_: string, listener: () => void) => listeners.add(listener),
    removeEventListener: (_: string, listener: () => void) => listeners.delete(listener),
  };
  vi.stubGlobal("matchMedia", () => list);
  return (next: boolean) =>
    act(() => {
      list.matches = next;
      for (const listener of listeners) listener();
    });
}

const detail = {
  slug: "cup",
  owner_id: 1,
  disciplines: [],
  setup_missing: ["discipline_prices"],
  cancelled_at: null,
  registrations_kept_by: "squire",
  feature_schedule: false,
  feature_payments: true,
  feature_teams: false,
  feature_extras: false,
} as unknown as TournamentDetail;

let host: HTMLElement | null = null;

async function mount() {
  host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  act(() =>
    root.render(
      <SetupPanel
        detail={detail}
        slug="cup"
        onSaved={() => {}}
        hasRegistrations={false}
        onDeleted={() => {}}
        onDirtyChange={() => {}}
      />,
    ),
  );
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

function tabs(): HTMLButtonElement[] {
  return [...(host?.querySelectorAll<HTMLButtonElement>(".setup-tabs [role=tab]") ?? [])];
}

function tab(key: string): HTMLButtonElement {
  const found = tabs().find((button) => button.id === `setup-tab-${key}`);
  if (found === undefined) throw new Error(`no ${key} tab`);
  return found;
}

function click(element: Element | null | undefined) {
  act(() => void element?.dispatchEvent(new MouseEvent("click", { bubbles: true })));
}

function preview(): HTMLElement {
  return host?.querySelector(".setup-preview") as HTMLElement;
}

function body(): HTMLElement {
  return host?.querySelector(".setup-panel-body") as HTMLElement;
}

function selected(): string | undefined {
  return tabs().find((button) => button.getAttribute("aria-selected") === "true")?.id;
}

beforeEach(() => {
  vi.restoreAllMocks();
  vi.spyOn(api, "account").mockResolvedValue({ id: 1 } as never);
  vi.spyOn(api, "setupSuggestions").mockRejectedValue(new Error("none"));
  vi.spyOn(api, "availability").mockResolvedValue([]);
});

afterEach(() => {
  vi.unstubAllGlobals();
  host?.remove();
  host = null;
});

describe("on a narrow viewport", () => {
  it("ends the bar with the preview tab, after Publish", async () => {
    stubViewport(true);
    await mount();

    // the label alone, without the markers' visually hidden text
    const labels = tabs().map((button) => button.firstChild?.textContent);
    expect(labels[labels.length - 2]).toBe(t("setup.tabs.publish"));
    expect(labels[labels.length - 1]).toBe(t("setup.tabs.preview"));
    expect(selected()).toBe("setup-tab-tournament");
    expect(preview().hidden).toBe(true);
  });

  it("shows the preview in place of the settings, with no save control", async () => {
    stubViewport(true);
    await mount();
    // DISCIPLINES has something to save, so its save bar is drawn
    click(tab("disciplines"));
    expect(host?.querySelector(".setup-save-bar")).not.toBeNull();
    click(tab("preview"));

    expect(selected()).toBe("setup-tab-preview");
    expect(preview().hidden).toBe(false);
    expect(preview().getAttribute("role")).toBe("tabpanel");
    expect(tab("preview").getAttribute("aria-controls")).toBe(preview().id);
    // the save bar is inside the hidden body, out of sight with every section
    expect(body().hidden).toBe(true);
    expect(body().contains(host?.querySelector(".setup-save-bar") ?? null)).toBe(true);
  });

  it("keeps the other tabs' markers and carries none of its own", async () => {
    stubViewport(true);
    await mount();
    click(tab("preview"));

    expect(tab("disciplines").querySelector(".tab-mark")).not.toBeNull();
    expect(tab("disciplines").querySelector(".tab-dirty-mark")).not.toBeNull();
    expect(tab("publish").querySelector(".tab-mark")).not.toBeNull();
    expect(tab("preview").querySelector(".tab-mark, .tab-dirty-mark")).toBeNull();
  });

  it("keeps the preview's face and form selections across a tab switch", async () => {
    stubViewport(true);
    await mount();
    click(tab("preview"));
    click(
      [...preview().querySelectorAll("button")].find(
        (button) => button.textContent === t("preview.tabs.form"),
      ),
    );
    click(preview().querySelector(".stub-form"));

    click(tab("disciplines"));
    expect(preview().hidden).toBe(true);
    expect(body().hidden).toBe(false);

    click(tab("preview"));
    expect((preview().querySelector(".stub-form") as HTMLInputElement).checked).toBe(true);
  });
});

describe("crossing the threshold", () => {
  it("returns to the settings tab selected before the preview when widened", async () => {
    const resize = stubViewport(true);
    await mount();
    click(tab("timeline"));
    click(tab("preview"));

    resize(false);

    expect(selected()).toBe("setup-tab-timeline");
    expect(tabs().some((button) => button.id === "setup-tab-preview")).toBe(false);
    expect(body().hidden).toBe(false);
    expect(preview().hidden).toBe(false);
    expect(preview().getAttribute("role")).toBeNull();
  });

  it("does not select the preview on narrowing again", async () => {
    const resize = stubViewport(true);
    await mount();
    click(tab("payments"));
    click(tab("preview"));
    resize(false);
    resize(true);

    expect(selected()).toBe("setup-tab-payments");
    expect(preview().hidden).toBe(true);
  });

  it("keeps the form selection when the window narrows", async () => {
    const resize = stubViewport(false);
    await mount();
    click(preview().querySelector(".preview-tabs button:last-child"));
    click(preview().querySelector(".stub-form"));

    resize(true);
    click(tab("preview"));

    expect((preview().querySelector(".stub-form") as HTMLInputElement).checked).toBe(true);
  });
});

describe("on a wide viewport", () => {
  it("offers no preview tab and keeps the preview beside the settings", async () => {
    await mount();

    expect(tabs().map((button) => button.id)).not.toContain("setup-tab-preview");
    expect(preview().hidden).toBe(false);
    expect(preview().getAttribute("role")).toBeNull();
    expect(body().hidden).toBe(false);
  });
});
