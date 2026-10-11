// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import type { Availability, FencerTournament } from "./api";
import i18n from "./i18n";
import { DisciplinesInfo, InfoHeader } from "./TournamentFace";

// The detail opens on its card's cover and carries the card's meters (change
// align-fencer-detail).

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let host: HTMLElement | null = null;
let root: Root | null = null;

function render(node: React.ReactNode): HTMLElement {
  host = document.createElement("div");
  document.body.append(host);
  root = createRoot(host);
  act(() => root?.render(<MemoryRouter>{node}</MemoryRouter>));
  return host;
}

const NOW = Date.parse("2026-10-01T10:00:00Z");

function detail(over: Partial<FencerTournament> = {}): FencerTournament {
  return {
    slug: "spring-open",
    display_name: "Spring Open",
    subtitle: null,
    short_code: null,
    has_logo: false,
    logo_tint: null,
    date: "2026-11-20",
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
        kind: "individual",
        capacity: 4,
        fee: 500,
        fee_eur: null,
        schedule_when: null,
        schedule_where: null,
        ruleset: null,
      },
    ],
    extra_items: [],
    discounts: [],
    local_currency: "CZK",
    eur_payments_enabled: false,
    currency_mode: "local",
    registration_opens: null,
    registration_opens_time: null,
    registration_closes: "2026-11-15",
    amendments_close: null,
    team_composition_deadline: null,
    timezone: "Europe/Prague",
    registration_opens_at: null,
    server_time: "2026-10-01T10:00:00Z",
    registrations_kept_by: "squire",
    external_registration_url: null,
    feature_schedule: false,
    feature_payments: true,
    feature_teams: false,
    feature_extras: false,
    ...over,
  } as unknown as FencerTournament;
}

beforeEach(async () => {
  await i18n.changeLanguage("cs");
});

afterEach(() => {
  act(() => root?.unmount());
  host?.remove();
  host = null;
  root = null;
});

describe("the detail's cover", () => {
  it("wears the logo's tint and rings the plate while registration is open", () => {
    const page = render(
      <InfoHeader detail={detail({ logo_tint: "green", has_logo: true })} now={NOW} />,
    );
    expect(page.querySelector(".detail-cover")?.getAttribute("data-tint")).toBe("green");
    expect(page.querySelector(".detail-plate")?.getAttribute("data-ring")).toBe("open");
    expect(page.querySelector(".status-block")?.textContent).toBe("registraceotevřenado 15. 11.");
  });

  it("states a coming opening and leaves the ring at rest", () => {
    const page = render(
      <InfoHeader
        detail={detail({
          registration_opens: "2026-10-05",
          registration_opens_at: "2026-10-05T08:00:00+02:00",
        })}
        now={NOW}
      />,
    );
    expect(page.querySelector(".detail-plate")?.getAttribute("data-ring")).toBe("rest");
    expect(page.querySelector(".status-block")?.textContent).toContain("od 5. 10.");
  });

  it("shows the short code where there is no logo", () => {
    const page = render(<InfoHeader detail={detail({ short_code: "SPO" })} now={NOW} />);
    expect(page.querySelector(".detail-plate")?.textContent).toBe("SPO");
  });
});

describe("the detail's disciplines", () => {
  it("draw a hidden meter under each row, full in its own state", () => {
    const availability = [
      {
        slug: "LS",
        kind: "individual",
        capacity: 4,
        taken: 4,
        entered: 4,
        free: 0,
        queue_length: 1,
      },
    ] as unknown as Availability[];
    const page = render(<DisciplinesInfo detail={detail()} availability={availability} />);
    const meter = page.querySelector(".detail-meter");
    expect(meter?.hasAttribute("data-full")).toBe(true);
    expect(meter?.querySelector(".meter-track")?.getAttribute("aria-hidden")).toBe("true");
    expect(meter?.querySelector<HTMLElement>(".meter-fill")?.style.width).toBe("100%");
  });
});
