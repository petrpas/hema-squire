// @vitest-environment jsdom
import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api, getToken, type RegistrationDetail, setToken } from "./api";
import i18n from "./i18n";
import { detailApi, mount, mounted, registerTab, settle } from "./publicDetailFixture";

// Registering without an account: the guest variant of the account form, the
// identity held by the page until the checklist is submitted, the manage link
// standing in for an account, and the verification link finishing a signup
// (change `guest-registration`).

const REGISTRATION = {
  state: "reserved",
  vs: 2601001,
  total_amount: 800,
  outstanding_amount: 800,
  outstanding_currency: "CZK",
  total_eur: null,
  expires_at: null,
  registered_at: "2026-10-01T10:00:00Z",
  paid_at: null,
  weapon_rentals: [],
  afterparty: false,
  aftersparring: false,
  accommodation: null,
  notes: null,
  refundable: null,
  refund_state: "not_applicable",
  extras: [],
  entries: [{ slug: "LS", is_substitute: false, queue_position: null, conditional: false }],
  condition_waits_for: [],
  teams: [],
  discounts: [],
} as unknown as RegistrationDetail;

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

function click(element: Element | null | undefined) {
  return act(async () => {
    element?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  });
}

function type(form: Element | null, name: string, value: string) {
  const input = form?.querySelector<HTMLInputElement>(`input[name="${name}"]`);
  if (!input) throw new Error(`no ${name} field`);
  // React tracks the value it last rendered; setting it through the native
  // setter is what makes the change event register as a change
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
  setter?.call(input, value);
  input.dispatchEvent(new Event("input", { bubbles: true }));
}

async function openSignIn() {
  detailApi();
  const page = mount("/t/spring-open");
  await settle();
  await click(registerTab(page));
  return page;
}

function fieldNames(form: Element | null): string[] {
  return [...(form?.querySelectorAll("input, select") ?? [])].map(
    (field) => field.getAttribute("name") ?? field.tagName.toLowerCase(),
  );
}

describe("two entries, one form", () => {
  it("differ only in heading and the password field", async () => {
    const page = await openSignIn();

    await click(page.querySelector("form#login-form .login-create"));
    const account = page.querySelector("form#signup-form");
    const accountFields = fieldNames(account);
    const accountHeading = account?.querySelector(".login-subtitle")?.textContent;
    // back to sign-in by the form's own foot control
    const back = [...(account?.querySelectorAll("button") ?? [])].find(
      (button) => button.textContent === i18n.t("signup.backToLogin"),
    );
    await click(back);

    await click(page.querySelector("form#login-form .login-guest"));
    const guest = page.querySelector("form#guest-form");
    expect(guest).not.toBeNull();
    expect(fieldNames(guest)).toEqual(accountFields.filter((name) => name !== "password"));
    expect(guest?.querySelector('input[type="password"]')).toBeNull();
    expect(guest?.querySelector(".login-subtitle")?.textContent).not.toBe(accountHeading);
    // an address, not an account identifier: no credential is offered for saving
    expect(guest?.querySelector('input[name="email"]')?.getAttribute("autocomplete")).toBe("email");
  });

  it("is not offered on a URL that needs an account", async () => {
    detailApi();
    const page = mount("/?tab=mine");
    await settle();
    expect(page.querySelector("form#login-form")).not.toBeNull();
    expect(page.querySelector(".login-guest")).toBeNull();
  });
});

