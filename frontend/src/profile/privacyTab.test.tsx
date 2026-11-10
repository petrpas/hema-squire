// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import { type Account, api, setToken } from "../api";
import i18n from "../i18n";
import { profile } from "../routes";

// The Profile page keeps everything about the account's personal data on one
// tab of its own, reachable by address (spec profile-page, The Profile page
// has a Privacy tab).

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let host: HTMLElement | null = null;

const ACCOUNT = {
  id: 1,
  email: "me@example.com",
  display_name: "Me",
  hr_id: null,
  nationality: null,
  club: null,
  language: "en",
  role: "organizer",
  is_deployment_owner: false,
  organized_count: 1,
  organizer_terms_due: false,
  organizer_terms_version: "2026-11-03",
  organizer_terms_accepted_at: "2026-11-03T10:00:00Z",
  deletion_effective_at: null,
} as Account;

async function mount(at: string) {
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
  await act(async () => {
    for (let i = 0; i < 8; i++) await Promise.resolve();
  });
  return host;
}

beforeEach(async () => {
  vi.restoreAllMocks();
  setToken("t");
  vi.spyOn(api, "account").mockResolvedValue(ACCOUNT);
  vi.spyOn(api, "hrNationalities").mockResolvedValue([]);
  await i18n.changeLanguage("en");
});

afterEach(() => {
  host?.remove();
  host = null;
  setToken(null);
});

describe("the Privacy tab", () => {
  it("gathers the notice, the download, the accepted terms and deletion", async () => {
    const page = await mount(profile("privacy"));
    const text = page.textContent ?? "";

    expect(page.querySelector('[role="tab"][aria-selected="true"]')?.textContent).toBe(
      i18n.t("profile.tabs.privacy"),
    );
    expect(text).toContain("privacy@hemasquire.eu");
    expect(text).toContain(i18n.t("privacy.download.action"));
    expect(text).toContain(i18n.t("profile.deletion.open"));
  });

  it("keeps the organizer terms behind a button below the other sections", async () => {
    const page = await mount(profile("privacy"));
    const panel = page.querySelector('[role="tabpanel"]');
    const button = panel?.lastElementChild;

    expect(button?.tagName).toBe("BUTTON");
    expect(button?.textContent).toBe(i18n.t("privacy.terms.title"));
    expect(page.textContent).not.toContain("2026-11-03");

    act(() => (button as HTMLButtonElement).click());

    const dialog = page.querySelector("dialog");
    expect(dialog?.textContent).toContain("2026-11-03");
    const paragraphs = i18n.t("privacy.terms.paragraphs", { returnObjects: true }) as string[];
    expect(dialog?.textContent).toContain(paragraphs[0]);
  });

  it("offers no terms to an account that never owed them", async () => {
    vi.spyOn(api, "account").mockResolvedValue({
      ...ACCOUNT,
      organizer_terms_version: null,
      organizer_terms_accepted_at: null,
    });
    const page = await mount(profile("privacy"));

    expect(page.textContent).not.toContain(i18n.t("privacy.terms.title"));
  });

  it("leaves the Profile tab to who the account is", async () => {
    const page = await mount(profile());
    const text = page.textContent ?? "";

    expect(text).toContain(i18n.t("profile.account.title"));
    expect(text).not.toContain(i18n.t("profile.deletion.open"));
    expect(text).not.toContain(i18n.t("privacy.download.action"));
  });
});
