// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import {
  type Account,
  type AdminAccount,
  type AdminTournament,
  ApiError,
  api,
  setToken,
} from "../api";
import i18n from "../i18n";

// The admin panel's tabs, search, sorting and tournament delete (spec
// user-roles, Admin panel; spec tournament-admin, Tournament deletion and
// cancellation).

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let host: HTMLElement | null = null;

function person(id: number, name: string, extra: Partial<AdminAccount> = {}): AdminAccount {
  return {
    id,
    email: `${id}@example.com`,
    display_name: name,
    role: "fencer",
    hr_id: null,
    created_at: `2026-0${id}-01T10:00:00Z`,
    is_deployment_owner: false,
    has_pending_plea: false,
    hr_shared: false,
    deleted: false,
    ...extra,
  };
}

function tournament(slug: string, count: number): AdminTournament {
  return {
    slug,
    display_name: slug.toUpperCase(),
    date: "2026-12-05",
    state: "published",
    owner: null,
    registration_count: count,
    credited: count > 0 ? [{ currency: "CZK", amount_cents: 380000 }] : [],
  };
}

async function settle() {
  await act(async () => {
    for (let i = 0; i < 6; i++) await Promise.resolve();
  });
}

async function mount() {
  host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  act(() =>
    root.render(
      <MemoryRouter initialEntries={["/admin"]}>
        <App />
      </MemoryRouter>,
    ),
  );
  await settle();
  return host;
}

function tab(page: HTMLElement, name: string): HTMLButtonElement {
  const found = [...page.querySelectorAll<HTMLButtonElement>('[role="tab"]')].find((button) =>
    button.textContent?.startsWith(name),
  );
  if (!found) throw new Error(`no tab ${name}`);
  return found;
}

async function click(element: Element | null | undefined) {
  act(() => (element as HTMLElement).click());
  await settle();
}

