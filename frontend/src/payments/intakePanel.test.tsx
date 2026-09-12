// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { ApiError, api, type Operation, type TournamentDetail } from "../api";
import i18n from "../i18n";
import { concludedMoment } from "../operationText";
import type { OperationsView } from "../useOperations";
import IntakePanel from "./IntakePanel";

// Getting money into the console: a statement from any bank, the bank's API
// where a token is configured, and the lifecycle passes on demand (spec
// `payments-intake`, Every intake action is reachable from the console).

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const t = i18n.getFixedT(i18n.language);

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

function operations(overrides: Partial<OperationsView> = {}): OperationsView {
  return { running: null, concluded: {}, refresh: vi.fn(), ...overrides };
}

function detail(fio: boolean, keptBy = "squire"): TournamentDetail {
  return {
    slug: "cup",
    fio_token_configured: fio,
    registrations_kept_by: keptBy,
  } as TournamentDetail;
}

/** The pre-flight count the panel reads on mount. Nothing to issue unless a
 *  test says otherwise, so the panel stays quiet about it. */
function issuable(pending_rows = 0, pending_dedup = 0) {
  return vi
    .spyOn(api, "issuableCount")
    .mockResolvedValue({ pending_rows, pending_dedup, skipped: [] });
}

function running(kind: string): Operation {
  return { id: 1, kind, status: "running", total: 10, done: 2 } as unknown as Operation;
}

function render(props: Partial<Parameters<typeof IntakePanel>[0]> = {}) {
  return mount(
    <IntakePanel
      slug="cup"
      detail={detail(false)}
      operations={operations()}
      reload={0}
      onChanged={() => {}}
      {...props}
    />,
  );
}

beforeEach(() => {
  vi.restoreAllMocks();
  issuable();
});
afterEach(() => {
  host?.remove();
  host = null;
});

it("does not offer the bank poll without a token, and says why", async () => {
  render({ detail: detail(false) });
  await settle();

  expect(buttonNamed(t("payments.intake.poll"))).toBeUndefined();
  expect(host?.textContent).toContain(t("payments.intake.noToken"));
});

it("offers the bank poll where a token is configured", async () => {
  render({ detail: detail(true) });
  await settle();

  expect(buttonNamed(t("payments.intake.poll"))).toBeDefined();
  expect(host?.textContent).not.toContain(t("payments.intake.noToken"));
});

it("disables every action while other work is running, naming it", async () => {
  render({ detail: detail(true), operations: operations({ running: running("parse") }) });
  await settle();

  expect(buttonNamed(t("payments.intake.upload"))?.disabled).toBe(true);
  expect(buttonNamed(t("payments.intake.poll"))?.disabled).toBe(true);
  expect(host?.textContent).toContain(t("operation.kind.parse"));
});

it("says a statement nothing can read was not imported", async () => {
  vi.spyOn(api, "importStatement").mockRejectedValue(new ApiError(409, "no_statement_parser"));
  render();

  const input = host?.querySelector('input[type="file"]') as HTMLInputElement;
  const file = new File(["Date,Amount\n"], "statement.csv", { type: "text/csv" });
  Object.defineProperty(input, "files", { value: [file] });
  act(() => void input.dispatchEvent(new Event("change", { bubbles: true })));
  await settle();

  expect(host?.querySelector(".login-error")?.textContent).toBe(t("payments.intake.noParser"));
});

it("says a table that is not a statement was not imported", async () => {
  // the detail is an object here, naming what was missing — the panel reads
  // the code out of it rather than comparing the whole detail to a string
  vi.spyOn(api, "importStatement").mockRejectedValue(
    new ApiError(422, { code: "unreadable_statement", missing: "an amount" }),
  );
  render();

  const input = host?.querySelector('input[type="file"]') as HTMLInputElement;
  Object.defineProperty(input, "files", {
    value: [new File(["Timestamp,Name\n"], "regs.csv", { type: "text/csv" })],
  });
  act(() => void input.dispatchEvent(new Event("change", { bubbles: true })));
  await settle();

  expect(host?.querySelector(".login-error")?.textContent).toBe(t("payments.intake.unreadable"));
});

