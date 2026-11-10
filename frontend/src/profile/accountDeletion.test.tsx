// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { type Account, ApiError, api, type DeletionImpact } from "../api";
import i18n from "../i18n";
import AccountDeletion from "./AccountDeletion";

// Asking for the account to be deleted from the Profile page (spec
// profile-page, The Profile page offers account deletion; spec
// account-deletion): the impact before the password, a refusal that asks for
// nothing, and the pending date with a way back.

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let host: HTMLElement | null = null;

const ACCOUNT = {
  id: 1,
  email: "me@example.com",
  display_name: "Me",
  language: "en",
  deletion_effective_at: null,
} as unknown as Account;

const IMPACT: DeletionImpact = {
  cancelled: [
    {
      tournament: "Spring Open",
      tournament_date: "2099-05-01",
      variable_symbol: 991001,
      credited: [{ amount_cents: 80000, currency: "CZK" }],
    },
  ],
  held_rosters: 2,
  blockers: [],
};

async function settle() {
  await act(async () => {
    for (let i = 0; i < 6; i++) await Promise.resolve();
  });
}

async function render(account: Account, onUpdated = vi.fn()) {
  host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  act(() => root.render(<AccountDeletion account={account} onUpdated={onUpdated} />));
  await settle();
  return host;
}

function button(page: HTMLElement, label: string): HTMLButtonElement | undefined {
  return [...page.querySelectorAll<HTMLButtonElement>("button")].find(
    (b) => b.textContent === label,
  );
}

async function click(element: Element | undefined) {
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

beforeEach(async () => {
  vi.restoreAllMocks();
  await i18n.changeLanguage("en");
});

afterEach(() => {
  host?.remove();
  host = null;
});

describe("the deletion dialog", () => {
  it("states the impact, and a wrong password is refused in place", async () => {
    vi.spyOn(api, "deletionImpact").mockResolvedValue(IMPACT);
    vi.spyOn(api, "requestDeletion").mockRejectedValue(new ApiError(403, "wrong_password"));
    const page = await render(ACCOUNT);
    await click(button(page, i18n.t("profile.deletion.open")));

    const text = page.textContent ?? "";
    expect(text).toContain("Spring Open");
    expect(text).toContain(i18n.t("profile.deletion.heldRosters", { count: 2 }));
    expect(text).toContain(i18n.t("profile.deletion.outOfReach"));

    const password = page.querySelector<HTMLInputElement>('input[type="password"]');
    if (password === null) throw new Error("no password field");
    type(password, "nope");
    const form = page.querySelector("form");
    act(() => form?.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
    await settle();

    expect(page.querySelector(".login-error")?.textContent).toBe(i18n.t("profile.password.wrong"));
  });

  it("names what blocks it and asks for no password", async () => {
    vi.spyOn(api, "deletionImpact").mockResolvedValue({
      ...IMPACT,
      blockers: [{ kind: "owner", tournaments: ["Spring Open"] }],
    });
    const page = await render(ACCOUNT);
    await click(button(page, i18n.t("profile.deletion.open")));

    expect(page.textContent).toContain(
      i18n.t("profile.deletion.blocker.owner", { tournaments: "Spring Open" }),
    );
    expect(page.querySelector('input[type="password"]')).toBeNull();
    expect(button(page, i18n.t("profile.deletion.submit"))).toBeUndefined();
  });
});

describe("a pending deletion", () => {
  it("states its date and can be withdrawn", async () => {
    const withdrawn = { ...ACCOUNT, deletion_effective_at: null } as Account;
    const withdraw = vi.spyOn(api, "withdrawDeletion").mockResolvedValue(withdrawn);
    const onUpdated = vi.fn();
    const page = await render(
      { ...ACCOUNT, deletion_effective_at: "2099-05-08T10:00:00Z" } as Account,
      onUpdated,
    );

    expect(page.textContent).toContain(new Date("2099-05-08T10:00:00Z").toLocaleDateString("en"));
    await click(button(page, i18n.t("profile.deletion.withdraw")));

    expect(withdraw).toHaveBeenCalledOnce();
    expect(onUpdated).toHaveBeenCalledWith(withdrawn);
  });
});
