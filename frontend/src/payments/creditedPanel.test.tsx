// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { api, type CreditedTransaction, type CreditReversalRow } from "../api";
import i18n from "../i18n";
import { formatTransactionAmount } from "../money";
import CreditedPanel from "./CreditedPanel";

// The transactions holding a live credit, and the reversal that is the only way
// back for the ones no payment link explains (spec `payments-clearing`, "Every
// credited transaction SHALL have such a route out").

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

function credit(overrides: Partial<CreditReversalRow> = {}): CreditReversalRow {
  return {
    registration_id: 3,
    fencer_name: "Jan Novák",
    vs: 2601001,
    amount: "1000.00",
    currency: "CZK",
    unsettles: true,
    ...overrides,
  };
}

function transaction(overrides: Partial<CreditedTransaction> = {}): CreditedTransaction {
  return {
    id: 11,
    external_id: "fio:1",
    source: "fio",
    date: "2026-08-01",
    amount_cents: 100000,
    currency: "CZK",
    vs: 2601001,
    message: null,
    payer_name: "Jan Novák",
    payer_account: null,
    status: "matched",
    status_reason: null,
    matched_registration_id: 3,
    reinstate_available: false,
    candidate_vs: [],
    named_person: null,
    proposed_fencer_id: null,
    proposed_fencer_name: null,
    last_evaluated_at: null,
    settled_by_hand_reason: null,
    settled_by_recorded_payment: null,
    credits: [credit()],
    ...overrides,
  } as CreditedTransaction;
}

it("lists a credited transaction with everyone it credited", async () => {
  vi.spyOn(api, "creditedTransactions").mockResolvedValue([
    transaction({
      credits: [credit(), credit({ registration_id: 4, fencer_name: "Eva Malá" })],
    }),
  ]);
  mount(<CreditedPanel slug="cup" reload={0} onChanged={vi.fn()} />);
  await settle();

  expect(host?.textContent).toContain(formatTransactionAmount(100000, "CZK"));
  // both, not the one the matcher happened to resolve to
  expect(host?.textContent).toContain("Jan Novák");
  expect(host?.textContent).toContain("Eva Malá");
});

it("collapses to its heading when nothing holds a credit", async () => {
  vi.spyOn(api, "creditedTransactions").mockResolvedValue([]);
  mount(<CreditedPanel slug="cup" reload={0} onChanged={vi.fn()} />);
  await settle();

  expect(host?.textContent).toContain(t("payments.credited.title"));
  expect(host!.querySelector("tbody tr")).toBeNull();
});

it("reports its own failure", async () => {
  vi.spyOn(api, "creditedTransactions").mockRejectedValue(new Error("down"));
  mount(<CreditedPanel slug="cup" reload={0} onChanged={vi.fn()} />);
  await settle();

  expect(host?.textContent).toContain(t("payments.queue.failed"));
});

it("names who stops reading as paid before the reversal is confirmed", async () => {
  vi.spyOn(api, "creditedTransactions").mockResolvedValue([transaction()]);
  // asked of the preflight rather than of the row already loaded: what the
  // reversal will do is a derivation, and the list may be a minute old
  const preflight = vi.spyOn(api, "reversalPreflight").mockResolvedValue({
    transaction_id: 11,
    registrations: [credit()],
  });
  const reverse = vi
    .spyOn(api, "reverseTransactionCredit")
    .mockResolvedValue({} as CreditedTransaction);
  const changed = vi.fn();
  mount(<CreditedPanel slug="cup" reload={0} onChanged={changed} />);
  await settle();

  act(() => (host!.querySelector("td.col-actions button") as HTMLButtonElement).click());
  await settle();
  expect(preflight).toHaveBeenCalledWith("cup", 11);
  expect(host?.textContent).toContain("Jan Novák");
  expect(host?.textContent).toContain(
    t("payments.credited.reverseUnsettles", { names: "Jan Novák" }),
  );
  expect(reverse).not.toHaveBeenCalled();

  act(() => (host!.querySelector(".modal-actions .btn-primary") as HTMLButtonElement).click());
  await settle();
  expect(reverse).toHaveBeenCalledWith("cup", 11);
  expect(changed).toHaveBeenCalled();
});

it("says plainly where nothing stops reading as paid", async () => {
  vi.spyOn(api, "creditedTransactions").mockResolvedValue([transaction()]);
  vi.spyOn(api, "reversalPreflight").mockResolvedValue({
    transaction_id: 11,
    registrations: [credit({ unsettles: false })],
  });
  mount(<CreditedPanel slug="cup" reload={0} onChanged={vi.fn()} />);
  await settle();

  act(() => (host!.querySelector("td.col-actions button") as HTMLButtonElement).click());
  await settle();
  expect(host?.textContent).toContain(t("payments.credited.reverseNoneUnsettle"));
});

it("does not offer the confirmation until the consequence is known", async () => {
  vi.spyOn(api, "creditedTransactions").mockResolvedValue([transaction()]);
  vi.spyOn(api, "reversalPreflight").mockReturnValue(new Promise(() => {}));
  mount(<CreditedPanel slug="cup" reload={0} onChanged={vi.fn()} />);
  await settle();

  act(() => (host!.querySelector("td.col-actions button") as HTMLButtonElement).click());
  expect(host?.textContent).toContain(t("payments.credited.checking"));
  const confirm = host!.querySelector(".modal-actions .btn-primary") as HTMLButtonElement;
  expect(confirm.disabled).toBe(true);
});
