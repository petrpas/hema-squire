// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";

import type { CreditedPayment, UncreditedPayment } from "../api";
import i18n from "../i18n";
import CreditedTable from "./CreditedTable";
import UncreditedTable from "./UncreditedTable";

// What the two tables say that the seven queues could not (spec
// `payments-console`, Credited payments are one table / Uncredited payments are
// one table).

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

afterEach(() => {
  host?.remove();
  host = null;
});

function rowTexts() {
  return [...(host?.querySelectorAll("tbody tr") ?? [])].map((tr) => tr.textContent ?? "");
}

let nextRegistrationId = 1;

function credit(fencer: string, amount: string, unsettles = false) {
  return {
    registration_id: nextRegistrationId++,
    fencer_name: fencer,
    vs: 2601001,
    amount,
    currency: "CZK" as const,
    unsettles,
  };
}

function creditedPayment(overrides: Partial<CreditedPayment> = {}): CreditedPayment {
  return {
    source_kind: "bank_transaction",
    source_id: 1,
    value_date: "2026-08-01",
    amount: "1000.00",
    currency: "CZK",
    payer_name: "Jan Novák",
    recorded_by: null,
    method: null,
    note: null,
    message: "startovne",
    origin: "auto_vs",
    credits: [credit("Jan Novák", "1000.00", true)],
    ...overrides,
  };
}

function uncreditedPayment(overrides: Partial<UncreditedPayment> = {}): UncreditedPayment {
  return {
    id: 1,
    external_id: "1",
    date: "2026-08-01",
    amount_cents: 100000,
    currency: "CZK",
    payer_name: "Klubový účet",
    message: "za dva",
    status: "unmatched",
    status_reason: null,
    disposition: "none",
    proposed_outstanding: null,
    paired_registrations: [],
    reinstate_available: false,
    settled_by_hand_reason: null,
    settled_by_recorded_payment: null,
    ...overrides,
  } as unknown as UncreditedPayment;
}

// --------------------------------------------------------------- the credited

it("names every fencer a payment credited, with their own share", () => {
  mount(
    <CreditedTable
      slug="cup"
      onChanged={vi.fn()}
      payments={[
        creditedPayment({
          amount: "3000.00",
          origin: "payment_link",
          credits: [
            credit("Adéla", "1000.00"),
            credit("Boris", "1000.00"),
            credit("Cyril", "1000.00"),
          ],
        }),
      ]}
    />,
  );

  const [row] = rowTexts();
  // one payment may cover several entries — that is what a pairing is — so the
  // row names all of them rather than the one the matcher resolved to
  expect(row).toContain("Adéla");
  expect(row).toContain("Boris");
  expect(row).toContain("Cyril");
  expect(host?.querySelectorAll(".credit-share")).toHaveLength(3);
});

it("states why each payment was credited", () => {
  mount(
    <CreditedTable
      slug="cup"
      onChanged={vi.fn()}
      payments={[
        creditedPayment({ origin: "auto_vs" }),
        creditedPayment({ source_id: 2, origin: "payment_link" }),
        creditedPayment({
          source_kind: "manual_payment",
          source_id: 3,
          origin: "recorded",
          payer_name: null,
          recorded_by: "org@example.com",
          message: null,
          note: "hotově u stolu",
        }),
      ]}
    />,
  );

  const rows = rowTexts();
  expect(rows[0]).toContain(t("payments.credited.origins.auto_vs"));
  expect(rows[1]).toContain(t("payments.credited.origins.payment_link"));
  // the hand-recorded half sits in the same table, naming who said so
  expect(rows[2]).toContain(t("payments.credited.origins.recorded"));
  expect(rows[2]).toContain("org@example.com");
});

// ------------------------------------------------------------- the uncredited

it("sorts by what is to be done, so like decisions sit together", () => {
  mount(
    <UncreditedTable
      slug="cup"
      onChanged={vi.fn()}
      payments={[
        uncreditedPayment({ id: 1, disposition: "none" }),
        uncreditedPayment({
          id: 2,
          disposition: "refused",
          status: "flagged",
          status_reason: "registration_paid",
        }),
        uncreditedPayment({
          id: 3,
          disposition: "proposal",
          proposed_fencer_name: "Josef Vejda",
          proposed_outstanding: "1000.00",
        }),
      ]}
    />,
  );

  const rows = rowTexts();
  expect(rows[0]).toContain("Josef Vejda");
  expect(rows[1]).toContain(t("payments.flagged.reasons.registration_paid"));
  expect(rows[2]).toContain("Klubový účet");
});

it("states what a proposed fencer owes, not only their name", () => {
  mount(
    <UncreditedTable
      slug="cup"
      onChanged={vi.fn()}
      payments={[
        uncreditedPayment({
          disposition: "proposal",
          proposed_fencer_name: "Josef Vejda",
          proposed_outstanding: "1000.00",
        }),
      ]}
    />,
  );

  // confirmed against a balance rather than against a name alone. The spaces
  // are normalized because the money formatter groups with a non-breaking one
  const stated = (rowTexts()[0] ?? "").replace(/\s/g, " ");
  expect(stated).toContain("owes 1 000 Kč");
});

it("names the pairing that credited nothing", () => {
  mount(
    <UncreditedTable
      slug="cup"
      onChanged={vi.fn()}
      payments={[
        uncreditedPayment({
          disposition: "paired_uncredited",
          status: "matched",
          paired_registrations: [{ registration_id: 7, fencer_name: "Jan Novák", vs: 2601001 }],
        }),
      ]}
    />,
  );

  // the case that used to read as done while its money sat on the account
  expect(rowTexts()[0]).toContain("Jan Novák");
});

it("offers pairing by hand on every row, and the verdicts only on a proposal", () => {
  mount(
    <UncreditedTable
      slug="cup"
      onChanged={vi.fn()}
      payments={[uncreditedPayment({ id: 1, disposition: "none" })]}
    />,
  );
  const titles = () =>
    [...(host?.querySelectorAll("button.row-action") ?? [])].map((button) =>
      button.getAttribute("title"),
    );

  expect(titles()).toContain(t("payments.unmatched.link"));
  expect(titles()).not.toContain(t("payments.uncredited.confirm"));
});

it("offers reinstate only where the server says the seat is there", () => {
  mount(
    <UncreditedTable
      slug="cup"
      onChanged={vi.fn()}
      payments={[
        uncreditedPayment({
          disposition: "refused",
          status: "flagged",
          status_reason: "expired_outside_grace",
          reinstate_available: true,
        }),
      ]}
    />,
  );

  const titles = [...(host?.querySelectorAll("button.row-action") ?? [])].map((button) =>
    button.getAttribute("title"),
  );
  expect(titles).toContain(t("payments.flagged.reinstate"));
  expect(titles).toContain(t("payments.flagged.markForRefund"));
});
