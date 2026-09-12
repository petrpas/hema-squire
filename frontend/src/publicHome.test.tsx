// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { type Account, ApiError, api, type OpenTournament, setToken } from "./api";
import i18n from "./i18n";

// One tournament list for every visitor, readable without an account, with the
// filter tabs above it and the application's title in the bar (change
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
    for (let i = 0; i < 5; i++) await Promise.resolve();
  });
}

function tournament(slug: string, over: Partial<OpenTournament> = {}): OpenTournament {
  return {
    slug,
    display_name: slug,
    subtitle: null,
    has_logo: false,
    date: "2026-09-20",
    city: null,
    description: null,
    qualification_open: true,
    qualification_criteria: null,
    local_currency: "CZK",
    organizers: [],
    registration_status: "open",
    registration_opens_on: null,
    registration_opens_at: null,
    timezone: "Europe/Prague",
    server_time: "2026-09-12T10:00:00Z",
    disciplines: [],
    ...over,
  } as OpenTournament;
}

const ACCOUNT = { display_name: "F", language: "cs", role: "fencer" } as unknown as Account;

/** What the three list scopes answer. Mine is left refusing, as the server
 *  does without a credential. */
function lists(scopes: {
  upcoming?: OpenTournament[];
  held?: OpenTournament[];
  mine?: OpenTournament[] | "refused";
}) {
  vi.spyOn(api, "openTournaments").mockResolvedValue(scopes.upcoming ?? []);
  vi.spyOn(api, "heldTournaments").mockResolvedValue(scopes.held ?? []);
  const mine = scopes.mine ?? "refused";
  vi.spyOn(api, "myTournaments").mockImplementation(() =>
    mine === "refused" ? Promise.reject(new ApiError(401, "x")) : Promise.resolve(mine),
  );
}

/** A tab's label without the entry count that may follow it. */
function label(tab: Element | null | undefined): string {
  if (!tab) return "";
  return [...tab.childNodes]
    .filter((node) => !(node instanceof HTMLElement && node.className === "tab-count"))
    .map((node) => node.textContent ?? "")
    .join("");
}

function tabNames(page: HTMLElement): string[] {
  return [...page.querySelectorAll(".home-tabs a")].map(label);
}

function activeTab(page: HTMLElement): string {
  return label(page.querySelector(".home-tabs a.active"));
}

beforeEach(async () => {
  vi.restoreAllMocks();
  setToken(null);
  // awaited: an unresolved changeLanguage would land after the one a test
  // makes and quietly put the language back
  await i18n.changeLanguage("en");
});

afterEach(() => {
  host?.remove();
  host = null;
  setToken(null);
});

describe("the list is public", () => {
  it("renders for a visitor with no account, with no account request issued", async () => {
    lists({ upcoming: [tournament("spring-open")] });
    const account = vi.spyOn(api, "account");

    const page = mount("/");
    await settle();

    expect(page.querySelector("form#login-form")).toBeNull();
    expect(page.textContent).toContain("spring-open");
    expect(account).not.toHaveBeenCalled();
  });

  it("keeps the gate on every other route", async () => {
    lists({});
    for (const at of ["/organizer", "/admin", "/profile"]) {
      const page = mount(at);
      await settle();
      expect(page.querySelector("form#login-form"), at).not.toBeNull();
      host?.remove();
    }
  });

  it("shows not-found rather than Login for an address that names no screen", async () => {
    lists({});
    const page = mount("/nonsense");
    await settle();
    expect(page.querySelector("form#login-form")).toBeNull();
    expect(page.textContent).toContain(i18n.t("notFound.title"));
  });
});

