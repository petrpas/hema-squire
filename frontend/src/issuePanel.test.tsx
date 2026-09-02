// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import IssuePanel from "./IssuePanel";
import { api } from "./api";
import i18n from "./i18n";

// Making the fencer list billable (spec `imported-registrations`). The action
// allocates variable symbols that are never reclaimed, so what the organizer is
// told before committing is as much the feature as the button is.

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const t = i18n.getFixedT("cs");

let host: HTMLElement | null = null;

function mount(element: React.ReactElement) {
  host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  act(() => root.render(element));
  return host;
}

function buttonNamed(text: string) {
  return [...(host?.querySelectorAll("button") ?? [])].find(
    (button) => button.textContent?.trim() === text,
  ) as HTMLButtonElement | undefined;
}

async function settle() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

function counts(pending_rows: number, pending_dedup = 0) {
  vi.spyOn(api, "issuableCount").mockResolvedValue({ pending_rows, pending_dedup });
}

beforeEach(() => void vi.restoreAllMocks());
afterEach(() => {
  host?.remove();
  host = null;
});

it("states how many rows it would issue", async () => {
  counts(54);
  mount(<IssuePanel slug="cup" onIssued={() => {}} />);
  await settle();

  expect(host?.querySelector(".rail-count")?.textContent).toBe("(54)");
});

it("does not issue on the first click, but asks first", async () => {
  counts(54);
  const issue = vi.spyOn(api, "issueRegistrations");
  mount(<IssuePanel slug="cup" onIssued={() => {}} />);
  await settle();

  act(() => void buttonNamed(t("issue.action"))?.click());

  expect(issue).not.toHaveBeenCalled();
  // the two things that cannot be taken back: the count, and the promise
  expect(host?.textContent).toContain("54");
  expect(host?.textContent).toContain(t("issue.noMail"));
});

it("issues once confirmed, and reports what it did", async () => {
  counts(3);
  const issue = vi.spyOn(api, "issueRegistrations").mockResolvedValue({
    issued: 2,
    already: 1,
    skipped: [],
  });
  const onIssued = vi.fn();
  mount(<IssuePanel slug="cup" onIssued={onIssued} />);
  await settle();

  act(() => void buttonNamed(t("issue.action"))?.click());
  act(() => void buttonNamed(t("issue.confirmAction"))?.click());
  await settle();

  expect(issue).toHaveBeenCalledWith("cup");
  expect(onIssued).toHaveBeenCalled();
  expect(host?.textContent).toContain(t("issue.result", { issued: 2, already: 1 }));
});

it("names every row it skipped and why", async () => {
  counts(2);
  vi.spyOn(api, "issueRegistrations").mockResolvedValue({
    issued: 1,
    already: 0,
    skipped: [{ row_id: "imp:a", name: "Nada", reason: "no_discipline" }],
  });
  mount(<IssuePanel slug="cup" onIssued={() => {}} />);
  await settle();

  act(() => void buttonNamed(t("issue.action"))?.click());
  act(() => void buttonNamed(t("issue.confirmAction"))?.click());
  await settle();

  expect(host?.textContent).toContain("Nada");
  expect(host?.textContent).toContain(t("issue.reason.no_discipline"));
});

it("will not issue while duplicates are still under review, and says why", async () => {
  counts(54, 2);
  mount(<IssuePanel slug="cup" onIssued={() => {}} />);
  await settle();

  expect(buttonNamed(t("issue.action"))).toBeUndefined();
  expect(host?.textContent).toContain(t("issue.blockedByDedup", { count: 2 }));
});

it("offers nothing to do when every row already has a registration", async () => {
  counts(0);
  mount(<IssuePanel slug="cup" onIssued={() => {}} />);
  await settle();

  expect(buttonNamed(t("issue.action"))?.disabled).toBe(true);
});

it("says so when the action fails", async () => {
  counts(1);
  vi.spyOn(api, "issueRegistrations").mockRejectedValue(new Error("nope"));
  mount(<IssuePanel slug="cup" onIssued={() => {}} />);
  await settle();

  act(() => void buttonNamed(t("issue.action"))?.click());
  act(() => void buttonNamed(t("issue.confirmAction"))?.click());
  await settle();

  expect(host?.querySelector(".login-error")?.textContent).toBe(t("issue.failed"));
});