function type(input: HTMLInputElement, value: string) {
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
  act(() => {
    setter?.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

function names(page: HTMLElement): string[] {
  return [...page.querySelectorAll("tbody tr")].map(
    (row) => row.querySelectorAll("td")[1]?.textContent ?? "",
  );
}

beforeEach(async () => {
  vi.restoreAllMocks();
  setToken("t");
  vi.spyOn(api, "account").mockResolvedValue({ id: 99, role: "admin" } as Account);
  vi.spyOn(api, "adminPleas").mockResolvedValue([]);
  vi.spyOn(api, "adminDeletions").mockResolvedValue([]);
  vi.spyOn(api, "adminAccounts").mockResolvedValue([]);
  vi.spyOn(api, "adminTournaments").mockResolvedValue([]);
  vi.spyOn(api, "tournaments").mockResolvedValue([]);
  await i18n.changeLanguage("cs");
});

afterEach(() => {
  host?.remove();
  host = null;
  setToken(null);
});

describe("the tasks tab", () => {
  it("opens first and counts pleas and shared HR IDs", async () => {
    vi.spyOn(api, "adminPleas").mockResolvedValue([
      {
        id: 1,
        fencer_id: 1,
        email: "a@x.cz",
        display_name: "A",
        message: null,
        created_at: "2026-10-01T00:00:00Z",
      },
    ]);
    vi.spyOn(api, "adminAccounts").mockResolvedValue([
      person(1, "A", { hr_id: 7, hr_shared: true }),
      person(2, "B", { hr_id: 7, hr_shared: true }),
    ]);
    const page = await mount();
    const tasks = tab(page, "Úkoly");
    expect(tasks.getAttribute("aria-selected")).toBe("true");
    expect(tasks.querySelector(".tab-count")?.textContent).toBe("2");
    expect(page.querySelector(".admin-shared-holders")?.children).toHaveLength(2);
  });

  it("drops a shared HR ID once unbinding leaves a single holder", async () => {
    const accounts = vi
      .spyOn(api, "adminAccounts")
      .mockResolvedValue([
        person(1, "A", { hr_id: 7, hr_shared: true }),
        person(2, "B", { hr_id: 7, hr_shared: true }),
      ]);
    const unbind = vi.spyOn(api, "adminHrUnbind").mockResolvedValue(person(2, "B"));
    const page = await mount();
    accounts.mockResolvedValue([person(1, "A", { hr_id: 7 }), person(2, "B")]);
    await click(page.querySelector(".admin-shared-holders li:last-child button"));
    expect(unbind).toHaveBeenCalledWith(2);
    expect(page.querySelector(".admin-shared-holders")).toBeNull();
    expect(tab(page, "Úkoly").querySelector(".tab-count")?.textContent).toBe("0");
  });
});

describe("the people tab", () => {
  it("finds a name typed without diacritics", async () => {
    vi.spyOn(api, "adminAccounts").mockResolvedValue([person(1, "Jan Nováček"), person(2, "Eva")]);
    const page = await mount();
    await click(tab(page, "Lidé"));
    type(page.querySelector<HTMLInputElement>(".admin-search") as HTMLInputElement, "novacek");
    expect(names(page)).toEqual(["Jan Nováček"]);
  });

  it("reverses a sort when its column is chosen again", async () => {
    vi.spyOn(api, "adminAccounts").mockResolvedValue([person(2, "Bára"), person(1, "Adam")]);
    const page = await mount();
    await click(tab(page, "Lidé"));
    const created = () =>
      [...page.querySelectorAll<HTMLButtonElement>(".sort-header")].find(
        (button) => button.textContent === "Vytvořeno",
      );
    await click(created());
    expect(names(page)).toEqual(["Adam", "Bára"]);
    expect(created()?.closest("th")?.getAttribute("aria-sort")).toBe("ascending");
    await click(created());
    expect(names(page)).toEqual(["Bára", "Adam"]);
    expect(created()?.closest("th")?.getAttribute("aria-sort")).toBe("descending");
  });
});

describe("deleting a tournament", () => {
  it("deletes an empty tournament without asking", async () => {
    vi.spyOn(api, "adminTournaments").mockResolvedValue([tournament("empty", 0)]);
    const remove = vi.spyOn(api, "adminDeleteTournament").mockResolvedValue(undefined);
    const page = await mount();
    await click(tab(page, "Akce"));
    await click(page.querySelector('tbody .row-action[title="Smazat akci"]'));
    expect(remove).toHaveBeenCalledWith("empty", false);
    expect(document.querySelector("dialog")).toBeNull();
  });

  it("asks first where registrations exist, stating them and the money", async () => {
    vi.spyOn(api, "adminTournaments").mockResolvedValue([tournament("cup", 12)]);
    const remove = vi.spyOn(api, "adminDeleteTournament").mockResolvedValue(undefined);
    const page = await mount();
    await click(tab(page, "Akce"));
    await click(page.querySelector('tbody .row-action[title="Smazat akci"]'));
    expect(remove).not.toHaveBeenCalled();
    const dialog = document.querySelector("dialog");
    expect(dialog?.textContent).toContain("12 registrací");
    // grouped with a no-break space, as the locale writes it
    expect(dialog?.textContent).toMatch(/3\s800/);
    await click(dialog?.querySelector(".btn-danger"));
    expect(remove).toHaveBeenCalledWith("cup", true);
  });
});

describe("assigning a tournament's owner", () => {
  async function openDialog() {
    vi.spyOn(api, "adminTournaments").mockResolvedValue([tournament("cup", 3)]);
    const page = await mount();
    await click(tab(page, "Akce"));
    await click(page.querySelector('tbody .row-action[title="Přiřadit vlastníka"]'));
    const dialog = document.querySelector("dialog");
    const input = dialog?.querySelector<HTMLInputElement>('input[type="email"]');
    if (!dialog || !input) throw new Error("no assign dialog");
    return { dialog, input };
  }

  it("assigns the named account and closes", async () => {
    const assign = vi.spyOn(api, "assignOwner").mockResolvedValue({} as never);
    const { dialog, input } = await openDialog();
    expect(dialog.textContent).toContain("nemá vlastníka");
    type(input, " new@example.com ");
    await click(dialog.querySelector('button[type="submit"]'));
    expect(assign).toHaveBeenCalledWith("cup", "new@example.com");
    expect(document.querySelector("dialog")).toBeNull();
  });

  it("stays open and says so when no account has the address", async () => {
    vi.spyOn(api, "assignOwner").mockRejectedValue(new ApiError(404, "account_not_found"));
    const { dialog, input } = await openDialog();
    type(input, "nobody@example.com");
    await click(dialog.querySelector('button[type="submit"]'));
    expect(document.querySelector("dialog")?.textContent).toContain(
      "Účet s tímto e-mailem neexistuje.",
    );
  });
});

describe("account deletion in the admin panel", () => {
  it("lists a deletion a blocker holds back among the tasks", async () => {
    vi.spyOn(api, "adminDeletions").mockResolvedValue([
      {
        fencer_id: 5,
        display_name: "Held Back",
        email: "held@example.com",
        requested_at: "2026-10-01T10:00:00Z",
        blockers: [{ kind: "owner", tournaments: ["Cup"] }],
      },
    ]);
    const page = await mount();

    expect(tab(page, i18n.t("admin.tabs.tasks")).textContent).toContain("1");
    expect(page.textContent).toContain("Held Back");
    expect(page.textContent).toContain("Cup");
  });

  it("marks a deleted record and erases its identity after asking", async () => {
    vi.spyOn(api, "adminAccounts").mockResolvedValue([
      person(5, "Jana Held", { email: null, deleted: true }),
      person(6, "Live One"),
    ]);
    const erase = vi.spyOn(api, "adminEraseIdentity").mockResolvedValue(person(5, "x"));
    const page = await mount();
    await click(tab(page, i18n.t("admin.tabs.people")));

    expect(page.textContent).toContain(i18n.t("admin.accounts.deleted"));
    const buttons = [...page.querySelectorAll("button")].filter(
      (button) => button.textContent === i18n.t("admin.erase.open"),
    );
    expect(buttons).toHaveLength(1);
    await click(buttons[0]);
    const confirm = [...page.querySelectorAll("dialog button")].find(
      (button) => button.textContent === i18n.t("admin.erase.confirm"),
    );
    await click(confirm);

    expect(erase).toHaveBeenCalledWith(5);
  });
});
