// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { type Account, ApiError, api, getToken, setToken } from "./api";
import i18n from "./i18n";
import AccountSection from "./profile/AccountSection";
import { mount, mounted, settle } from "./publicDetailFixture";
import { confirmEmail } from "./routes";

// The address change (spec profile-page, Address change): asked for from the
// Profile page with the current password, made by the link mailed to the new
// address.

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

beforeEach(async () => {
  vi.restoreAllMocks();
  setToken(null);
  await i18n.changeLanguage("en");
});

afterEach(() => {
  mounted.host?.remove();
  mounted.host = null;
  document.body.innerHTML = "";
  setToken(null);
});

function render(node: React.ReactNode) {
  const host = document.createElement("div");
  mounted.host = host;
  document.body.append(host);
  const root = createRoot(host);
  act(() => root.render(node));
  return host;
}

function click(element: Element | null | undefined) {
  return act(async () => {
    element?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  });
}

function type(form: Element | null, name: string, value: string) {
  const input = form?.querySelector<HTMLInputElement>(`input[name="${name}"]`);
  if (!input) throw new Error(`no ${name} field`);
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
  act(() => {
    setter?.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

function submit(form: Element | null) {
  return act(async () => {
    form?.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
  });
}

describe("asking for an address change", () => {
  const ACCOUNT = { email: "eva@example.com", display_name: "Eva", language: "en" } as Account;

  async function openDialog() {
    const page = render(<AccountSection account={ACCOUNT} onUpdated={() => {}} />);
    const changeLink = [...page.querySelectorAll("button.link-button")].find(
      (button) => button.textContent === i18n.t("profile.email.open"),
    );
    await click(changeLink);
    return { page, form: document.querySelector("dialog form#change-email") };
  }

  it("shows the address read-only and never sends it as an ordinary edit", async () => {
    const update = vi.spyOn(api, "updateAccount").mockResolvedValue(ACCOUNT);
    const page = render(<AccountSection account={ACCOUNT} onUpdated={() => {}} />);
    const address = page.querySelector<HTMLInputElement>("#account-email");
    expect(address?.value).toBe("eva@example.com");
    expect(address?.readOnly).toBe(true);

    const name = page.querySelectorAll<HTMLInputElement>(".param-field input")[1];
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
    act(() => {
      setter?.call(name, "Eva N");
      name?.dispatchEvent(new Event("input", { bubbles: true }));
    });
    await click(page.querySelector("button.param-save"));
    expect(update).toHaveBeenCalledOnce();
    expect(update.mock.calls[0]?.[0]).not.toHaveProperty("email");
  });

  it("refuses a wrong current password in place", async () => {
    setToken("current");
    vi.spyOn(api, "requestEmailChange").mockRejectedValue(new ApiError(403, "wrong_password"));
    const { form } = await openDialog();
    type(form, "new-email", "new@example.com");
    type(form, "current-password", "wrong-horse");
    await submit(form);
    expect(form?.textContent).toContain(i18n.t("profile.email.wrong"));
    expect(getToken()).toBe("current");
  });

  it("says where the link went and that nothing has changed yet", async () => {
    const request = vi
      .spyOn(api, "requestEmailChange")
      .mockResolvedValue({ email: "new@example.com" });
    const { form } = await openDialog();
    type(form, "new-email", " new@example.com ");
    type(form, "current-password", "correct-horse");
    await submit(form);
    expect(request).toHaveBeenCalledWith("correct-horse", "new@example.com");
    expect(document.querySelector(".email-change-sent")?.textContent).toBe(
      i18n.t("profile.email.sent", { email: "new@example.com" }),
    );
  });
});

describe("the address-change link", () => {
  it("changes nothing until confirmed, then signs this browser in", async () => {
    vi.spyOn(api, "openTournaments").mockResolvedValue([]);
    vi.spyOn(api, "inspectEmailChange").mockResolvedValue({ email: "new@example.com" });
    const confirm = vi.spyOn(api, "confirmEmailChange").mockResolvedValue({ token: "fresh" });
    vi.spyOn(api, "account").mockResolvedValue({
      email: "new@example.com",
      display_name: "Eva",
      language: "en",
    } as never);
    const page = mount(confirmEmail("live"));
    await settle();

    expect(confirm).not.toHaveBeenCalled();
    const card = page.querySelector(".email-confirm");
    expect(card?.textContent).toContain("new@example.com");
    await click(card?.querySelector("button"));
    await settle();
    expect(confirm).toHaveBeenCalledWith("live");
    expect(getToken()).toBe("fresh");
    expect(page.querySelector(".email-confirm")).toBeNull();
  });

  it("states a dead link", async () => {
    vi.spyOn(api, "openTournaments").mockResolvedValue([]);
    vi.spyOn(api, "inspectEmailChange").mockRejectedValue(
      new ApiError(410, "email_change_invalid"),
    );
    const page = mount(confirmEmail("used"));
    await settle();
    expect(page.querySelector(".email-confirm-dead")?.textContent).toContain(
      i18n.t("confirmEmail.invalid"),
    );
  });

  it("states an address taken meanwhile", async () => {
    vi.spyOn(api, "openTournaments").mockResolvedValue([]);
    vi.spyOn(api, "inspectEmailChange").mockResolvedValue({ email: "new@example.com" });
    vi.spyOn(api, "confirmEmailChange").mockRejectedValue(new ApiError(409, "email_taken"));
    const page = mount(confirmEmail("live"));
    await settle();
    await click(page.querySelector(".email-confirm button"));
    await settle();
    expect(page.querySelector(".email-confirm-dead")?.textContent).toContain(
      i18n.t("confirmEmail.taken"),
    );
    expect(getToken()).toBeNull();
  });
});
