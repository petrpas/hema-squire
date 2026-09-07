// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";

import { api, type TournamentDetail } from "./api";
import i18n from "./i18n";
import { TournamentSettingsFields } from "./TournamentSettingsDialog";

// Nothing is created until the settings panel is confirmed. The tournament
// used to be persisted before that panel was shown; the cost was a tournament
// brought into existence by an act the organizer then backed out of.

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

function draft(): TournamentDetail {
  return {
    slug: "",
    registrations_kept_by: "squire",
    in_app_registrations: 0,
    feature_schedule: false,
    feature_payments: false,
    feature_teams: false,
    feature_extras: false,
    payment_mode: "immediate",
    bank_account: null,
    deposit_amount: null,
    disciplines: [],
    extra_items: [],
  } as unknown as TournamentDetail;
}

async function settle() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

it("reports what was chosen instead of writing it", async () => {
  const confirm = vi.fn().mockResolvedValue(undefined);
  const mode = vi.spyOn(api, "setRegistrationsKeptBy");
  const flags = vi.spyOn(api, "setTournamentFlags");

  mount(
    <TournamentSettingsFields
      detail={draft()}
      onApplied={vi.fn()}
      onClose={vi.fn()}
      onConfirm={confirm}
    />,
  );
  const radios = [...document.querySelectorAll<HTMLInputElement>('input[name="tournament-mode"]')];
  act(() => radios[1]!.click());
  act(() => buttonNamed(t("setup.settings.apply"))?.click());
  await settle();

  expect(confirm).toHaveBeenCalledWith({
    mode: "organizer",
    flags: expect.objectContaining({ feature_payments: false }),
  });
  // nothing is written from here: the caller creates the tournament with it
  expect(mode).not.toHaveBeenCalled();
  expect(flags).not.toHaveBeenCalled();
});

it("asks for no confirmation on a tournament that does not exist yet", async () => {
  // the warnings count what a change would hide, and a draft holds nothing
  const confirm = vi.fn().mockResolvedValue(undefined);
  mount(
    <TournamentSettingsFields
      detail={draft()}
      onApplied={vi.fn()}
      onClose={vi.fn()}
      onConfirm={confirm}
    />,
  );
  const radios = [...document.querySelectorAll<HTMLInputElement>('input[name="tournament-mode"]')];
  act(() => radios[1]!.click());
  act(() => buttonNamed(t("setup.settings.apply"))?.click());
  await settle();

  expect(document.body.textContent).not.toContain(t("setup.settings.confirmIntro"));
  expect(confirm).toHaveBeenCalled();
});

it("cancelling reports nothing and creates nothing", () => {
  const confirm = vi.fn();
  const close = vi.fn();
  mount(
    <TournamentSettingsFields
      detail={draft()}
      onApplied={vi.fn()}
      onClose={close}
      onConfirm={confirm}
    />,
  );
  act(() => buttonNamed(t("common.cancel"))?.click());

  expect(close).toHaveBeenCalled();
  expect(confirm).not.toHaveBeenCalled();
});

it("asks nothing extra for a mode change on a tournament that exists", () => {
  // The draft path used to be the exception. Now no path confirms a mode
  // change: it can only be made while the tournament is a draft, which holds
  // no in-app registration for a warning to count (spec tournament-mode).
  const detail = { ...draft(), slug: "cup", in_app_registrations: 0 };
  mount(<TournamentSettingsFields detail={detail} onApplied={vi.fn()} onClose={vi.fn()} />);
  const radios = [...document.querySelectorAll<HTMLInputElement>('input[name="tournament-mode"]')];
  act(() => radios[1]!.click());
  act(() => buttonNamed(t("setup.settings.apply"))?.click());

  expect(document.body.textContent).not.toContain(t("setup.settings.confirmIntro"));
});
