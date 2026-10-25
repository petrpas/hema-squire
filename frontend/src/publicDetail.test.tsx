// @vitest-environment jsdom
import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { type Account, ApiError, api, getToken, setToken } from "./api";
import i18n from "./i18n";
import { detailApi, mount, mounted, registerTab, settle } from "./publicDetailFixture";

// A tournament's detail reads without an account, and the Register action it
// offers leads to sign-in rather than to a form that could only fail (change
// `public-tournament-list`).

/** The sign-in screen's way back out, which renders in English whatever the
 *  visitor was reading a moment ago. */
function back(page: HTMLElement): HTMLButtonElement | null {
  return page.querySelector<HTMLButtonElement>("form#login-form .login-back");
}

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

describe("a tournament's detail is public", () => {
  it("renders without a credential, asking nothing personal", async () => {
    detailApi();
    const mine = vi.spyOn(api, "myRegistration");

    const page = mount("/t/spring-open");
    await settle();

    expect(page.querySelector("form#login-form")).toBeNull();
    expect(page.textContent).toContain("Spring Open");
    expect(mine).not.toHaveBeenCalled();
  });

  it("shows none of the four filter tabs while it is open", async () => {
    detailApi();
    const page = mount("/t/spring-open");
    await settle();

    expect(page.querySelector(".home-tabs")).toBeNull();
    expect(page.textContent).not.toContain(i18n.t("home.tabs.announced"));
  });

  it("names the town on its facts line and the address under it, link and all", async () => {
    detailApi({
      city: "Brno",
      address: "[Sportovní hala](https://osm.org/go/0J0ajlLg8?m=)",
    });
    const page = mount("/t/spring-open");
    await settle();

    expect(page.querySelector(".detail-facts")?.textContent).toContain("Brno");
    const address = page.querySelector(".detail-address");
    expect(address?.textContent).toBe("Sportovní hala");
    expect(address?.querySelector("a")?.getAttribute("href")).toBe(
      "https://osm.org/go/0J0ajlLg8?m=",
    );
  });

  it("leaves no address line where there is no address", async () => {
    detailApi({ city: "Brno" });
    const page = mount("/t/spring-open");
    await settle();

    expect(page.querySelector(".detail-facts")?.textContent).toContain("Brno");
    expect(page.querySelector(".detail-address")).toBeNull();
  });

  it("offers Spravovat to an account that may manage it, and to nobody else", async () => {
    detailApi({ organized: true });
    const page = mount("/t/spring-open");
    await settle();
    const manage = page.querySelector<HTMLAnchorElement>(".detail-cover a.button-quiet");
    expect(manage?.textContent).toBe(i18n.t("home.manage"));
    expect(manage?.getAttribute("href")).toBe("/organizer/spring-open/console");
    mounted.host?.remove();

    detailApi();
    const other = mount("/t/spring-open");
    await settle();
    expect(other.querySelector(".detail-cover a.button-quiet")).toBeNull();
  });

  it("keeps the shared top bar", async () => {
    detailApi();
    const page = mount("/t/spring-open");
    await settle();

    expect(page.querySelector(".topbar .logo")?.textContent).toBe("HEMA Squire");
    expect(page.querySelector(".topbar-title")?.textContent).toBe(i18n.t("app.listTitle"));
    expect(page.querySelector(".detail-header h1")?.textContent).toBe("Spring Open");
  });
});

describe("registering while signed out", () => {
  it("leads to sign-in, stating why", async () => {
    detailApi();
    const page = mount("/t/spring-open");
    await settle();

    const register = registerTab(page);
    expect(register).not.toBeUndefined();
    await act(async () => {
      register?.click();
    });

    expect(page.querySelector("form#login-form")).not.toBeNull();
    // the sign-in screen renders in English, so the reason does too
    // and it no longer says that registering needs an account
    expect(page.querySelector(".login-subtitle .help-hint-box")?.textContent).toBe(
      "Sign in, create an account, or register without one.",
    );
    expect(page.querySelector("form#login-form .login-guest")?.textContent).toBe(
      "Register without signing up",
    );
  });

  it("comes back to the tournament on its registration tab", async () => {
    detailApi();
    vi.spyOn(api, "login").mockResolvedValue({ token: "fresh" } as never);
    vi.spyOn(api, "account").mockResolvedValue({
      display_name: "F",
      language: "cs",
      role: "fencer",
    } as Account);
    vi.spyOn(api, "myRegistration").mockRejectedValue(new ApiError(404, "none"));

    const page = mount("/t/spring-open");
    await settle();
    await act(async () => {
      registerTab(page)?.click();
    });

    const form = page.querySelector<HTMLFormElement>("form#login-form");
    const email = form?.querySelector<HTMLInputElement>('input[name="email"]');
    const password = form?.querySelector<HTMLInputElement>('input[name="password"]');
    await act(async () => {
      if (email) {
        email.value = "f@example.com";
        email.dispatchEvent(new Event("input", { bubbles: true }));
      }
      if (password) {
        password.value = "correct-horse";
        password.dispatchEvent(new Event("input", { bubbles: true }));
      }
    });
    await act(async () => {
      form?.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    });
    await settle();

    expect(getToken()).toBe("fresh");
    expect(page.querySelector("form#login-form")).toBeNull();
    const active = page.querySelector(".detail-tabs button.active");
    expect(active?.textContent).toBe(i18n.t("detail.tabs.register"));
  });

  it("can be declined, leaving the tournament as it was", async () => {
    detailApi();
    const page = mount("/t/spring-open");
    await settle();
    await act(async () => {
      registerTab(page)?.click();
    });
    expect(page.querySelector("form#login-form")).not.toBeNull();

    await act(async () => {
      back(page)?.click();
    });

    expect(page.querySelector("form#login-form")).toBeNull();
    expect(page.querySelector(".detail-header h1")?.textContent).toBe("Spring Open");
  });

  it("is dismissed by Escape, the screen being over the page and not at a URL", async () => {
    detailApi();
    const page = mount("/t/spring-open");
    await settle();
    await act(async () => {
      registerTab(page)?.click();
    });

    await act(async () => {
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    });

    expect(page.querySelector("form#login-form")).toBeNull();
    expect(page.querySelector(".detail-header h1")?.textContent).toBe("Spring Open");
  });
});
