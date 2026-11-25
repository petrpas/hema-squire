// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { getToken, type OpenTournament, setToken } from "./api";
import i18n from "./i18n";

// A stored token the server no longer accepts. The public reads refuse it with
// 401 rather than answer as anonymous (spec `public-browsing`), so a browser
// that kept it showed every tab of the list empty until the visitor signed in
// and out by hand. The refusal drops it, and the list reads again without it.

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
    for (let i = 0; i < 20; i++) await Promise.resolve();
  });
}

const UPCOMING = [
  {
    slug: "spring-open",
    display_name: "spring-open",
    organizers: [],
    disciplines: [],
    program_meters: [],
    registration_status: "open",
    date: "2026-12-20",
    timezone: "Europe/Prague",
    server_time: "2026-11-25T10:00:00Z",
    local_currency: "CZK",
    entrant_count: 0,
    club_count: 0,
  },
] as unknown as OpenTournament[];

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

/** The server as it stands: any credential presented is refused as expired,
 *  and the public list answers whoever comes without one. */
function server() {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const headers = new Headers(init?.headers);
    if (headers.has("Authorization")) return json(401, { detail: "invalid_token" });
    const path = String(input);
    if (path === "/api/tournaments/open") return json(200, UPCOMING);
    if (path === "/api/tournaments/held") return json(200, []);
    return json(404, { detail: "not_found" });
  });
}

beforeEach(async () => {
  vi.restoreAllMocks();
  setToken(null);
  await i18n.changeLanguage("en");
});

afterEach(() => {
  host?.remove();
  host = null;
  setToken(null);
});

describe("a refused credential", () => {
  it("is dropped, and the list is read again without it", async () => {
    server();
    setToken("expired");

    const page = mount("/");
    await settle();

    expect(getToken()).toBeNull();
    expect(page.textContent).toContain("spring-open");
    // the default tab is chosen on the anonymous answer, not on the refusal
    expect(page.querySelector(".home-tabs a.active")?.textContent).toContain("Open");
  });

  it("is not a 401 about a wrong password, which leaves a held token alone", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(json(401, { detail: "invalid_credentials" }));
    setToken("held");

    mount("/");
    await settle();

    expect(getToken()).toBe("held");
  });
});
