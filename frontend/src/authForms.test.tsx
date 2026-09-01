// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import Login from "./Login";
import RequireAuth from "./RequireAuth";
import { ApiError, api, getToken, setToken } from "./api";

// The three things that decide whether a fencer gets into the app from a
// phone: a credential manager can see the fields, a slow submit says so, and
// a token the server has stopped accepting ends at Login rather than at an
// empty signed-in shell (change `add-mobile-fencer-layout`, group 2).

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let host: HTMLElement | null = null;

function mount(node: React.ReactNode) {
  host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  act(() => root.render(node));
  return host;
}

async function settle() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
  });
}

beforeEach(() => {
  vi.restoreAllMocks();
  setToken(null);
});

afterEach(() => {
  host?.remove();
  host = null;
  setToken(null);
});

describe("credential managers can read the auth forms", () => {
  // Asserted against the parsed DOM rather than the rendered markup string:
  // HTML attribute names are case-insensitive, so React's server renderer is
  // free to emit `autoComplete=` and the browser still parses `autocomplete`.
  // The DOM is what a password manager reads, so the DOM is what we check.
  it("declares the sign-in fields", () => {
    const page = mount(<Login onLogin={() => {}} />);

    expect(page.querySelector("form")!.id).toBe("login-form");

    const email = page.querySelector('input[name="email"]')!;
    expect(email.getAttribute("type")).toBe("email");
    expect(email.getAttribute("autocomplete")).toBe("username");
    expect(email.getAttribute("autocapitalize")).toBe("none");
    expect(email.getAttribute("inputmode")).toBe("email");
    expect(email.getAttribute("spellcheck")).toBe("false");

    const password = page.querySelector('input[name="password"]')!;
    expect(password.getAttribute("autocomplete")).toBe("current-password");
    expect(password.getAttribute("enterkeyhint")).toBe("go");
  });

  it("declares the sign-up fields, e-mail included as the identifier", async () => {
    const page = mount(<Login onLogin={() => {}} />);
    // switch to signup — the create-account control is the last link-button
    // the create-account control is the last link-button on the card
    const links = page.querySelectorAll("button.link-button");
    const toSignup = links[links.length - 1];
    await act(async () => {
      toSignup.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    const form = page.querySelector("form")!;
    expect(form.id).toBe("signup-form");

    const email = form.querySelector('input[name="email"]')!;
    // "username" on signup too: without it no manager offers to save the pair
    expect(email.getAttribute("autocomplete")).toBe("username");

    const password = form.querySelector('input[name="password"]')!;
    expect(password.getAttribute("autocomplete")).toBe("new-password");

    const display = form.querySelector('input[name="display_name"]')!;
    expect(display.getAttribute("autocomplete")).toBe("name");
    expect(display.getAttribute("autocapitalize")).toBe("words");
  });

  it("gives the two modes different form identities", async () => {
    const page = mount(<Login onLogin={() => {}} />);
    expect(page.querySelector("form")!.id).toBe("login-form");

    // the create-account control is the last link-button on the card
    const links = page.querySelectorAll("button.link-button");
    const toSignup = links[links.length - 1];
    await act(async () => {
      toSignup.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });
    expect(page.querySelector("form")!.id).toBe("signup-form");
  });
});

describe("a submission in flight is stated in words", () => {
  it("changes the sign-in label while the request is outstanding", async () => {
    let release: (value: { token: string }) => void = () => {};
    vi.spyOn(api, "login").mockReturnValue(
      new Promise((resolve) => {
        release = resolve;
      }) as never,
    );

    const page = mount(<Login onLogin={() => {}} />);
    const submit = page.querySelector('button[type="submit"]')! as HTMLButtonElement;
    const resting = submit.textContent;

    await act(async () => {
      page.querySelector("form")!.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
    });

    expect(submit.disabled).toBe(true);
    expect(submit.textContent).not.toBe(resting);
    expect(submit.textContent).toMatch(/signing in/i);
    // static text, not a spinner — nothing animated was introduced
    expect(page.querySelector(".spinner")).toBeNull();

    await act(async () => {
      release({ token: "t" });
      await Promise.resolve();
    });
  });

  it("holds the submit control still when an error appears", async () => {
    vi.spyOn(api, "login").mockRejectedValue(new ApiError(401, "bad"));

    const page = mount(<Login onLogin={() => {}} />);
    // the slot is in the layout before any error exists, so nothing below it
    // moves when a message arrives
    const slot = page.querySelector(".login-error")!;
    expect(slot).not.toBeNull();
    expect(slot.textContent).toBe("");

    await act(async () => {
      page.querySelector("form")!.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
    });
    await settle();

    expect(page.querySelector(".login-error")!.textContent).not.toBe("");
  });
});

describe("an expired session ends at Login", () => {
  function gate() {
    return mount(
      <MemoryRouter initialEntries={["/t/spring-open-2026"]}>
        <Routes>
          <Route path="/t/:slug" element={<RequireAuth />}>
            <Route index element={<p>signed in</p>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );
  }

  it("discards a rejected token and shows Login", async () => {
    setToken("stale");
    vi.spyOn(api, "account").mockRejectedValue(new ApiError(401, "expired"));

    const page = gate();
    await settle();

    expect(page.querySelector("form#login-form")).not.toBeNull();
    expect(page.textContent).not.toContain("signed in");
    expect(getToken()).toBeNull();
  });

  it("keeps an offline fencer signed in", async () => {
    setToken("fine");
    // a network failure is not a rejected credential — it resolves itself,
    // and signing the fencer out would lose their place for no reason
    vi.spyOn(api, "account").mockRejectedValue(new TypeError("Failed to fetch"));

    const page = gate();
    await settle();

    expect(page.textContent).toContain("signed in");
    expect(getToken()).toBe("fine");
  });

  it("leaves a live session alone", async () => {
    setToken("good");
    vi.spyOn(api, "account").mockResolvedValue({
      display_name: "F",
      language: "cs",
    } as never);

    const page = gate();
    await settle();

    expect(page.textContent).toContain("signed in");
    expect(getToken()).toBe("good");
  });
});
