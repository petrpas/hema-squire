// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { ApiError, api } from "../api";
import i18n from "../i18n";
import IssueOnArrival from "./IssueOnArrival";

// A tournament whose payments Squire does not collect has no intake to issue
// its roster, so the Payments phase issues on arrival (spec
// `imported-registrations`, design Decision 10).

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const t = i18n.getFixedT(i18n.language);

let host: HTMLElement | null = null;

function render(onIssued = vi.fn()) {
  host = document.createElement("div");
  document.body.append(host);
  act(() => createRoot(host!).render(<IssueOnArrival slug="cup" onIssued={onIssued} />));
  return onIssued;
}

async function settle() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

beforeEach(() => void vi.restoreAllMocks());
afterEach(() => {
  host?.remove();
  host = null;
});

it("issues the roster on arrival and refreshes the list", async () => {
  const issue = vi
    .spyOn(api, "issueRegistrations")
    .mockResolvedValue({ issued: 51, already: 0, skipped: [] });
  const onIssued = render();
  await settle();

  expect(issue).toHaveBeenCalledWith("cup");
  expect(onIssued).toHaveBeenCalled();
});

it("says nothing when it issued cleanly", async () => {
  vi.spyOn(api, "issueRegistrations").mockResolvedValue({
    issued: 51,
    already: 0,
    skipped: [],
  });
  render();
  await settle();

  expect(host?.textContent).toBe("");
});

it("does not refresh the list when there was nothing to issue", async () => {
  vi.spyOn(api, "issueRegistrations").mockResolvedValue({
    issued: 0,
    already: 51,
    skipped: [],
  });
  const onIssued = render();
  await settle();

  expect(onIssued).not.toHaveBeenCalled();
});

it("names the rows it could not issue, and why", async () => {
  vi.spyOn(api, "issueRegistrations").mockResolvedValue({
    issued: 50,
    already: 0,
    skipped: [{ row_id: "imp:9", name: "Jan Novák", reason: "no_discipline" }],
  });
  render();
  await settle();

  expect(host?.textContent).toContain(
    t("issue.skipped", { name: "Jan Novák", reason: t("issue.reason.no_discipline") }),
  );
});

it("states the unresolved duplicates rather than failing silently", async () => {
  vi.spyOn(api, "issueRegistrations").mockRejectedValue(new ApiError(409, "dedup_pending"));
  render();
  await settle();

  expect(host?.textContent).toContain(t("issue.blockedByDedup"));
});
