// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { ApiError, api, type RankedFencer, type Transaction } from "../api";
import i18n from "../i18n";
import LinkDialog from "./LinkDialog";

// The manual link dialog. It addresses a **person** first — a variable symbol
// is a shortcut, and about one payment in ten carries none or carries one that
// is wrong — with the detected candidates and a typed symbol kept as a second
// way in (spec name-assisted-matching, payments-console).

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const t = i18n.getFixedT(i18n.language);

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

function ranked(overrides: Partial<RankedFencer> = {}): RankedFencer {
  return {
    fencer_id: 1,
    name: "Jan Novák",
    registration_id: 11,
    vs: 2601001,
    outstanding_amount: "1200.00",
    score: 1,
    proposed: false,
    rejected: false,
    ...overrides,
  };
}

/** The roster the dialog fetches when it opens. Empty by default so the tests
 *  that predate it keep exercising the symbol path. */
function withRoster(fencers: RankedFencer[] = []) {
  return vi.spyOn(api, "transactionRoster").mockResolvedValue({
    transaction_id: 7,
    query: "za Novaka a Dvoraka",
    fencers,
  });
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

function render(
  tx = transaction(),
  handlers: { onLinked?: () => void; onClose?: () => void } = {},
) {
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

  // the roster is empty here, so a symbol the dialog cannot resolve locally is
  // sent as a symbol and the endpoint resolves it
  expect(link).toHaveBeenCalledWith("cup", 7, [2601001], []);
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
  expect(link).toHaveBeenCalledWith("cup", 7, [2601001, 2601002], []);
});

it("names an unrecognised VS and keeps the dialog open with the entry", async () => {
  vi.spyOn(api, "linkTransaction").mockRejectedValue(new ApiError(404, { unknown_vs: [2609999] }));
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

// ------------------------------------------------------- addressing a person

it("lists the whole roster ranked, with the strongest marked", async () => {
  withRoster([
    ranked({ fencer_id: 1, name: "Josef Vejda", registration_id: 11, proposed: true }),
    ranked({ fencer_id: 2, name: "Milan Diviš", registration_id: 12, score: 0.2 }),
  ]);
  render();
  await settle();

  const text = host?.textContent ?? "";
  expect(text).toContain("Josef Vejda");
  expect(text).toContain("Milan Diviš");
  expect(text).toContain(t("payments.link.strongest"));
});

it("links by choosing a person, with no symbol quoted", async () => {
  withRoster([ranked({ name: "Josef Vejda", registration_id: 11, vs: null })]);
  const link = vi.spyOn(api, "linkTransaction").mockResolvedValue({ rule_id: 1, applied: 1 });
  render();
  await settle();

  const box = host?.querySelector('input[type="checkbox"]') as HTMLInputElement;
  act(() => box.click());
  click(buttonNamed(t("payments.link.confirm")));
  await settle();

  // a registration with no symbol is addressed by id, which is the whole point
  expect(link).toHaveBeenCalledWith("cup", 7, [], [11]);
});

it("filters the roster as the organizer types", async () => {
  withRoster([
    ranked({ fencer_id: 1, name: "Josef Vejda", registration_id: 11 }),
    ranked({ fencer_id: 2, name: "Milan Diviš", registration_id: 12 }),
  ]);
  render();
  await settle();

  const search = [...(host?.querySelectorAll("input") ?? [])].find(
    (input) => (input as HTMLInputElement).placeholder === t("payments.link.search"),
  ) as HTMLInputElement;
  act(() => {
    // React tracks the input's value on the node, so assigning it directly is
    // ignored; the native setter is how a controlled input is driven in a test
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value")?.set;
    setter?.call(search, "diviš");
    search.dispatchEvent(new Event("input", { bubbles: true }));
  });

  expect(host?.textContent).toContain("Milan Diviš");
  expect(host?.textContent).not.toContain("Josef Vejda");
});

it("a symbol the roster knows resolves to that person", async () => {
  withRoster([ranked({ name: "Josef Vejda", registration_id: 11, vs: 2601001 })]);
  const link = vi.spyOn(api, "linkTransaction").mockResolvedValue({ rule_id: 1, applied: 1 });
  render();
  await settle();

  click(buttonNamed("2601001"));
  click(buttonNamed(t("payments.link.confirm")));
  await settle();

  // sent as the registration, not as the number: one kind of thing reaches the
  // endpoint wherever the dialog could tell
  expect(link).toHaveBeenCalledWith("cup", 7, [], [11]);
});

it("says nothing can be linked until something is chosen", async () => {
  withRoster([ranked()]);
  render();
  await settle();
  expect(buttonNamed(t("payments.link.confirm"))?.disabled).toBe(true);
});

// A tournament whose registrations the organizer keeps mints no variable
// symbols at all, so the symbol half of the dialog can resolve nothing: every
// number typed comes back `unknown_vs` (spec `tournament-mode`).

it("offers no symbol where the roster carries none", async () => {
  withRoster([
    ranked({ fencer_id: 1, name: "Josef Vejda", registration_id: 11, vs: null }),
    ranked({ fencer_id: 2, name: "Václav Pekárek", registration_id: 12, vs: null }),
  ]);
  render(transaction({ candidate_vs: [2601001] }));
  await settle();

  expect(host?.querySelector(".link-entry")).toBeNull();
  expect(buttonNamed(t("payments.link.add"))).toBeUndefined();
  expect(buttonNamed("2601001")).toBeUndefined();
  // the roster itself is untouched: choosing a person is the way in
  expect(host?.textContent).toContain("Václav Pekárek");
});

it("keeps the symbol where some registration carries one", async () => {
  withRoster([
    ranked({ fencer_id: 1, name: "Jan Novák", registration_id: 11, vs: 2601001 }),
    ranked({ fencer_id: 2, name: "Josef Vejda", registration_id: 12, vs: null }),
  ]);
  render(transaction({ candidate_vs: [] }));
  await settle();

  expect(host?.querySelector(".link-entry")).not.toBeNull();
});

it("keeps the symbol when the roster could not be read", async () => {
  // an empty roster proves nothing about symbols, and it is then the only way
  // in the organizer has left
  vi.spyOn(api, "transactionRoster").mockRejectedValue(new Error("boom"));
  render(transaction({ candidate_vs: [] }));
  await settle();

  expect(host?.querySelector(".link-entry")).not.toBeNull();
});