describe("the guest identity", () => {
  async function completeGuestForm() {
    const page = await openSignIn();
    await click(page.querySelector("form#login-form .login-guest"));
    const form = page.querySelector("form#guest-form");
    await act(async () => {
      type(form, "email", "jana@example.com");
      type(form, "display_name", "Jana Malá");
    });
    await act(async () => {
      form?.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    });
    await settle();
    return page;
  }

  it("returns to the checklist with nothing posted", async () => {
    const check = vi.spyOn(api, "guestCheck").mockResolvedValue(undefined);
    const register = vi.spyOn(api, "guestRegister");
    const signup = vi.spyOn(api, "signup");

    const page = await completeGuestForm();

    expect(check).toHaveBeenCalledWith("jana@example.com");
    expect(page.querySelector("form#guest-form")).toBeNull();
    expect(page.querySelector(".detail-tabs button.active")?.textContent).toBe(
      i18n.t("detail.tabs.register"),
    );
    const line = page.querySelector(".guest-identity")?.textContent ?? "";
    expect(line).toContain("Jana Malá");
    expect(line).toContain("jana@example.com");
    expect(register).not.toHaveBeenCalled();
    expect(signup).not.toHaveBeenCalled();
  });

  it("is refused early where the address has an account", async () => {
    vi.spyOn(api, "guestCheck").mockRejectedValue(new ApiError(409, "email_has_account"));

    const page = await completeGuestForm();

    const form = page.querySelector("form#guest-form");
    expect(form).not.toBeNull();
    expect(form?.querySelector(".login-error")?.textContent).toContain(
      i18n.t("guest.errors.hasAccount"),
    );
  });

  it("goes to the manage link once submitted", async () => {
    vi.spyOn(api, "guestCheck").mockResolvedValue(undefined);
    const register = vi
      .spyOn(api, "guestRegister")
      .mockResolvedValue({ registration: REGISTRATION, manage_key: "7.secret" });
    const mine = vi.spyOn(api, "myRegistration").mockResolvedValue(REGISTRATION);

    const page = await completeGuestForm();
    const ls = [...page.querySelectorAll(".checklist-row, .checklist label, .checklist button")];
    await click(ls.find((row) => row.textContent?.includes("Longsword")));
    await click(page.querySelector("button.param-save"));
    await settle();

    expect(register).toHaveBeenCalledWith(
      "spring-open",
      expect.objectContaining({
        disciplines: ["LS"],
        guest: expect.objectContaining({ email: "jana@example.com", display_name: "Jana Malá" }),
      }),
    );
    expect(mine).toHaveBeenCalledWith("spring-open", "7.secret");
    expect(page.querySelector(".detail-tabs button.active")?.textContent).toBe(
      i18n.t("detail.tabs.registered"),
    );
  });
});

describe("the manage screen", () => {
  it("shows the registration its key names, with the shell anonymous", async () => {
    detailApi();
    setToken("someone-elses");
    vi.spyOn(api, "account").mockResolvedValue({ display_name: "Signed In" } as never);
    const mine = vi.spyOn(api, "myRegistration").mockResolvedValue(REGISTRATION);

    const page = mount("/t/spring-open/manage#7.secret");
    await settle();

    expect(mine).toHaveBeenCalledWith("spring-open", "7.secret");
    expect(page.querySelector(".detail-tabs button.active")?.textContent).toBe(
      i18n.t("detail.tabs.registered"),
    );
    expect(page.textContent).toContain(i18n.t("cancel.button"));
    expect(page.textContent).not.toContain("Signed In");
  });

  it("opens in the language the guest chose", async () => {
    detailApi();
    vi.spyOn(api, "myRegistration").mockResolvedValue({ ...REGISTRATION, language: "cs" });

    mount("/t/spring-open/manage#7.secret");
    await settle();

    expect(i18n.language).toBe("cs");
  });

  it("states a dead link in place of the registration", async () => {
    detailApi();
    vi.spyOn(api, "myRegistration").mockRejectedValue(new ApiError(404, "manage_key_invalid"));

    const page = mount("/t/spring-open/manage#7.stale");
    await settle();

    expect(page.querySelector(".manage-link-dead")?.textContent).toBe(i18n.t("guest.linkDead"));
    expect(page.querySelector(".detail-header h1")?.textContent).toBe("Spring Open");
    expect(page.querySelector(".login-error")).toBeNull();
  });
});

describe("the verification link", () => {
  it("signs in and lands where the signup was started", async () => {
    detailApi();
    vi.spyOn(api, "account").mockResolvedValue({ display_name: "F", language: "en" } as never);
    vi.spyOn(api, "myRegistration").mockRejectedValue(new ApiError(404, "not_registered"));
    const verify = vi
      .spyOn(api, "verify")
      .mockResolvedValue({ token: "fresh", return_to: "/t/spring-open#register" });

    const page = mount("/verify#the-key");
    await settle();
    await settle();

    expect(verify).toHaveBeenCalledTimes(1);
    expect(verify).toHaveBeenCalledWith("the-key");
    expect(getToken()).toBe("fresh");
    expect(page.querySelector(".detail-header h1")?.textContent).toBe("Spring Open");
    expect(page.querySelector(".detail-tabs button.active")?.textContent).toBe(
      i18n.t("detail.tabs.register"),
    );
  });

  it("states a link that no longer works, offering sign-in and account creation", async () => {
    vi.spyOn(api, "openTournaments").mockResolvedValue([]);
    vi.spyOn(api, "verify").mockRejectedValue(new ApiError(410, "verification_invalid"));

    const page = mount("/verify#used");
    await settle();

    expect(page.querySelector(".verify-invalid")?.textContent).toContain(i18n.t("verify.invalid"));
    await click(
      [...page.querySelectorAll(".verify-invalid button")].find(
        (b) => b.textContent === i18n.t("login.createAccount"),
      ),
    );
    expect(page.querySelector("form#signup-form")).not.toBeNull();
  });
});