it("says a file that is not a table at all was not imported", async () => {
  vi.spyOn(api, "importStatement").mockRejectedValue(
    new ApiError(422, "unsupported_statement_format"),
  );
  render();

  const input = host?.querySelector('input[type="file"]') as HTMLInputElement;
  Object.defineProperty(input, "files", {
    value: [new File(["%PDF"], "statement.pdf", { type: "application/pdf" })],
  });
  act(() => void input.dispatchEvent(new Event("change", { bubbles: true })));
  await settle();

  expect(host?.querySelector(".login-error")?.textContent).toBe(
    t("payments.intake.unsupportedFormat"),
  );
});

/** What `concludedMoment` makes of the fixtures' `finished_at` — asked of the
 *  helper rather than spelled out, since the reader's own zone decides it. */
const WHEN = concludedMoment({ finished_at: "2026-09-06T07:33:04Z" } as unknown as Operation);

it("reports what a concluded import brought in, and when it landed", async () => {
  const concluded = {
    statement: {
      id: 3,
      kind: "statement",
      status: "done",
      finished_at: "2026-09-06T07:33:04Z",
      outcome: { new: 2, matched: 1 },
    } as unknown as Operation,
  };
  render({ operations: operations({ concluded }) });
  await settle();

  expect(host?.textContent).toContain(
    t("payments.intake.imported", { when: WHEN, new: 2, matched: 1 }),
  );
});

it("does not let a days-old import read as the poll just run", async () => {
  // the defect this guards: the panel shows the most recent concluded run of
  // each kind with no bound on its age, so a four-day-old statement report sat
  // under a fresh poll result and was read as its outcome
  vi.spyOn(api, "fioPoll").mockResolvedValue({
    new: 0,
    duplicate: 0,
    matched: 0,
    flagged: 0,
    unmatched: 0,
    partial: 0,
    set_aside: 0,
    issued: 0,
    already_issued: 0,
    skipped: [],
  });
  const concluded = {
    statement: {
      id: 5,
      kind: "statement",
      status: "done",
      finished_at: "2026-09-06T07:33:04Z",
      outcome: { new: 43, matched: 0 },
    } as unknown as Operation,
  };
  render({ detail: detail(true), operations: operations({ concluded }) });
  await settle();

  act(() => void buttonNamed(t("payments.intake.poll"))?.click());
  await settle();

  const text = host?.textContent ?? "";
  // both are shown — the old report is not withdrawn — but the old one carries
  // the day it landed and the poll says it is the one that just ran
  expect(text).toContain(t("payments.intake.polled", { new: 0, matched: 0 }));
  expect(text).toContain(t("payments.intake.imported", { when: WHEN, new: 43, matched: 0 }));
  expect(text).toContain("6. 9. 2026");
});

it("polls the bank and reports what it brought in", async () => {
  const poll = vi.spyOn(api, "fioPoll").mockResolvedValue({
    new: 3,
    duplicate: 0,
    matched: 2,
    flagged: 0,
    unmatched: 1,
    partial: 0,
    set_aside: 0,
    issued: 0,
    already_issued: 0,
    skipped: [],
  });
  const onChanged = vi.fn();
  render({ detail: detail(true), onChanged });

  act(() => void buttonNamed(t("payments.intake.poll"))?.click());
  await settle();

  expect(poll).toHaveBeenCalledWith("cup");
  expect(onChanged).toHaveBeenCalled();
  expect(host?.textContent).toContain(t("payments.intake.polled", { new: 3, matched: 2 }));
});

// The lifecycle passes are no longer fired from here: in manual mode they
// decide nothing, every registration being dormant, while still able to stamp
// seating settled. `POST /payments/process` and the scheduler keep them; the
// organizer gets them back as actions over the debtors table.

it("does not offer the lifecycle passes", async () => {
  render();
  await settle();

  expect(buttonNamed(t("payments.intake.lifecycle"))).toBeUndefined();
});

// Intake issues registrations for the fencer list before it matches anything,
// so the panel carries what the confirmation dialog used to: what the import
// will irreversibly do, and what it could not do (design Decision 10).

