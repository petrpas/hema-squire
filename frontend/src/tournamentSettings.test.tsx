// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";

import { api, type TournamentDetail } from "./api";
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

const t = i18n.getFixedT(i18n.language);

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

function paymentRadios() {
  return [...document.querySelectorAll<HTMLInputElement>('input[name="tournament-payments"]')];
}

function checkboxes() {
  return [...document.querySelectorAll<HTMLInputElement>('input[type="checkbox"]')];
}

function detail(overrides: Partial<TournamentDetail> = {}): TournamentDetail {
  return {
    slug: "cup",
    registrations_kept_by: "squire",
    published_at: null,
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
  mount(<TournamentSettingsDialog detail={detail()} onApplied={vi.fn()} onClose={vi.fn()} />);
  expect(modeRadios()).toHaveLength(2);
  // payments is a named choice between two, like the mode above it — both
  // behavioural settings are answered rather than one being the absence of
  // the other. The three inclusions are checkboxes; payments is not among them
  expect(paymentRadios()).toHaveLength(2);
  expect(checkboxes()).toHaveLength(3);
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
  // the tournament under test is manual, so the payments line is the manual
  // one: what payments on adds there is matching, not the whole machinery
  expect(host.textContent).toContain(t("setup.settings.section.payments.manual.on"));
  expect(host.textContent).toContain(
    t("setup.settings.section.includes", {
      features: t("setup.settings.feature.extras").toLocaleLowerCase(),
    }),
  );
});

// ------------------------------------------------------------ the mode tier

it("asks no confirmation for a mode change, and writes it", async () => {
  // The confirmation's whole content was a count of in-app registrations, and
  // the only tournaments that can still switch are drafts, which hold none
  // (spec tournament-mode, design Decision 3).
  const patch = vi
    .spyOn(api, "setRegistrationsKeptBy")
    .mockResolvedValue(detail({ registrations_kept_by: "organizer" }));
  vi.spyOn(api, "setTournamentFlags").mockResolvedValue(detail());
  mount(<TournamentSettingsDialog detail={detail()} onApplied={vi.fn()} onClose={vi.fn()} />);

  act(() => {
    modeRadios()[1]!.click();
  });
  act(() => buttonNamed(t("setup.settings.apply"))?.click());
  await settle();

  expect(patch).toHaveBeenCalledWith("cup", "organizer");
});

it("states the mode instead of offering it once the tournament is published", () => {
  mount(
    <TournamentSettingsDialog
      detail={detail({ registrations_kept_by: "organizer", published_at: "2026-09-01T00:00:00Z" })}
      onApplied={vi.fn()}
      onClose={vi.fn()}
    />,
  );

  expect(modeRadios()).toHaveLength(0);
  expect(document.body.textContent).toContain(t("setup.settings.mode.organizer"));
  expect(document.body.textContent).toContain(t("setup.settings.mode.fixedAtPublication"));
});

it("still offers the payments setting and the inclusions once published", () => {
  mount(
    <TournamentSettingsDialog
      detail={detail({ published_at: "2026-09-01T00:00:00Z" })}
      onApplied={vi.fn()}
      onClose={vi.fn()}
    />,
  );

  expect(document.querySelectorAll('input[name="tournament-payments"]').length).toBeGreaterThan(0);
  expect(document.querySelectorAll('input[type="checkbox"]').length).toBeGreaterThan(0);
});

