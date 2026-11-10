// @vitest-environment jsdom
import { expect, it } from "vitest";

import { ApiError, type TournamentFlags } from "../api";
import i18n from "../i18n";
import { apiErrors } from "../validation";
import { saveFailureMessage } from "./shared";

// A published tournament refuses EVERY write while a mandatory item is
// missing (backend `setup.guard_published_completeness`), including a save of
// a section that has nothing to do with the missing item. The statement must
// therefore name the items and the tab that holds them — a bare status leaves
// the organizer with a save that fails and no reachable cause.

const t = i18n.getFixedT("en");

const MODE: TournamentFlags = {
  feature_schedule: true,
  feature_payments: true,
  feature_teams: true,
  feature_extras: true,
};

function incomplete(...missing: string[]): ApiError {
  return new ApiError(422, { reason: "setup_incomplete", missing });
}

it("names the missing item and the tab that resolves it", () => {
  const message = saveFailureMessage(incomplete("bank_account_holder"), [], MODE, t);
  expect(message).toContain(t("setup.missing.bank_account_holder"));
  expect(message).toContain(t("setup.tabs.payments"));
});

it("names each tab once, however many items it holds", () => {
  const message = saveFailureMessage(
    incomplete("bank_account", "bank_account_holder"),
    [],
    MODE,
    t,
  );
  expect(message).toContain(t("setup.missing.bank_account"));
  expect(message.match(new RegExp(t("setup.tabs.payments"), "g"))).toHaveLength(1);
});

it("names an item whose editor the mode conceals without a tab to fix it on", () => {
  // `team_bounds` belongs to the disciplines tab only while teams are on;
  // with the feature off the editor is gone, so no tab can be named.
  const message = saveFailureMessage(
    incomplete("team_bounds"),
    [],
    { ...MODE, feature_teams: false },
    t,
  );
  expect(message).toContain(t("setup.missing.team_bounds"));
  expect(message).not.toContain(t("setup.tabs.disciplines"));
});

it("falls back to the item's key when the client does not recognize it", () => {
  const message = saveFailureMessage(incomplete("item_from_a_newer_backend"), [], MODE, t);
  expect(message).toContain("item_from_a_newer_backend");
});

it("prefers the fields the backend named over any other reading", () => {
  const err = new ApiError(422, { errors: [{ field: "fee", code: "out_of_range", params: {} }] });
  const message = saveFailureMessage(err, apiErrors(err), MODE, t);
  expect(message).toBe(t("validation.out_of_range", {}));
});

it("reports a failure it cannot read by status", () => {
  const message = saveFailureMessage(new ApiError(503, "unavailable"), [], MODE, t);
  expect(message).toBe(t("setup.saveBar.genericError", { status: 503 }));
});