it("states what an import will issue, and that the symbols are not reclaimed", async () => {
  issuable(54);
  render({ detail: detail(false) });
  await settle();

  expect(host?.textContent).toContain(t("payments.intake.willIssueWithSymbols", { count: 54 }));
});

it("says nothing about symbols where the organizer keeps the registrations", async () => {
  issuable(54);
  render({ detail: detail(false, "organizer") });
  await settle();

  expect(host?.textContent).toContain(t("payments.intake.willIssue", { count: 54 }));
  expect(host?.textContent).not.toContain(t("payments.intake.willIssueWithSymbols", { count: 54 }));
});

it("announces nothing where there is nothing to issue", async () => {
  issuable(0);
  render({ detail: detail(false) });
  await settle();

  expect(host?.textContent).not.toContain(t("payments.intake.willIssue", { count: 0 }));
});

it("states the pending duplicates instead, before anything is uploaded", async () => {
  issuable(54, 3);
  render({ detail: detail(false) });
  await settle();

  expect(host?.textContent).toContain(t("payments.intake.dedupPending", { count: 3 }));
  expect(host?.textContent).not.toContain(t("payments.intake.willIssueWithSymbols", { count: 54 }));
});

it("reports a refused poll on the duplicates rather than as a failure", async () => {
  vi.spyOn(api, "fioPoll").mockRejectedValue(
    new ApiError(409, { code: "dedup_pending", groups: 2 }),
  );
  render({ detail: detail(true) });

  act(() => void buttonNamed(t("payments.intake.poll"))?.click());
  await settle();

  expect(host?.textContent).toContain(t("payments.intake.dedupPending", { count: 2 }));
  expect(host?.textContent).not.toContain(t("payments.intake.pollFailed"));
});

it("names the rows an import could not issue, and why", async () => {
  const concluded = {
    statement: {
      id: 7,
      kind: "statement",
      status: "done",
      outcome: {
        new: 2,
        matched: 1,
        issued: 51,
        already_issued: 0,
        skipped: [{ row_id: "imp:9", name: "Jan Novák", reason: "no_discipline" }],
      },
    } as unknown as Operation,
  };
  render({ operations: operations({ concluded }) });
  await settle();

  expect(host?.textContent).toContain(t("payments.intake.issued", { count: 51 }));
  expect(host?.textContent).toContain(
    t("issue.skipped", { name: "Jan Novák", reason: t("issue.reason.no_discipline") }),
  );
});

it("says nothing about issuing where an import issued nothing", async () => {
  const concluded = {
    statement: {
      id: 8,
      kind: "statement",
      status: "done",
      finished_at: "2026-09-06T07:33:04Z",
      outcome: { new: 2, matched: 1, issued: 0, already_issued: 51, skipped: [] },
    } as unknown as Operation,
  };
  render({ operations: operations({ concluded }) });
  await settle();

  expect(host?.textContent).toContain(
    t("payments.intake.imported", { when: WHEN, new: 2, matched: 1 }),
  );
  expect(host?.textContent).not.toContain(t("payments.intake.issued", { count: 0 }));
});

// The clear is the load's undo, so it lives in this card directly beneath the
// control that loads a statement, rather than in a card of its own further
// down the rail (spec `payments-clearing`).

it("offers the clear directly beneath the control that loads a statement", async () => {
  vi.spyOn(api, "clearablePayments").mockResolvedValue({ payments: 43, credited: 0 });
  render({ detail: detail(true) });
  await settle();

  const buttons = [...(host?.querySelectorAll("button") ?? [])].map((button) =>
    button.textContent?.trim(),
  );
  expect(buttons.indexOf(t("payments.clear.action", { payments: 43 }))).toBe(
    buttons.indexOf(t("payments.intake.upload")) + 1,
  );
});

it("does not offer the clear while other work is running", async () => {
  vi.spyOn(api, "clearablePayments").mockResolvedValue({ payments: 43, credited: 0 });
  render({ detail: detail(true), operations: operations({ running: running("parse") }) });
  await settle();

  expect(buttonNamed(t("payments.clear.action", { payments: 43 }))?.disabled).toBe(true);
});
