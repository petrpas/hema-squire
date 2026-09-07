// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { ApiError, api, type ManualPayment, type SheetRow } from "../api";
import i18n from "../i18n";
import { formatMoney } from "../money";
import SheetArea from "../SheetArea";
import RecordedPaymentsPanel from "./RecordedPaymentsPanel";
import RecordPaymentDialog from "./RecordPaymentDialog";

// Recording a payment Squire never saw, and the view that lists what was
// recorded (spec `payments-console`). The dialog opens from a registration's
// own row rather than a queue: the queues hold money looking for a
// registration, and this is the other way round.

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

function type(input: HTMLInputElement, value: string) {
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value")!.set!;
  act(() => {
    setter.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

beforeEach(() => void vi.restoreAllMocks());
afterEach(() => {
  host?.remove();
  host = null;
});

function payment(overrides: Partial<ManualPayment> = {}): ManualPayment {
  return {
    id: 7,
    registration_id: 3,
    fencer_name: "Jan Novák",
    amount: "1000.00",
    currency: "CZK",
    received_on: "2026-08-01",
    method: "cash",
    note: "u prezence",
    recorded_by: "Organizátor <org@example.com>",
    created_at: "2026-08-01T10:00:00Z",
    removal_unsettles: true,
    ...overrides,
  };
}

function row(overrides: Partial<SheetRow> = {}): SheetRow {
  return {
    id: "reg:3",
    name: "Jan Novák",
    vs: 2601001,
    paid: false,
    registration_id: 3,
    outstanding_amount: "1000.00",
    outstanding_currency: "CZK",
    ...overrides,
  } as unknown as SheetRow;
}

// ----------------------------------------------------------------- the view

it("lists what was recorded by hand", async () => {
  vi.spyOn(api, "manualPayments").mockResolvedValue([payment()]);
  mount(<RecordedPaymentsPanel slug="cup" reload={0} onChanged={vi.fn()} />);
  await settle();

  expect(host?.textContent).toContain("Jan Novák");
  // formatted as every other money figure in the console is — asked of the
  // formatter rather than spelled out, since the grouping separator is a
  // non-breaking space
  expect(host?.textContent).toContain(formatMoney("1000.00", "CZK"));
  expect(host?.textContent).toContain(t("payments.record.method.cash"));
  expect(host?.textContent).toContain("u prezence");
  expect(host?.textContent).toContain("org@example.com");
});

it("collapses to its heading when nothing was recorded", async () => {
  vi.spyOn(api, "manualPayments").mockResolvedValue([]);
  mount(<RecordedPaymentsPanel slug="cup" reload={0} onChanged={vi.fn()} />);
  await settle();

  expect(host?.textContent).toContain(t("payments.recorded.title"));
  expect(host?.querySelector("tbody tr")).toBeNull();
});

it("reports its own failure", async () => {
  vi.spyOn(api, "manualPayments").mockRejectedValue(new Error("down"));
  mount(<RecordedPaymentsPanel slug="cup" reload={0} onChanged={vi.fn()} />);
  await settle();

  expect(host?.textContent).toContain(t("payments.queue.failed"));
});

it("says what removal will do before it is confirmed", async () => {
  vi.spyOn(api, "manualPayments").mockResolvedValue([payment()]);
  const remove = vi.spyOn(api, "removeManualPayment").mockResolvedValue(payment());
  const changed = vi.fn();
  mount(<RecordedPaymentsPanel slug="cup" reload={0} onChanged={changed} />);
  await settle();

  act(() => (host?.querySelector("td.col-actions button") as HTMLButtonElement).click());
  // the reversal may unsettle a row the roster already shows as paid, and that
  // is not a consequence to discover afterwards
  expect(host?.textContent).toContain(t("payments.recorded.removeUnsettles"));
  expect(remove).not.toHaveBeenCalled();

  act(() => (host?.querySelector(".modal-actions .btn-primary") as HTMLButtonElement).click());
  await settle();
  expect(remove).toHaveBeenCalledWith("cup", 7);
  expect(changed).toHaveBeenCalled();
});

it("does not warn about unsettling where removal would not", async () => {
  vi.spyOn(api, "manualPayments").mockResolvedValue([payment({ removal_unsettles: false })]);
  mount(<RecordedPaymentsPanel slug="cup" reload={0} onChanged={vi.fn()} />);
  await settle();

  act(() => (host?.querySelector("td.col-actions button") as HTMLButtonElement).click());
  expect(host?.textContent).not.toContain(t("payments.recorded.removeUnsettles"));
});

// --------------------------------------------------------------- the dialog

it("states the balance before anything is typed, and offers it", () => {
  mount(
    <RecordPaymentDialog
      slug="cup"
      row={row()}
      currency="CZK"
      eurOffered={false}
      onRecorded={vi.fn()}
      onClose={vi.fn()}
    />,
  );

  expect(host?.textContent).toContain(formatMoney("1000.00", "CZK"));
  const amount = host?.querySelector(".form-field input") as HTMLInputElement;
  expect(amount.value).toBe("1000.00");
});

it("records what was typed", async () => {
  const record = vi.spyOn(api, "recordManualPayment").mockResolvedValue(payment());
  const recorded = vi.fn();
  const close = vi.fn();
  mount(
    <RecordPaymentDialog
      slug="cup"
      row={row()}
      currency="CZK"
      eurOffered={false}
      onRecorded={recorded}
      onClose={close}
    />,
  );

  const amount = host?.querySelector(".form-field input") as HTMLInputElement;
  type(amount, "500,00");
  act(() => buttonNamed(t("payments.record.confirm"))!.click());
  await settle();

  expect(record).toHaveBeenCalledWith(
    "cup",
    expect.objectContaining({
      registration_id: 3,
      // a comma is how the amount is typed here and a dot is what the API
      // takes
      amount: "500.00",
      currency: "CZK",
      method: "cash",
    }),
  );
  expect(recorded).toHaveBeenCalled();
  expect(close).toHaveBeenCalled();
});

it("keeps what was typed when the endpoint refuses", async () => {
  vi.spyOn(api, "recordManualPayment").mockRejectedValue(
    new ApiError(409, "currency_not_accepted"),
  );
  const close = vi.fn();
  mount(
    <RecordPaymentDialog
      slug="cup"
      row={row()}
      currency="CZK"
      eurOffered={false}
      onRecorded={vi.fn()}
      onClose={close}
    />,
  );

  const amount = host?.querySelector(".form-field input") as HTMLInputElement;
  type(amount, "700");
  act(() => buttonNamed(t("payments.record.confirm"))!.click());
  await settle();

  expect(host?.textContent).toContain(t("payments.record.error.currency_not_accepted"));
  expect((host?.querySelector(".form-field input") as HTMLInputElement).value).toBe("700");
  expect(close).not.toHaveBeenCalled();
});

it("offers the second currency only where the tournament prices in one", () => {
  mount(
    <RecordPaymentDialog
      slug="cup"
      row={row()}
      currency="CZK"
      eurOffered={false}
      onRecorded={vi.fn()}
      onClose={vi.fn()}
    />,
  );
  // the method select is always there; the currency one is not
  expect(host?.querySelectorAll("select").length).toBe(1);

  host?.remove();
  mount(
    <RecordPaymentDialog
      slug="cup"
      row={row()}
      currency="CZK"
      eurOffered
      onRecorded={vi.fn()}
      onClose={vi.fn()}
    />,
  );
  // the currency select, plus the method one that is always there
  expect(host?.querySelectorAll("select").length).toBe(2);
});

// ---------------------------------------- where the record action sits

it("puts recording a payment at the end of the row, not in a column", () => {
  // the table already carries seven columns on this phase; an action belongs
  // with the other row actions rather than widening it further
  const record = vi.fn();
  const sheetRow = row();
  mount(
    <SheetArea
      phase="payments"
      rows={[sheetRow]}
      visibleRows={[sheetRow]}
      columns={["name", "vs", "state"]}
      activeRows={[sheetRow]}
      paidCount={0}
      revision={0}
      timezone={null}
      currency={null}
      error={false}
      refresh={() => {}}
      onEdit={() => {}}
      onValidate={() => null}
      onDelete={() => {}}
      onRestore={() => {}}
      onRatify={() => {}}
      onSearch={() => {}}
      collects
      onToggleSettled={async () => {}}
      onRecordPayment={record}
    />,
  );

  const action = host?.querySelector("td.col-actions button") as HTMLButtonElement;
  expect(action).not.toBeNull();
  expect(action.title).toBe(t("payments.record.action"));
  act(() => action.click());
  expect(record).toHaveBeenCalledWith(sheetRow);
});

it("offers no end-of-row action where no payment can be recorded", () => {
  const sheetRow = row();
  mount(
    <SheetArea
      phase="payments"
      rows={[sheetRow]}
      visibleRows={[sheetRow]}
      columns={["name", "vs", "state"]}
      activeRows={[sheetRow]}
      paidCount={0}
      revision={0}
      timezone={null}
      currency={null}
      error={false}
      refresh={() => {}}
      onEdit={() => {}}
      onValidate={() => null}
      onDelete={() => {}}
      onRestore={() => {}}
      onRatify={() => {}}
      onSearch={() => {}}
    />,
  );
  expect(host?.querySelector("td.col-actions")).toBeNull();
});
