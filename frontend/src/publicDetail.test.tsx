// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import {
  type Account,
  ApiError,
  type Availability,
  api,
  type FencerTournament,
  getToken,
  setToken,
} from "./api";
import i18n from "./i18n";

// A tournament's detail reads without an account, and the Register action it
// offers leads to sign-in rather than to a form that could only fail (change
// `public-tournament-list`).

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let host: HTMLElement | null = null;

function mount(at: string) {
  host = document.createElement("div");
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

async function settle() {
  await act(async () => {
    for (let i = 0; i < 6; i++) await Promise.resolve();
  });
}

const DETAIL = {
  slug: "spring-open",
  display_name: "Spring Open",
  subtitle: null,
  has_logo: false,
  date: "2099-05-01",
  location: null,
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

const AVAILABILITY = [
  { slug: "LS", kind: "individual", capacity: 20, taken: 1, free: 19, queue_length: 0 },
] as unknown as Availability[];

function detailApi() {
  vi.spyOn(api, "tournament").mockResolvedValue(DETAIL);
  vi.spyOn(api, "availability").mockResolvedValue(AVAILABILITY);
  vi.spyOn(api, "openTournaments").mockResolvedValue([]);
  vi.spyOn(api, "heldTournaments").mockResolvedValue([]);
  vi.spyOn(api, "myTournaments").mockRejectedValue(new ApiError(401, "x"));
}

function registerTab(page: HTMLElement): HTMLButtonElement | undefined {
  return [...page.querySelectorAll<HTMLButtonElement>(".detail-tabs button")].find(
    (b) => b.textContent === i18n.t("detail.tabs.register"),
  );
}

beforeEach(async () => {
  vi.restoreAllMocks();
  setToken(null);
  await i18n.changeLanguage("cs");
});

afterEach(() => {
  host?.remove();
  host = null;
  setToken(null);
});

describe("a tournament's detail is public", () => {
  it("renders without a credential, asking nothing personal", async () => {
    detailApi();
    const mine = vi.spyOn(api, "myRegistration");

    const page = mount("/t/spring-open");
    await settle();

    expect(page.querySelector("form#login-form")).toBeNull();
    expect(page.textContent).toContain("Spring Open");
    expect(mine).not.toHaveBeenCalled();
  });

  it("shows none of the four filter tabs while it is open", async () => {
    detailApi();
    const page = mount("/t/spring-open");
    await settle();

    expect(page.querySelector(".home-tabs")).toBeNull();
    expect(page.textContent).not.toContain(i18n.t("home.tabs.announced"));
  });

  it("keeps the shared top bar", async () => {
    detailApi();
    const page = mount("/t/spring-open");
    await settle();

    expect(page.querySelector(".topbar .logo")?.textContent).toBe("HEMA Squire");
    expect(page.querySelector(".topbar-title")?.textContent).toBe("Šermířské turnaje a akce");
    expect(page.querySelector(".detail-header h1")?.textContent).toBe("Spring Open");
  });
});

describe("registering while signed out", () => {
  it("leads to sign-in, stating why", async () => {
    detailApi();
    const page = mount("/t/spring-open");
    await settle();

    const register = registerTab(page);
    expect(register).not.toBeUndefined();
    await act(async () => {
      register?.click();
    });

    expect(page.querySelector("form#login-form")).not.toBeNull();
    // the sign-in screen renders in English, so the reason does too
    expect(page.querySelector(".login-notice")?.textContent).toBe(
      "Registering for a tournament needs an account.",
    );
  });

  it("comes back to the tournament on its registration tab", async () => {
    detailApi();
    vi.spyOn(api, "login").mockResolvedValue({ token: "fresh" } as never);
    vi.spyOn(api, "account").mockResolvedValue({
      display_name: "F",
      language: "cs",
      role: "fencer",
    } as Account);
    vi.spyOn(api, "myRegistration").mockRejectedValue(new ApiError(404, "none"));

    const page = mount("/t/spring-open");
    await settle();
    await act(async () => {
      registerTab(page)?.click();
    });

    const form = page.querySelector<HTMLFormElement>("form#login-form");
    const email = form?.querySelector<HTMLInputElement>('input[name="email"]');
    const password = form?.querySelector<HTMLInputElement>('input[name="password"]');
    await act(async () => {
      if (email) {
        email.value = "f@example.com";
        email.dispatchEvent(new Event("input", { bubbles: true }));
      }
      if (password) {
        password.value = "correct-horse";
        password.dispatchEvent(new Event("input", { bubbles: true }));
      }
    });
    await act(async () => {
      form?.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    });
    await settle();

    expect(getToken()).toBe("fresh");
    expect(page.querySelector("form#login-form")).toBeNull();
    const active = page.querySelector(".detail-tabs button.active");
    expect(active?.textContent).toBe(i18n.t("detail.tabs.register"));
  });
});
