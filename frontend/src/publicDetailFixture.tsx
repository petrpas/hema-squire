// The harness the public detail page's tests share: the application mounted at
// a URL, and a tournament whose registration is open.
import { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import App from "./App";
import { ApiError, type Availability, api, type FencerTournament } from "./api";
import i18n from "./i18n";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

export const mounted: { host: HTMLElement | null } = { host: null };

export function mount(at: string) {
  const host = document.createElement("div");
  mounted.host = host;
  document.body.append(host);
  const root = createRoot(host);
  act(() =>
    root.render(
      <MemoryRouter initialEntries={[at]}>
        <App />
      </MemoryRouter>,
    ),
  );
  return host;
}

export async function settle() {
  await act(async () => {
    for (let i = 0; i < 6; i++) await Promise.resolve();
  });
}

export const DETAIL = {
  slug: "spring-open",
  display_name: "Spring Open",
  subtitle: null,
  has_logo: false,
  date: "2099-05-01",
  city: null,
  address: null,
  description: null,
  qualification_open: true,
  qualification_criteria: null,
  registration_instructions: null,
  organizers: [],
  disciplines: [
    {
      slug: "LS",
      name: "Longsword",
      ordinal: 1,
      weapon: "LS",
      gender: "open",
      material: "steel",
      kind: "individual",
      team_min: null,
      team_max: null,
      capacity: 20,
      fee: 800,
      fee_early: null,
      fee_eur: null,
      fee_early_eur: null,
      schedule_when: null,
      schedule_where: null,
      ruleset: null,
      identity_frozen: false,
    },
  ],
  extra_items: [],
  discounts: [],
  local_currency: "CZK",
  eur_payments_enabled: false,
  currency_mode: "local",
  registration_opens: null,
  registration_opens_time: null,
  registration_closes: null,
  amendments_close: null,
  team_composition_deadline: null,
  timezone: "Europe/Prague",
  registration_opens_at: null,
  server_time: "2026-09-12T10:00:00Z",
  registrations_kept_by: "squire",
  external_registration_url: null,
  feature_schedule: false,
  feature_payments: false,
  feature_teams: false,
  feature_extras: false,
} as unknown as FencerTournament;

export const AVAILABILITY = [
  { slug: "LS", kind: "individual", capacity: 20, taken: 1, entered: 1, free: 19, queue_length: 0 },
] as unknown as Availability[];

export function detailApi(over: Partial<FencerTournament> = {}) {
  vi.spyOn(api, "tournament").mockResolvedValue({ ...DETAIL, ...over });
  vi.spyOn(api, "availability").mockResolvedValue(AVAILABILITY);
  vi.spyOn(api, "openTournaments").mockResolvedValue([]);
  vi.spyOn(api, "heldTournaments").mockResolvedValue([]);
  vi.spyOn(api, "myTournaments").mockRejectedValue(new ApiError(401, "x"));
}

export function registerTab(page: HTMLElement): HTMLButtonElement | undefined {
  return [...page.querySelectorAll<HTMLButtonElement>(".detail-tabs button")].find(
    (b) => b.textContent === i18n.t("detail.tabs.register"),
  );
}