describe("the shell with no account", () => {
  it("offers sign-in where a name would stand, and no account menu", async () => {
    lists({});
    const page = mount("/");
    await settle();

    expect(page.querySelector(".signin-block")?.textContent).toBe(i18n.t("menu.signIn"));
    expect(page.querySelector(".identity-block")).toBeNull();
    expect(page.querySelector(".account-menu")).toBeNull();
  });

  it("names the application at the left and the page in the middle", async () => {
    lists({});
    const page = mount("/");
    await settle();

    const tracks = [...page.querySelectorAll(".topbar > *")].map((el) => el.className);
    expect(tracks).toEqual(["topbar-side", "topbar-title", "topbar-side topbar-side-end"]);
    expect(page.querySelector(".logo")?.textContent).toBe("HEMA Squire");
    expect(page.querySelector(".topbar-title")?.textContent).toBe(i18n.t("app.listTitle"));
  });

  it("pins the language to the default, whatever an ended session left behind", async () => {
    await i18n.changeLanguage("cs");
    lists({});
    const page = mount("/");
    await settle();

    expect(i18n.language).toBe("en");
    expect(page.querySelector(".topbar-title")?.textContent).toBe(i18n.t("app.listTitle"));
  });

  it("offers three tabs, Mine not among them", async () => {
    lists({});
    const page = mount("/");
    await settle();

    expect(tabNames(page)).toEqual([
      i18n.t("home.tabs.announced"),
      i18n.t("home.tabs.open"),
      i18n.t("home.tabs.past"),
    ]);
  });

  it("names the town on a card and nothing more of where it is", async () => {
    // the card is itself a link, so a venue link inside it has nowhere to go;
    // the address is read on the tournament's own page (spec `fencer-home`)
    lists({ upcoming: [tournament("open-one", { city: "Brno" })] });
    const page = mount("/?tab=open");
    await settle();

    const when = page.querySelector(".home-card-when");
    expect(when?.textContent).toContain("Brno");
    expect(when?.querySelector("a")).toBeNull();
  });

  it("gates ?tab=mine at its own URL", async () => {
    lists({});
    const page = mount("/?tab=mine");
    await settle();
    expect(page.querySelector("form#login-form")).not.toBeNull();
  });

  it("lets that gate be declined, landing on a tab a visitor may read", async () => {
    // Mine has no public page behind it — it is the URL — so declining goes
    // to the list's default tab rather than leaving the screen standing
    lists({ upcoming: [tournament("open-one")] });
    const page = mount("/?tab=mine");
    await settle();

    await act(async () => {
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    });
    await settle();

    expect(page.querySelector("form#login-form")).toBeNull();
    expect(page.textContent).toContain("open-one");
  });
});

describe("an account's own language", () => {
  it("titles the bar in the account's language, without a reload", async () => {
    setToken("t");
    vi.spyOn(api, "account").mockResolvedValue({ ...ACCOUNT, language: "cs" } as Account);
    lists({ mine: [] });

    const page = mount("/");
    await settle();

    expect(i18n.language).toBe("cs");
    expect(page.querySelector(".topbar-title")?.textContent).toBe("Šermířské turnaje a akce");
    // the application's own name is not a translated string
    expect(page.querySelector(".logo")?.textContent).toBe("HEMA Squire");
  });
});

describe("the tabs live in the main field", () => {
  it("stands above the list and not in the bar", async () => {
    lists({});
    const page = mount("/");
    await settle();

    expect(page.querySelector(".topbar .stage-control")).toBeNull();
    expect(page.querySelector(".home-workspace .home-tabs")).not.toBeNull();
  });
});

