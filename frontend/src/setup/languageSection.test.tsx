// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";

import { api, type TournamentDetail } from "../api";
import { LanguageSection } from "./LanguageSection";

// The communication language on `OTHER`: the stored value shown, and a change
// applied by the section itself, with no tab save (spec setup-navigation, The
// communication language has its own control).

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let host: HTMLElement | null = null;

afterEach(() => {
  host?.remove();
  host = null;
  vi.restoreAllMocks();
});

function mount(language: string, onApplied: () => void) {
  host = document.createElement("div");
  document.body.append(host);
  const detail = { slug: "cup", language } as unknown as TournamentDetail;
  act(() =>
    createRoot(host!).render(<LanguageSection slug="cup" detail={detail} onApplied={onApplied} />),
  );
  return host.querySelector("select")!;
}

it("shows the stored language", () => {
  expect(mount("cs", vi.fn()).value).toBe("cs");
});

it("sends a change at once and refetches", async () => {
  const update = vi
    .spyOn(api, "updateTournament")
    .mockResolvedValue({} as unknown as TournamentDetail);
  const onApplied = vi.fn();
  const select = mount("cs", onApplied);

  await act(async () => {
    select.value = "en";
    select.dispatchEvent(new Event("change", { bubbles: true }));
  });

  expect(update).toHaveBeenCalledWith("cup", { language: "en" });
  expect(onApplied).toHaveBeenCalledOnce();
});
