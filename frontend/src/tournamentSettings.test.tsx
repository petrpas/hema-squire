// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";

import { type TournamentDetail, api } from "./api";
import i18n from "./i18n";
import { SettingsSection } from "./setup/SettingsSection";
import TournamentSettingsDialog from "./TournamentSettingsDialog";

// The tournament's whole configuration on one surface, in three tiers: the
// mode, the payments setting, and what the tournament includes (spec
// setup-navigation, tournament-mode, tournament-features).
//
// There is no easy or advanced mode. Nothing here derives a name from how many
// features are enabled — that named a state nothing stored, and it is gone.

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const t = i18n.getFixedT("cs");

let host: HTMLElement | null = null;

function mount(element: React.ReactElement) {
  host = document.createElement("div");
  document.body.append(host);
  act(() => createRoot(host!).render(element));
  return host;
}

afterEach(() => {
  host?.remove();
  host = null;
  vi.restoreAllMocks();
});

function buttonNamed(text: string) {
  return [...document.querySelectorAll("button")].find(
    (button) => button.textContent?.trim() === text,
  ) as HTMLButtonElement | undefined;
}

function modeRadios() {
  return [...document.querySelectorAll<HTMLInputElement>('input[name="tournament-mode"]')];
}

function checkboxes() {
  return [...document.querySelectorAll<HTMLInputElement>('input[type="checkbox"]')];
}

function detail(overrides: Partial<TournamentDetail> = {}): TournamentDetail {
  return {
    slug: "cup",
    registrations_kept_by: "squire",
    in_app_registrations: 0,
    feature_schedule: false,
    feature_payments: false,
    feature_teams: false,
    feature_extras: false,
    payment_mode: "immediate",
    bank_account: null,
    deposit_amount: null,
    extra_items: [],
    disciplines: [],
    ...overrides,
  } as unknown as TournamentDetail;
}

async function settle() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

// --------------------------------------------------------- the three tiers

it("offers the mode, payments and the three inclusions on one surface", () => {
  mount(
    <TournamentSettingsDialog detail={detail()} onApplied={vi.fn()} onClose={vi.fn()} />,
  );
  expect(modeRadios()).toHaveLength(2);
  // payments plus the three inclusions; payments is not one of the three
  expect(checkboxes()).toHaveLength(4);
  expect(document.body.textContent).toContain(t("setup.settings.mode.title"));
  expect(document.body.textContent).toContain(t("setup.settings.payments.title"));
  expect(document.body.textContent).toContain(t("setup.settings.includes.title"));
});

it("names no tier when nothing is included", () => {
  const host = mount(<SettingsSection detail={detail()} onApplied={vi.fn()} />);
  expect(host.textContent).toContain(t("setup.settings.section.includesNothing"));
  // the words that used to name a state nothing stored
  expect(host.textContent).not.toMatch(/jednoduch|pokročil/i);
});

it("states all three tiers in one section", () => {
  const host = mount(
    <SettingsSection
      detail={detail({
        registrations_kept_by: "organizer",
        feature_payments: true,
        feature_extras: true,
      })}
      onApplied={vi.fn()}
    />,
  );
  expect(host.textContent).toContain(t("setup.settings.section.mode.organizer"));
  expect(host.textContent).toContain(t("setup.settings.section.payments.on"));
  expect(host.textContent).toContain(
    t("setup.settings.section.includes", {
      features: t("setup.settings.feature.extras").toLocaleLowerCase(),
    }),
  );
});

// ------------------------------------------------------------ the mode tier

it("confirms a mode change and states what stops", () => {
  const patch = vi.spyOn(api, "setRegistrationsKeptBy");
  mount(
    <TournamentSettingsDialog
      detail={detail({ in_app_registrations: 12 })}
      onApplied={vi.fn()}
      onClose={vi.fn()}
    />,
  );

  act(() => {
    modeRadios()[1].click();
  });
  act(() => buttonNamed(t("setup.settings.apply"))?.click());

  expect(document.body.textContent).toContain(t("setup.settings.mode.confirmToManual"));
  expect(document.body.textContent).toContain(
    t("setup.settings.mode.alreadyHeld", { count: 12 }),
  );
  expect(patch).not.toHaveBeenCalled();
});