describe("the default tab follows what there is to show", () => {
  it("opens on Mine when the account has entries there", async () => {
    setToken("t");
    vi.spyOn(api, "account").mockResolvedValue(ACCOUNT);
    lists({ upcoming: [tournament("open-one")], mine: [tournament("mine-one")] });

    const page = mount("/");
    await settle();

    expect(activeTab(page)).toBe(i18n.t("home.tabs.mine"));
    expect(page.textContent).toContain("mine-one");
  });

  it("opens on Open when the account has nothing of its own", async () => {
    setToken("t");
    vi.spyOn(api, "account").mockResolvedValue(ACCOUNT);
    lists({ upcoming: [tournament("open-one")], mine: [] });

    const page = mount("/");
    await settle();

    expect(activeTab(page)).toBe(i18n.t("home.tabs.open"));
  });

  it("falls back to Announced when nothing is open", async () => {
    setToken("t");
    vi.spyOn(api, "account").mockResolvedValue(ACCOUNT);
    lists({
      upcoming: [tournament("soon", { registration_status: "opens_on" })],
      mine: [],
    });

    const page = mount("/");
    await settle();

    expect(activeTab(page)).toBe(i18n.t("home.tabs.announced"));
  });

  it("starts an anonymous visitor at Open", async () => {
    lists({ upcoming: [tournament("open-one")] });
    const page = mount("/");
    await settle();
    expect(activeTab(page)).toBe(i18n.t("home.tabs.open"));
  });

  it("gives an anonymous visitor Announced when nothing is open", async () => {
    lists({ upcoming: [tournament("soon", { registration_status: "closed" })] });
    const page = mount("/");
    await settle();
    expect(activeTab(page)).toBe(i18n.t("home.tabs.announced"));
  });

  it("does not override a tab named in the URL", async () => {
    setToken("t");
    vi.spyOn(api, "account").mockResolvedValue(ACCOUNT);
    lists({
      upcoming: [tournament("soon", { registration_status: "opens_on" })],
      mine: [tournament("mine-one")],
    });

    const page = mount("/?tab=announced");
    await settle();

    expect(activeTab(page)).toBe(i18n.t("home.tabs.announced"));
  });

  it("falls back to the default for an unrecognised tab value", async () => {
    lists({ upcoming: [tournament("open-one")] });
    const page = mount("/?tab=archive");
    await settle();
    expect(activeTab(page)).toBe(i18n.t("home.tabs.open"));
  });

  it("shows the loading treatment rather than a tab chosen too early", async () => {
    setToken("t");
    vi.spyOn(api, "account").mockResolvedValue(ACCOUNT);
    vi.spyOn(api, "openTournaments").mockReturnValue(new Promise(() => {}));
    vi.spyOn(api, "heldTournaments").mockResolvedValue([]);
    vi.spyOn(api, "myTournaments").mockResolvedValue([]);

    const page = mount("/");
    await settle();

    expect(page.textContent).toContain(i18n.t("common.loading"));
    expect(activeTab(page)).toBe("");
  });
});

describe("managing a tournament from its card", () => {
  it("offers the control only where the account may manage", async () => {
    setToken("t");
    vi.spyOn(api, "account").mockResolvedValue(ACCOUNT);
    lists({
      upcoming: [
        tournament("ours", { organized: true }),
        tournament("theirs", { organized: false }),
      ],
      mine: [],
    });

    const page = mount("/?tab=open");
    await settle();

    const manage = [...page.querySelectorAll(".home-card-manage")];
    expect(manage).toHaveLength(1);
    expect(manage[0]?.getAttribute("href")).toBe("/organizer/ours/console");
    expect(manage[0]?.textContent).toBe(i18n.t("home.manage"));
  });

  it("offers it on a held tournament too", async () => {
    setToken("t");
    vi.spyOn(api, "account").mockResolvedValue(ACCOUNT);
    lists({ held: [tournament("last-month", { organized: true })], mine: [] });

    const page = mount("/?tab=past");
    await settle();

    expect(page.querySelector(".home-card-manage")).not.toBeNull();
  });

  it("offers it to nobody without an account", async () => {
    lists({ upcoming: [tournament("open-one")] });
    const page = mount("/");
    await settle();
    expect(page.querySelector(".home-card-manage")).toBeNull();
  });

  it("leaves the card itself a link to the tournament, with nothing nested in it", async () => {
    setToken("t");
    vi.spyOn(api, "account").mockResolvedValue(ACCOUNT);
    lists({ upcoming: [tournament("ours", { organized: true })], mine: [] });

    const page = mount("/?tab=open");
    await settle();

    const body = page.querySelector(".home-card-body");
    expect(body?.getAttribute("href")).toBe("/t/ours");
    expect(body?.querySelector("a, button")).toBeNull();
  });
});

