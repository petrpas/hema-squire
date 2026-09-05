// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";

import { type TournamentDetail } from "./api";
import ExternalRegistrationNotice from "./ExternalRegistrationNotice";
import i18n from "./i18n";
import { registrationStatus } from "./openingMoment";

// Where a tournament's registration lives when Squire does not hold it (spec
// external-registration). The surfaces state where registration is; none of
// them says it is closed, which would be a false account of a window that
// never existed here.

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

function detail(overrides: Partial<TournamentDetail> = {}): TournamentDetail {
  return {
    slug: "cup",
    date: "2026-12-05",
    timezone: "Europe/Prague",
    registrations_kept_by: "squire",
    external_registration_url: null,
    registration_opens_at: null,
    registration_closes: null,
    ...overrides,
  } as unknown as TournamentDetail;
}

it("offers the way out and names where registration is", () => {
  mount(
    <ExternalRegistrationNotice
      detail={detail({ external_registration_url: "https://forms.example.org/x" })}
    />,
  );
  expect(host?.textContent).toContain(t("detail.registrationElsewhere"));
  const link = host?.querySelector("a") as HTMLAnchorElement;
  expect(link.href).toBe("https://forms.example.org/x");
  expect(link.target).toBe("_blank");
  expect(link.rel).toContain("noopener");
});

it("never says registration is closed", () => {
  mount(
    <ExternalRegistrationNotice
      detail={detail({ external_registration_url: "https://forms.example.org/x" })}
    />,
  );
  expect(host?.textContent).not.toContain(t("detail.closedNotice"));
});

it("states it without an action where no address is recorded", () => {
  mount(<ExternalRegistrationNotice detail={detail()} />);
  expect(host?.textContent).toContain(t("detail.registrationElsewhere"));
  expect(host?.querySelector("a")).toBeNull();
});

// ------------------------------------------------- the client-side gate mirror

it("an organizer-kept tournament reads as elsewhere, not closed", () => {
  const kept = detail({ registrations_kept_by: "organizer" });
  expect(registrationStatus(kept, Date.parse("2026-10-01T12:00:00Z"))).toBe("elsewhere");
});

it("it reads as elsewhere even after the closing date", () => {
  const kept = detail({
    registrations_kept_by: "organizer",
    registration_closes: "2026-01-01",
  });
  expect(registrationStatus(kept, Date.parse("2026-10-01T12:00:00Z"))).toBe("elsewhere");
});

it("a Squire-kept tournament is unaffected", () => {
  expect(registrationStatus(detail(), Date.parse("2026-10-01T12:00:00Z"))).toBe("open");
  expect(
    registrationStatus(
      detail({ registration_closes: "2026-01-01" }),
      Date.parse("2026-10-01T12:00:00Z"),
    ),
  ).toBe("closed");
});
