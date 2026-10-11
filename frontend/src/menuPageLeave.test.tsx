// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter, useLocation } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { type Account, api, setToken } from "./api";
import i18n from "./i18n";

// The Profile page and the admin panel carry the top bar and a close control,
// and Escape leaves them as the control does (spec profile-page, "Leaving a
// page reached from the account menu").

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let host: HTMLElement | null = null;
let path = "";

function Probe() {
  path = useLocation().pathname;
  return null;
}

function mount(entries: string[]) {
  host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  act(() =>
    root.render(
      <MemoryRouter initialEntries={entries} initialIndex={entries.length - 1}>
        <App />
        <Probe />
      </MemoryRouter>,
    ),
  );
  return host;
}

async function settle() {
  await act(async () => {
    for (let i = 0; i < 6; i++) await Promise.resolve();
  });
}

function pressEscape(target: EventTarget = document) {
  act(() => {
    target.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  });
}

const ACCOUNT = {
  id: 1,
  email: "f@example.com",
  display_name: "F",
  hr_id: 7,
  nationality: "CZ",
  club: null,
  language: "cs",
  role: "admin",
  is_deployment_owner: false,
  organized_count: 0,
} as Account;

beforeEach(async () => {
  vi.restoreAllMocks();
  setToken("t");
  vi.spyOn(api, "account").mockResolvedValue(ACCOUNT);
  vi.spyOn(api, "openTournaments").mockResolvedValue([]);
  vi.spyOn(api, "heldTournaments").mockResolvedValue([]);
  vi.spyOn(api, "myTournaments").mockResolvedValue([]);
  vi.spyOn(api, "adminAccounts").mockResolvedValue([]);
  vi.spyOn(api, "adminPleas").mockResolvedValue([]);
  await i18n.changeLanguage("cs");
});

afterEach(() => {
  host?.remove();
  host = null;
  setToken(null);
});

describe("leaving the Profile page", () => {
  it("carries the top bar, whose name leads to the tournament list", async () => {
    const page = mount(["/profile"]);
    await settle();
    expect(page.querySelector(".topbar .logo-button")?.getAttribute("href")).toBe("/");
  });

  it("closes back to where it was opened from", async () => {
    const page = mount(["/nowhere", "/profile"]);
    await settle();
    const close = page.querySelector<HTMLButtonElement>(
      '.page-card-head button[aria-label="Zavřít"]',
    );
    act(() => close?.click());
    await settle();
    expect(path).toBe("/nowhere");
  });

  it("closes to the tournament list where it was reached by its address", async () => {
    mount(["/profile"]);
    await settle();
    pressEscape();
    await settle();
    expect(path).toBe("/");
  });

  it("leaves Escape to a field that has focus", async () => {
    const page = mount(["/nowhere", "/profile"]);
    await settle();
    const field = page.querySelector("input");
    expect(field).not.toBeNull();
    pressEscape(field ?? document);
    expect(path).toBe("/profile");
  });
});

describe("leaving the admin panel", () => {
  it("is left by Escape, back to where it was opened from", async () => {
    const page = mount(["/nowhere", "/admin"]);
    await settle();
    expect(page.querySelector(".topbar")).not.toBeNull();
    pressEscape();
    await settle();
    expect(path).toBe("/nowhere");
  });
});
