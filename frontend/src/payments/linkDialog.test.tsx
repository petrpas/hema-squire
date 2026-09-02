// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { ApiError, type Transaction, api } from "../api";
import i18n from "../i18n";
import LinkDialog from "./LinkDialog";

// The manual link dialog: the candidates the backend detected, a VS typed by
// hand, and several registrations settled by one transfer (spec
// `payments-console`, Manual link dialog).

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const t = i18n.getFixedT("cs");

function transaction(overrides: Partial<Transaction> = {}): Transaction {
  return {
    id: 7,
    external_id: "1",
    source: "fio",
    date: "2026-08-12",
    amount_cents: 120000,
    currency: "CZK",
    vs: null,
    message: "za Novaka a Dvoraka",
    payer_name: "Jan Novák",
    payer_account: null,
    status: "unmatched",
    status_reason: null,
    matched_registration_id: null,
    reinstate_available: false,
    candidate_vs: [2601001],
    last_evaluated_at: null,
    ...overrides,
  } as Transaction;
}

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

function click(button: HTMLButtonElement | undefined) {
  act(() => void button?.dispatchEvent(new MouseEvent("click", { bubbles: true })));
}

function type(value: string) {
  const input = host?.querySelector(".link-entry input") as HTMLInputElement;
  act(() => {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set?.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
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

function render(tx = transaction(), handlers: { onLinked?: () => void; onClose?: () => void } = {}) {
  return mount(
    <LinkDialog
      slug="cup"
      transaction={tx}
      onLinked={handlers.onLinked ?? (() => {})}
      onClose={handlers.onClose ?? (() => {})}
    />,
  );
}

it("offers a detected candidate and links it in one click", async () => {
  const link = vi.spyOn(api, "linkTransaction").mockResolvedValue({ rule_id: 1, applied: 1 });
  const onLinked = vi.fn();
  render(transaction(), { onLinked });

  click(buttonNamed("2601001"));
  click(buttonNamed(t("payments.link.confirm")));
  await settle();

  expect(link).toHaveBeenCalledWith("cup", 7, [2601001]);
  expect(onLinked).toHaveBeenCalled();
});

it("sends both registrations in one request when a transfer covers two", async () => {
  const link = vi.spyOn(api, "linkTransaction").mockResolvedValue({ rule_id: 1, applied: 2 });
  render();

  click(buttonNamed("2601001"));
  type("2601002");
  click(buttonNamed(t("payments.link.add")));
  click(buttonNamed(t("payments.link.confirm")));
  await settle();

  expect(link).toHaveBeenCalledTimes(1);
  expect(link).toHaveBeenCalledWith("cup", 7, [2601001, 2601002]);
});

it("names an unrecognised VS and keeps the dialog open with the entry", async () => {
  vi.spyOn(api, "linkTransaction").mockRejectedValue(
    new ApiError(404, { unknown_vs: [2609999] }),
  );
  const onClose = vi.fn();
  render(transaction({ candidate_vs: [] }), { onClose });

  type("2609999");
  click(buttonNamed(t("payments.link.add")));
  click(buttonNamed(t("payments.link.confirm")));
  await settle();

  expect(host?.textContent).toContain("2609999");
  expect(onClose).not.toHaveBeenCalled();
  // the selection survives, so the organizer corrects rather than retypes
  expect(host?.querySelector(".link-selected")?.textContent).toContain("2609999");
});

it("closes and refreshes when a concurrent poll matched the transaction first", async () => {
  vi.spyOn(api, "linkTransaction").mockRejectedValue(new ApiError(409, "already_matched"));
  const onLinked = vi.fn();
  const onClose = vi.fn();
  render(transaction(), { onLinked, onClose });

  click(buttonNamed("2601001"));
  click(buttonNamed(t("payments.link.confirm")));
  await settle();

  // the work was done elsewhere: not an error the organizer can act on
  expect(onClose).toHaveBeenCalled();
  expect(onLinked).toHaveBeenCalled();
});

it("creates no link when dismissed", () => {
  const link = vi.spyOn(api, "linkTransaction");
  const onClose = vi.fn();
  render(transaction(), { onClose });

  click(buttonNamed(t("common.cancel")));

  expect(link).not.toHaveBeenCalled();
  expect(onClose).toHaveBeenCalled();
});

it("cannot confirm with nothing selected", () => {
  render(transaction({ candidate_vs: [] }));
  expect(buttonNamed(t("payments.link.confirm"))?.disabled).toBe(true);
});
