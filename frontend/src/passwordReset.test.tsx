// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { type Account, ApiError, api, getToken, setToken } from "./api";
import i18n from "./i18n";
import Login from "./Login";
import AccountSection from "./profile/AccountSection";
import { mount, mounted, settle } from "./publicDetailFixture";
import { resetPassword } from "./routes";

// Forgot password on the sign-in screen, the reset link's screen, and the
// password section of the profile (change `password-reset`).

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

beforeEach(async () => {
  vi.restoreAllMocks();
  setToken(null);
  await i18n.changeLanguage("en");
});

afterEach(() => {
  mounted.host?.remove();
  mounted.host = null;
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

async function openForgot() {
  const page = render(<Login onLogin={() => {}} />);
  type(page.querySelector("form#login-form"), "email", "eva@example.com");
  await click(page.querySelector("button.login-forgot"));
  return page;
}

describe("forgot password", () => {
  it("carries the address typed into sign-in", async () => {
    const page = await openForgot();
    const form = page.querySelector("form#forgot-password");
    expect(form).not.toBeNull();
    expect(form?.querySelector<HTMLInputElement>('input[name="email"]')?.value).toBe(
      "eva@example.com",
    );
  });

  it("states where the link went", async () => {
    const request = vi
      .spyOn(api, "requestPasswordReset")
      .mockResolvedValue({ email: "eva@example.com" });
    const page = await openForgot();
    await submit(page.querySelector("form#forgot-password"));
    expect(request).toHaveBeenCalledWith("eva@example.com");
    expect(page.querySelector("#forgot-password-sent")?.textContent).toContain(
      "We sent a link to eva@example.com",
    );
  });

  it("says plainly that no account uses the address, and offers one", async () => {
    vi.spyOn(api, "requestPasswordReset").mockRejectedValue(new ApiError(404, "no_account"));
    const page = await openForgot();
    await submit(page.querySelector("form#forgot-password"));
    const notice = page.querySelector(".forgot-no-account");
    expect(notice?.textContent).toContain("No account uses this address.");
    await click(notice?.querySelector("button"));
    expect(page.querySelector("form#signup-form")).not.toBeNull();
  });
});

describe("the reset link", () => {
  it("states a dead link without offering a form, and offers a new request", async () => {
    vi.spyOn(api, "openTournaments").mockResolvedValue([]);
    vi.spyOn(api, "inspectPasswordReset").mockRejectedValue(new ApiError(410, "reset_invalid"));
    const page = mount(resetPassword("used"));
    await settle();
    expect(page.querySelector("form#reset-password")).toBeNull();
    expect(page.querySelector(".reset-invalid")?.textContent).toContain(i18n.t("reset.invalid"));
    await click(page.querySelector(".reset-invalid button"));
    expect(page.querySelector("form#forgot-password")).not.toBeNull();
  });

  it("names the account inside the form and signs in on saving", async () => {
    vi.spyOn(api, "openTournaments").mockResolvedValue([]);
    vi.spyOn(api, "heldTournaments").mockResolvedValue([]);
    vi.spyOn(api, "myTournaments").mockResolvedValue([]);
    vi.spyOn(api, "account").mockResolvedValue({ display_name: "Eva", language: "en" } as never);
    vi.spyOn(api, "inspectPasswordReset").mockResolvedValue({ email: "eva@example.com" });
    const confirm = vi.spyOn(api, "confirmPasswordReset").mockResolvedValue({ token: "fresh" });
    const page = mount(resetPassword("live"));
    await settle();

    const form = page.querySelector("form#reset-password");
    const username = form?.querySelector<HTMLInputElement>('input[autocomplete="username"]');
    expect(username?.value).toBe("eva@example.com");
    expect(username?.readOnly).toBe(true);
    expect(form?.querySelector('input[name="new-password"]')?.getAttribute("autocomplete")).toBe(
      "new-password",
    );

    type(form, "new-password", "new-horse-battery");
    await submit(form);
    await settle();
    expect(confirm).toHaveBeenCalledWith("live", "new-horse-battery");
    expect(getToken()).toBe("fresh");
    expect(page.querySelector("form#reset-password")).toBeNull();
  });

  it("refuses too short a password in place without spending the link", async () => {
    vi.spyOn(api, "openTournaments").mockResolvedValue([]);
    vi.spyOn(api, "inspectPasswordReset").mockResolvedValue({ email: "eva@example.com" });
    const confirm = vi.spyOn(api, "confirmPasswordReset");
    const page = mount(resetPassword("live"));
    await settle();
    const form = page.querySelector("form#reset-password");
    type(form, "new-password", "short");
    await submit(form);
    expect(confirm).not.toHaveBeenCalled();
    expect(form?.querySelector(".field-error")).not.toBeNull();
  });
});

describe("changing the password from the profile", () => {
  const ACCOUNT = { email: "eva@example.com", display_name: "Eva", language: "en" } as Account;

  async function openDialog() {
    const page = render(<AccountSection account={ACCOUNT} onUpdated={() => {}} />);
    expect(page.querySelector('input[type="password"]')).toBeNull();
    await click(page.querySelector("button.change-password"));
    return { page, form: document.querySelector("dialog form#change-password") };
  }

  it("renders no password field until the link is followed", async () => {
    const { form } = await openDialog();
    expect(form?.querySelector('input[name="current-password"]')).not.toBeNull();
  });

  it("refuses a wrong current password in place and keeps the session", async () => {
    setToken("current");
    vi.spyOn(api, "changePassword").mockRejectedValue(new ApiError(403, "wrong_password"));
    const { form } = await openDialog();
    type(form, "current-password", "wrong-horse");
    type(form, "new-password", "new-horse-battery");
    await submit(form);
    expect(form?.textContent).toContain(i18n.t("profile.password.wrong"));
    expect(getToken()).toBe("current");
  });

  it("replaces this browser's session with the one the change returns", async () => {
    setToken("current");
    vi.spyOn(api, "changePassword").mockResolvedValue({ token: "fresh" });
    const { page, form } = await openDialog();
    type(form, "current-password", "correct-horse");
    type(form, "new-password", "new-horse-battery");
    await submit(form);
    expect(getToken()).toBe("fresh");
    expect(document.querySelector("dialog form#change-password")).toBeNull();
    expect(page.querySelector(".password-changed")?.textContent).toBe(
      i18n.t("profile.password.changed"),
    );
  });
});
