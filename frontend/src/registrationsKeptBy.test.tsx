// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";

import { type TournamentDetail, api } from "./api";
import i18n from "./i18n";
import RegistrationsKeptByDialog from "./RegistrationsKeptBy";
import { RegistrationsKeptBySection } from "./setup/RegistrationsKeptBySection";
import TournamentModeDialog from "./TournamentModeDialog";

// Who keeps the tournament's list of entrants (spec registration-ownership).
// Its own section, never a fifth feature in the mode dialog: the mode dialog's
// own explanation is that turning a feature off hides settings without
// changing behaviour, and this closes the registration form.

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const t = i18n.getFixedT("cs");

let host: HTMLElement | null = null;

function mount(element: React.ReactElement) {
  host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  act(() => root.render(element));
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

function radios() {
  return [...document.querySelectorAll<HTMLInputElement>(
    'input[name="registrations-kept-by"]',
  )];
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

// ------------------------------------------------------------- the section

it("states which way round the tournament is, in words", () => {
  mount(
    <RegistrationsKeptBySection
      detail={detail({ registrations_kept_by: "organizer" })}
      onApplied={vi.fn()}
    />,
  );
  expect(host?.textContent).toContain(t("setup.keptBy.section.organizer"));
  expect(host?.textContent).toContain(t("setup.keptBy.consequence.organizer"));
});

it("opens the choice from the section", () => {
  mount(<RegistrationsKeptBySection detail={detail()} onApplied={vi.fn()} />);
  act(() => buttonNamed(t("setup.keptBy.section.change"))?.click());
  expect(radios()).toHaveLength(2);
});

// -------------------------------------------------------- changing the value

it("confirms before it changes anything, and states what stops", () => {
  mount(
    <RegistrationsKeptByDialog
      detail={detail({ in_app_registrations: 12 })}
      onApplied={vi.fn()}
      onClose={vi.fn()}
    />,
  );
  const patch = vi.spyOn(api, "setRegistrationsKeptBy");

  act(() => {
    radios()[1].click();
  });
  act(() => buttonNamed(t("setup.keptBy.apply"))?.click());

  expect(document.body.textContent).toContain(t("setup.keptBy.confirmToOrganizer"));
  expect(document.body.textContent).toContain(
    t("setup.keptBy.alreadyHeld", { count: 12 }),
  );
  // the count is stated before anything is written, not after
  expect(patch).not.toHaveBeenCalled();
});

it("writes only once the confirmation is accepted", async () => {
  const applied = vi.fn();
  const patch = vi
    .spyOn(api, "setRegistrationsKeptBy")
    .mockResolvedValue(detail({ registrations_kept_by: "organizer" }));
  mount(
    <RegistrationsKeptByDialog detail={detail()} onApplied={applied} onClose={vi.fn()} />,
  );

  act(() => {
    radios()[1].click();
  });
  act(() => buttonNamed(t("setup.keptBy.apply"))?.click());
  act(() => buttonNamed(t("setup.keptBy.confirm"))?.click());
  await settle();

  expect(patch).toHaveBeenCalledWith("cup", "organizer");
  expect(applied).toHaveBeenCalled();
});

it("declining the confirmation writes nothing", () => {
  const patch = vi.spyOn(api, "setRegistrationsKeptBy");
  mount(
    <RegistrationsKeptByDialog detail={detail()} onApplied={vi.fn()} onClose={vi.fn()} />,
  );

  act(() => {
    radios()[1].click();
  });
  act(() => buttonNamed(t("setup.keptBy.apply"))?.click());
  act(() => buttonNamed(t("common.back"))?.click());

  expect(patch).not.toHaveBeenCalled();
  expect(radios()).toHaveLength(2);
});

it("confirms the other direction too, stating what starts", () => {
  mount(
    <RegistrationsKeptByDialog
      detail={detail({ registrations_kept_by: "organizer" })}
      onApplied={vi.fn()}
      onClose={vi.fn()}
    />,
  );
  act(() => {
    radios()[0].click();
  });
  act(() => buttonNamed(t("setup.keptBy.apply"))?.click());
  expect(document.body.textContent).toContain(t("setup.keptBy.confirmToSquire"));
});

it("says that nothing already registered is written by the change", () => {
  mount(
    <RegistrationsKeptByDialog detail={detail()} onApplied={vi.fn()} onClose={vi.fn()} />,
  );
  act(() => {
    radios()[1].click();
  });
  act(() => buttonNamed(t("setup.keptBy.apply"))?.click());
  expect(document.body.textContent).toContain(t("setup.keptBy.nothingIsWritten"));
});

// ------------------------------------------------- the two axes stay apart

it("the mode dialog offers four features and nothing about who keeps them", () => {
  mount(
    <TournamentModeDialog detail={detail()} onApplied={vi.fn()} onClose={vi.fn()} />,
  );
  expect(document.body.textContent).not.toContain(t("setup.keptBy.option.organizer"));
  expect(radios()).toHaveLength(0);
});