describe("what the account menu offers", () => {
  async function menu(role: Account["role"], organized = 0) {
    setToken("t");
    vi.spyOn(api, "account").mockResolvedValue({
      ...ACCOUNT,
      role,
      organized_count: organized,
    } as Account);
    lists({ mine: [] });
    const page = mount("/");
    await settle();
    const trigger = page.querySelector<HTMLButtonElement>(".account-menu-trigger");
    await act(async () => {
      trigger?.click();
    });
    return page;
  }

  it("offers creating a tournament to an organizer", async () => {
    const page = await menu("organizer");
    expect(page.textContent).toContain(i18n.t("menu.createTournament"));
  });

  it("does not offer creating one to a plain fencer", async () => {
    const page = await menu("fencer");
    expect(page.textContent).not.toContain(i18n.t("menu.createTournament"));
  });

  it("names the picker for the tournaments the account holds", async () => {
    const page = await menu("organizer", 2);
    const entry = [...page.querySelectorAll("a")].find(
      (a) => a.textContent === i18n.t("menu.myTournaments"),
    );
    expect(entry?.getAttribute("href")).toBe("/organizer");
  });

  it("hides that entry where the account holds none", async () => {
    const page = await menu("organizer", 0);
    expect(page.textContent).not.toContain(i18n.t("menu.myTournaments"));
  });

  it("offers no way back to the fencer's screens, the logo being that", async () => {
    const page = await menu("organizer", 1);
    const home = [...page.querySelectorAll(".account-menu-dropdown a")].filter(
      (a) => a.getAttribute("href") === "/",
    );
    expect(home).toHaveLength(0);
    expect(page.querySelector(".logo-button")?.getAttribute("href")).toBe("/");
  });
});

describe("the picker keeps what the public list cannot show", () => {
  it("lists a draft, which appears in no home tab", async () => {
    setToken("t");
    vi.spyOn(api, "account").mockResolvedValue({ ...ACCOUNT, role: "organizer" } as Account);
    vi.spyOn(api, "tournaments").mockResolvedValue([
      {
        slug: "draft-2026",
        display_name: "Draft 2026",
        date: "2026-11-01",
        published_at: null,
      } as never,
    ]);
    lists({ mine: [] });

    const picker = mount("/organizer");
    await settle();
    expect(picker.textContent).toContain("Draft 2026");
    expect(picker.textContent).toContain(i18n.t("picker.draft"));
    // its own create button is still there
    expect(picker.textContent).toContain(i18n.t("picker.newTournament"));
    host?.remove();

    for (const tab of ["announced", "open", "past", "mine"]) {
      const page = mount(`/?tab=${tab}`);
      await settle();
      expect(page.textContent, tab).not.toContain("Draft 2026");
      host?.remove();
    }
  });
});

describe("every tab names itself in the URL", () => {
  it("does not send Open to the bare URL, where the default would win", async () => {
    setToken("t");
    vi.spyOn(api, "account").mockResolvedValue(ACCOUNT);
    lists({ upcoming: [tournament("open-one")], mine: [tournament("mine-one")] });

    const page = mount("/");
    await settle();
    // the account's own list is where the default put them
    expect(activeTab(page)).toBe(i18n.t("home.tabs.mine"));

    const open = [...page.querySelectorAll<HTMLAnchorElement>(".home-tabs a")].find(
      (a) => label(a) === i18n.t("home.tabs.open"),
    );
    expect(open?.getAttribute("href")).toBe("/?tab=open");

    await act(async () => {
      open?.click();
    });
    await settle();

    expect(activeTab(page)).toBe(i18n.t("home.tabs.open"));
    expect(page.textContent).toContain("open-one");
  });
});