it("writes the mode before the flags, so a later failure keeps the bigger choice", async () => {
  const order: string[] = [];
  const mode = vi
    .spyOn(api, "setRegistrationsKeptBy")
    .mockImplementation(async () => {
      order.push("mode");
      return detail({ registrations_kept_by: "organizer" });
    });
  const flags = vi.spyOn(api, "setTournamentFlags").mockImplementation(async () => {
    order.push("flags");
    return detail({ registrations_kept_by: "organizer" });
  });

  mount(
    <TournamentSettingsDialog detail={detail()} onApplied={vi.fn()} onClose={vi.fn()} />,
  );
  act(() => {
    modeRadios()[1].click();
  });
  act(() => buttonNamed(t("setup.settings.apply"))?.click());
  act(() => buttonNamed(t("setup.settings.confirm"))?.click());
  await settle();

  expect(order).toEqual(["mode", "flags"]);
  expect(mode).toHaveBeenCalledWith("cup", "organizer");
  expect(flags).toHaveBeenCalled();
});

it("says the mode was applied when only the flag write failed", async () => {
  vi.spyOn(api, "setRegistrationsKeptBy").mockResolvedValue(detail());
  vi.spyOn(api, "setTournamentFlags").mockRejectedValue(new Error("nope"));
  const applied = vi.fn();

  mount(
    <TournamentSettingsDialog detail={detail()} onApplied={applied} onClose={vi.fn()} />,
  );
  act(() => {
    modeRadios()[1].click();
  });
  act(() => buttonNamed(t("setup.settings.apply"))?.click());
  act(() => buttonNamed(t("setup.settings.confirm"))?.click());
  await settle();

  expect(applied).not.toHaveBeenCalled();
  expect(document.body.textContent).toContain(t("setup.settings.failedAfterMode"));
});

it("declining the confirmation writes nothing", () => {
  const mode = vi.spyOn(api, "setRegistrationsKeptBy");
  const flags = vi.spyOn(api, "setTournamentFlags");
  mount(
    <TournamentSettingsDialog detail={detail()} onApplied={vi.fn()} onClose={vi.fn()} />,
  );

  act(() => {
    modeRadios()[1].click();
  });
  act(() => buttonNamed(t("setup.settings.apply"))?.click());
  act(() => buttonNamed(t("common.back"))?.click());

  expect(mode).not.toHaveBeenCalled();
  expect(flags).not.toHaveBeenCalled();
  expect(modeRadios()).toHaveLength(2);
});

// ------------------------------------------------------- hiding an inclusion

it("warns before hiding a feature the tournament uses", () => {
  mount(
    <TournamentSettingsDialog
      detail={detail({
        feature_extras: true,
        extra_items: [{ id: 1 }, { id: 2 }] as TournamentDetail["extra_items"],
      })}
      onApplied={vi.fn()}
      onClose={vi.fn()}
    />,
  );
  const boxes = checkboxes();
  const extras = boxes[boxes.length - 1];
  act(() => extras.click());
  act(() => buttonNamed(t("setup.settings.apply"))?.click());

  expect(document.body.textContent).toContain(t("setup.settings.confirmIntro"));
  expect(document.body.textContent).toContain(t("setup.settings.stillSold"));
});

it("turning a feature on is never warned", async () => {
  const flags = vi.spyOn(api, "setTournamentFlags").mockResolvedValue(detail());
  mount(
    <TournamentSettingsDialog detail={detail()} onApplied={vi.fn()} onClose={vi.fn()} />,
  );
  const boxes = checkboxes();
  const extras = boxes[boxes.length - 1];
  act(() => extras.click());
  act(() => buttonNamed(t("setup.settings.apply"))?.click());
  await settle();

  expect(flags).toHaveBeenCalled();
});
