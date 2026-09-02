// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { ApiError, type Operation, type TournamentDetail, api } from "../api";
import i18n from "../i18n";
import type { OperationsView } from "../useOperations";
import IntakePanel from "./IntakePanel";

// Getting money into the console: a statement from any bank, the bank's API
// where a token is configured, and the lifecycle passes on demand (spec
// `payments-intake`, Every intake action is reachable from the console).

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

function operations(overrides: Partial<OperationsView> = {}): OperationsView {
  return { running: null, concluded: {}, refresh: vi.fn(), ...overrides };
}

function detail(fio: boolean): TournamentDetail {
  return { slug: "cup", fio_token_configured: fio } as TournamentDetail;
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
      onChanged={() => {}}
      {...props}
    />,
  );
}

beforeEach(() => void vi.restoreAllMocks());
afterEach(() => {
  host?.remove();
  host = null;
});

it("does not offer the bank poll without a token, and says why", () => {
  render({ detail: detail(false) });

  expect(buttonNamed(t("payments.intake.poll"))).toBeUndefined();
  expect(host?.textContent).toContain(t("payments.intake.noToken"));
});

it("offers the bank poll where a token is configured", () => {
  render({ detail: detail(true) });

  expect(buttonNamed(t("payments.intake.poll"))).toBeDefined();
  expect(host?.textContent).not.toContain(t("payments.intake.noToken"));
});

it("disables every action while other work is running, naming it", () => {
  render({ detail: detail(true), operations: operations({ running: running("parse") }) });

  expect(buttonNamed(t("payments.intake.upload"))?.disabled).toBe(true);
  expect(buttonNamed(t("payments.intake.poll"))?.disabled).toBe(true);
  expect(buttonNamed(t("payments.intake.lifecycle"))?.disabled).toBe(true);
  expect(host?.textContent).toContain(t("operation.kind.parse"));
});

it("says a statement nothing can read was not imported", async () => {
  vi.spyOn(api, "importStatement").mockRejectedValue(
    new ApiError(409, "no_statement_parser"),
  );
  render();

  const input = host?.querySelector('input[type="file"]') as HTMLInputElement;
  const file = new File(["Date,Amount\n"], "statement.csv", { type: "text/csv" });
  Object.defineProperty(input, "files", { value: [file] });
  act(() => void input.dispatchEvent(new Event("change", { bubbles: true })));
  await settle();

  expect(host?.querySelector(".login-error")?.textContent).toBe(
    t("payments.intake.noParser"),
  );
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

  expect(host?.querySelector(".login-error")?.textContent).toBe(
    t("payments.intake.unreadable"),
  );
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

it("reports what a concluded import brought in", () => {
  const concluded = {
    statement: {
      id: 3,
      kind: "statement",
      status: "done",
      outcome: { new: 2, matched: 1 },
    } as unknown as Operation,
  };
  render({ operations: operations({ concluded }) });

  expect(host?.textContent).toContain(
    t("payments.intake.imported", { new: 2, matched: 1 }),
  );
});

it("polls the bank and reports what it brought in", async () => {
  const poll = vi.spyOn(api, "fioPoll").mockResolvedValue({
    new: 3, duplicate: 0, matched: 2, flagged: 0, unmatched: 1, partial: 0, set_aside: 0,
  });
  const onChanged = vi.fn();
  render({ detail: detail(true), onChanged });

  act(() => void buttonNamed(t("payments.intake.poll"))?.click());
  await settle();

  expect(poll).toHaveBeenCalledWith("cup");
  expect(onChanged).toHaveBeenCalled();
  expect(host?.textContent).toContain(t("payments.intake.polled", { new: 3, matched: 2 }));
});

it("runs the lifecycle passes on demand", async () => {
  const process = vi.spyOn(api, "processLifecycle").mockResolvedValue(undefined);
  const onChanged = vi.fn();
  render({ onChanged });

  act(() => void buttonNamed(t("payments.intake.lifecycle"))?.click());
  await settle();

  expect(process).toHaveBeenCalledWith("cup");
  expect(onChanged).toHaveBeenCalled();
});
