// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter, Outlet, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { type Account, api, type Sheet, type TournamentDetail } from "./api";
import Console from "./Console";
import i18n from "./i18n";
import PrivacyPage from "./PrivacyPage";
import { privacy } from "./routes";
import SignupForm from "./SignupForm";

// The privacy baseline on screen (spec privacy): the notice is a page of its
// own, every collecting form leads to it without asking for a tick, and the
// organizer data terms stand between an owner and the console until accepted.

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let host: HTMLElement | null = null;

function render(node: React.ReactNode, at = "/") {
  host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  act(() => root.render(<MemoryRouter initialEntries={[at]}>{node}</MemoryRouter>));
  return host;
}

async function settle() {
  await act(async () => {
    for (let i = 0; i < 6; i++) await Promise.resolve();
  });
}

beforeEach(async () => {
  vi.restoreAllMocks();
  await i18n.changeLanguage("en");
});

afterEach(() => {
  host?.remove();
  host = null;
});

describe("the privacy page", () => {
  it("names the controller and the contact and states what stays on rosters", () => {
    const page = render(<PrivacyPage />);
    const text = page.textContent ?? "";
    expect(text).toContain("Petr Paščenko");
    expect(text).toContain("privacy@hemasquire.eu");
    expect(text).toContain("not anonymised");
    expect(page.querySelectorAll("h2").length).toBeGreaterThan(5);
  });
});

describe("the collection notice", () => {
  it("stands on the guest form with a link and nothing to tick", () => {
    const page = render(
      <SignupForm variant={{ kind: "guest", onGuest: () => {} }} onCancel={() => {}} />,
    );
    const notice = page.querySelector(".privacy-notice");
    expect(notice?.querySelector("a")?.getAttribute("href")).toBe(privacy());
    expect(page.querySelector('input[type="checkbox"]')).toBeNull();
  });
});

describe("the organizer data terms", () => {
  const tournament = {
    slug: "cup",
    display_name: "Cup",
    date: "2099-12-05",
    owner_id: 5,
    published_at: "2099-01-01T00:00:00Z",
    registrations_kept_by: "squire",
    feature_schedule: false,
    feature_payments: true,
    feature_teams: false,
    feature_extras: false,
  } as unknown as TournamentDetail;
  const account = (id: number, due: boolean) =>
    ({ id, display_name: "O", organized_count: 1, organizer_terms_due: due }) as Account;

  function mountConsole() {
    const path = "/organizer/cup/console/fencers";
    return render(
      <Routes>
        <Route element={<Outlet context={{ onLogout: () => {} }} />}>
          <Route path={path} element={<Console tournament={tournament} phase="fencers" />} />
        </Route>
      </Routes>,
      path,
    );
  }

  beforeEach(() => {
    vi.spyOn(api, "sheet").mockResolvedValue({ rows: [], edits: [] } as unknown as Sheet);
    vi.spyOn(api, "tournament").mockResolvedValue(tournament as never);
    vi.spyOn(api, "operations").mockResolvedValue({ running: null, concluded: [] } as never);
  });

  it("are put to the owner, and accepting lets the console be used", async () => {
    vi.spyOn(api, "account").mockResolvedValue(account(5, true));
    const accept = vi.spyOn(api, "acceptOrganizerTerms").mockResolvedValue(account(5, false));
    const page = mountConsole();
    await settle();

    const dialog = page.querySelector("dialog .modal");
    expect(dialog?.textContent).toContain(i18n.t("privacy.terms.title"));
    const agree = [...(dialog?.querySelectorAll("button") ?? [])].find(
      (button) => button.textContent === i18n.t("privacy.terms.accept"),
    );
    act(() => agree?.dispatchEvent(new MouseEvent("click", { bubbles: true })));
    await settle();

    expect(accept).toHaveBeenCalledOnce();
    expect(page.querySelector("dialog .modal")).toBeNull();
  });

  it("are not put to a team member, even one owing them for a tournament of their own", async () => {
    vi.spyOn(api, "account").mockResolvedValue(account(6, true));
    const page = mountConsole();
    await settle();

    expect(page.querySelector("dialog .modal")).toBeNull();
  });
});
