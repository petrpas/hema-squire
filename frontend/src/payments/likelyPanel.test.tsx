// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";

import { type Transaction, api } from "../api";
import i18n from "../i18n";
import LikelyPanel from "./LikelyPanel";

// The proposals queue: payments the resolver read a fencer's name in, waiting
// for a person. Nothing here has been credited (spec name-assisted-matching).

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const t = i18n.getFixedT("cs");

let host: HTMLElement | null = null;

function mount(element: React.ReactElement) {
  host = document.createElement("div");
  document.body.append(host);
  act(() => createRoot(host!).render(element));
  return host;
}

afterEach(() => {
  host?.remove();
  host = null;
  vi.restoreAllMocks();
});

async function settle() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

function buttonNamed(text: string) {
  return [...(host?.querySelectorAll("button") ?? [])].find(
    (button) => button.textContent?.trim() === text,
  ) as HTMLButtonElement | undefined;
}

function proposal(overrides: Partial<Transaction> = {}): Transaction {
  return {
    id: 7,
    external_id: "1",
    source: "csv",
    date: "2026-08-12",
    amount_cents: 100000,
    currency: "CZK",
    vs: null,
    message: "NaDuel26: Josef Vejda - sabre",
    payer_name: "Milan Diviš",
    payer_account: null,
    status: "likely",
    status_reason: null,
    matched_registration_id: null,
    reinstate_available: false,
    candidate_vs: [],
    named_person: "Josef Vejda",
    proposed_fencer_id: 3,
    proposed_fencer_name: "Josef Vejda",
    last_evaluated_at: null,
    ...overrides,
  } as Transaction;
}

function render() {
  return mount(<LikelyPanel slug="cup" reload={0} onChanged={vi.fn()} />);
}

it("states the bank's own text beside the fencer proposed", async () => {
  vi.spyOn(api, "likelyTransactions").mockResolvedValue([proposal()]);
  render();
  await settle();

  const text = host?.textContent ?? "";
  // the evidence has to be in front of the eye that clicks
  expect(text).toContain("NaDuel26: Josef Vejda - sabre");
  expect(text).toContain("Milan Diviš");
  expect(text).toContain("Josef Vejda");
  expect(text).toContain(t("payments.likely.explain"));
});

it("confirming calls the endpoint and refreshes", async () => {
  vi.spyOn(api, "likelyTransactions").mockResolvedValue([proposal()]);
  const confirm = vi
    .spyOn(api, "confirmProposal")
    .mockResolvedValue({ rule_id: 1, applied: 1 });
  render();
  await settle();

  act(() => buttonNamed(t("payments.likely.confirm"))?.click());
  await settle();

  expect(confirm).toHaveBeenCalledWith("cup", 7);
});

it("rejecting calls the endpoint and refreshes", async () => {
  vi.spyOn(api, "likelyTransactions").mockResolvedValue([proposal()]);
  const reject = vi
    .spyOn(api, "rejectProposal")
    .mockResolvedValue(proposal({ status: "unmatched" }));
  render();
  await settle();

  act(() => buttonNamed(t("payments.likely.reject"))?.click());
  await settle();

  expect(reject).toHaveBeenCalledWith("cup", 7);
});

it("an empty queue collapses to its heading", async () => {
  vi.spyOn(api, "likelyTransactions").mockResolvedValue([]);
  render();
  await settle();

  expect(host?.textContent).toContain(t("payments.likely.title"));
  expect(host?.querySelector("tbody tr")).toBeNull();
});

it("offers no bulk confirm", async () => {
  // a confirmation flow that is always right trains the person not to read;
  // deliberately one row at a time (design, Risks)
  vi.spyOn(api, "likelyTransactions").mockResolvedValue([proposal(), proposal({ id: 8 })]);
  render();
  await settle();

  const confirms = [...(host?.querySelectorAll("button") ?? [])].filter(
    (button) => button.textContent?.trim() === t("payments.likely.confirm"),
  );
  expect(confirms).toHaveLength(2);
});