it("writes the mode before the flags, so a later failure keeps the bigger choice", async () => {
  const order: string[] = [];
  const mode = vi.spyOn(api, "setRegistrationsKeptBy").mockImplementation(async () => {
    order.push("mode");
    return detail({ registrations_kept_by: "organizer" });
  });
  const flags = vi.spyOn(api, "setTournamentFlags").mockImplementation(async () => {
    order.push("flags");
    return detail({ registrations_kept_by: "organizer" });
  });

  mount(<TournamentSettingsDialog detail={detail()} onApplied={vi.fn()} onClose={vi.fn()} />);
  act(() => {
    modeRadios()[1]!.click();
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

  mount(<TournamentSettingsDialog detail={detail()} onApplied={applied} onClose={vi.fn()} />);
  act(() => {
    modeRadios()[1]!.click();
  });
  act(() => buttonNamed(t("setup.settings.apply"))?.click());
  act(() => buttonNamed(t("setup.settings.confirm"))?.click());
  await settle();

  expect(applied).not.toHaveBeenCalled();
  expect(document.body.textContent).toContain(t("setup.settings.failedAfterMode"));
});

it("declining the confirmation writes nothing", () => {
  // the confirmation that remains is the one about losing a feature in use;
  // a mode change no longer raises one
  const mode = vi.spyOn(api, "setRegistrationsKeptBy");
  const flags = vi.spyOn(api, "setTournamentFlags");
  mount(
    <TournamentSettingsDialog
      detail={detail({
        feature_extras: true,
        extra_items: [{ id: 1 }] as TournamentDetail["extra_items"],
      })}
      onApplied={vi.fn()}
      onClose={vi.fn()}
    />,
  );

  const boxes = checkboxes();
  act(() => boxes[boxes.length - 1]!.click());
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
  const extras = boxes[boxes.length - 1]!;
  act(() => extras.click());
  act(() => buttonNamed(t("setup.settings.apply"))?.click());

  expect(document.body.textContent).toContain(t("setup.settings.confirmIntro"));
  expect(document.body.textContent).toContain(t("setup.settings.stillSold"));
});

it("turning a feature on is never warned", async () => {
  const flags = vi.spyOn(api, "setTournamentFlags").mockResolvedValue(detail());
  mount(<TournamentSettingsDialog detail={detail()} onApplied={vi.fn()} onClose={vi.fn()} />);
  const boxes = checkboxes();
  const extras = boxes[boxes.length - 1]!;
  act(() => extras.click());
  act(() => buttonNamed(t("setup.settings.apply"))?.click());
  await settle();

  expect(flags).toHaveBeenCalled();
});

it("states both payment answers by what each gives, not by what it withholds", () => {
  mount(<TournamentSettingsDialog detail={detail()} onApplied={vi.fn()} onClose={vi.fn()} />);
  const text = document.body.textContent ?? "";
  expect(text).toContain(t("setup.settings.payments.consequence.automatic.squire"));
  expect(text).toContain(t("setup.settings.payments.consequence.automatic.self"));
  // neither answer is described as the other one turned off
  expect(text).not.toMatch(/vypnut|nepoužívá|bez plateb/i);
});

it("says what payments do in the mode actually selected", () => {
  // The setting means two different things. In automatic mode, payments on is
  // the whole machinery. In manual mode the scheduler never sees the
  // tournament and the roster arrived by import, so everything else is already
  // suspended and what payments on adds is matching against the statement —
  // which is the only thing an organizer in that mode wants to know.
  mount(<TournamentSettingsDialog detail={detail()} onApplied={vi.fn()} onClose={vi.fn()} />);
  expect(document.body.textContent).toContain(
    t("setup.settings.payments.consequence.automatic.squire"),
  );

  act(() => {
    modeRadios()[1]!.click();
  });

  const text = document.body.textContent ?? "";
  expect(text).toContain(t("setup.settings.payments.consequence.manual.squire"));
  expect(text).not.toContain(t("setup.settings.payments.consequence.automatic.squire"));
});

it("choosing to handle payments yourself is written like any other flag", async () => {
  const flags = vi
    .spyOn(api, "setTournamentFlags")
    .mockResolvedValue(detail({ feature_payments: false }));
  mount(
    <TournamentSettingsDialog
      detail={detail({ feature_payments: true })}
      onApplied={vi.fn()}
      onClose={vi.fn()}
    />,
  );
  act(() => {
    paymentRadios()[1]!.click();
  });
  act(() => buttonNamed(t("setup.settings.apply"))?.click());
  await settle();

  expect(flags).toHaveBeenCalledWith("cup", expect.objectContaining({ feature_payments: false }));
});
