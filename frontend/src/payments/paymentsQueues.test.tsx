// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { api, type ExpiredHolding, type PaymentLink } from "../api";
import i18n from "../i18n";
import SheetArea from "../SheetArea";
import ExpiredHoldingPanel from "./ExpiredHoldingPanel";
import PaymentLinksPanel from "./PaymentLinksPanel";
import QueueCard from "./QueueCard";

// The expired-holding and payment-links queues, and the shell all four draw
// themselves in (spec `payments-console`).

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

beforeEach(() => void vi.restoreAllMocks());
afterEach(() => {
  host?.remove();
  host = null;
});

function stranded(overrides: Partial<ExpiredHolding> = {}): ExpiredHolding {
  return {
    registration_id: 3,
    fencer_name: "Jan Novák",
    vs: 2601001,
    credited_amount: "600.00",
    credited_eur_amount: null,
    expired_at: "2026-08-20T10:00:00Z",
    ...overrides,
  };
}

function link(overrides: Partial<PaymentLink> = {}): PaymentLink {
  return {
    rule_id: 11,
    auto_created: false,
    fencers: ["Adéla Nová"],
    vs: [2601001],
    transaction: {
      id: 5,
      date: "2026-08-01",
      amount_cents: 200000,
      currency: "CZK",
      payer_name: "Klubový účet",
      message: "platba za dva",
    } as unknown as PaymentLink["transaction"],
    ...overrides,
  };
}

it("lists money stranded on an expired reservation", async () => {
  vi.spyOn(api, "expiredHolding").mockResolvedValue([stranded()]);
  mount(<ExpiredHoldingPanel slug="cup" reload={0} currency="CZK" />);
  await settle();

  expect(host?.textContent).toContain("Jan Novák");
  expect(host?.textContent).toContain("2601001");
  expect(host?.textContent).toContain("600");
});

it("collapses to its heading when nothing is stranded", async () => {
  vi.spyOn(api, "expiredHolding").mockResolvedValue([]);
  mount(<ExpiredHoldingPanel slug="cup" reload={0} currency="CZK" />);
  await settle();

  // the absence is stated by the heading and its zero; no table, no body, so
  // four empty queues do not push the fencer table down (design D1)
  expect(host?.querySelector(".rail-count")?.textContent).toBe("0");
  expect(host?.querySelector("table")).toBeNull();
});

it("reports its own failure without claiming the queue is empty", async () => {
  vi.spyOn(api, "expiredHolding").mockRejectedValue(new Error("boom"));
  mount(<ExpiredHoldingPanel slug="cup" reload={0} currency="CZK" />);
  await settle();

  expect(host?.querySelector(".login-error")?.textContent).toBe(t("payments.queue.failed"));
  expect(host?.querySelector("table")).toBeNull();
});

it("reloads when the console says the money moved", async () => {
  // a statement import lands, the Fio poll returns, the lifecycle runs: the
  // queue owns its own data, so without this the organizer sees the state from
  // before the import until they reload the page
  const holdings = vi.spyOn(api, "expiredHolding").mockResolvedValue([]);
  const view = (reload: number) => (
    <ExpiredHoldingPanel slug="cup" reload={reload} currency="CZK" />
  );
  host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  act(() => root.render(view(0)));
  await settle();
  expect(holdings).toHaveBeenCalledTimes(1);

  act(() => root.render(view(1)));
  await settle();

  expect(holdings).toHaveBeenCalledTimes(2);
});

it("marks an auto-created link apart from one made by hand", async () => {
  vi.spyOn(api, "paymentLinks").mockResolvedValue([
    link({ rule_id: 11, auto_created: true }),
    link({ rule_id: 12 }),
  ]);
  mount(<PaymentLinksPanel slug="cup" reload={0} onChanged={() => {}} />);
  await settle();

  const rows = [...(host?.querySelectorAll("tbody tr") ?? [])];
  expect(rows[0]!.textContent).toContain(t("payments.links.auto"));
  expect(rows[1]!.textContent).toContain(t("payments.links.manual"));
});

it("states the payment as the bank wrote it, beside the fencer it credits", async () => {
  // the queue's only action destroys a link, and nobody can aim that at the
  // right row from an external id and a symbol
  vi.spyOn(api, "paymentLinks").mockResolvedValue([link()]);
  mount(<PaymentLinksPanel slug="cup" reload={0} onChanged={() => {}} />);
  await settle();

  const row = host?.querySelector("tbody tr")?.textContent ?? "";
  expect(row).toContain("Klubový účet");
  expect(row).toContain("platba za dva");
  expect(row).toContain("Adéla Nová");
  expect(row).not.toContain("txn:");
});

it("names the fencer where the payer quoted no symbol", async () => {
  vi.spyOn(api, "paymentLinks").mockResolvedValue([link({ vs: [] })]);
  mount(<PaymentLinksPanel slug="cup" reload={0} onChanged={() => {}} />);
  await settle();

  expect(host?.querySelector("tbody tr")?.textContent).toContain("Adéla Nová");
});

it("keeps a link whose payment is gone, and says why it reads short", async () => {
  // the statement was cleared; the credit is still with the fencer until the
  // link itself is removed
  vi.spyOn(api, "paymentLinks").mockResolvedValue([link({ transaction: null })]);
  mount(<PaymentLinksPanel slug="cup" reload={0} onChanged={() => {}} />);
  await settle();

  expect(host?.querySelector("tbody tr")?.textContent).toContain("Adéla Nová");
  expect(host?.textContent).toContain(t("payments.links.orphaned"));
});

it("refetches after removing a link rather than assuming the outcome", async () => {
  const rules = vi.spyOn(api, "paymentLinks").mockResolvedValue([link()]);
  const remove = vi.spyOn(api, "deleteRule").mockResolvedValue(undefined);
  const onChanged = vi.fn();
  mount(<PaymentLinksPanel slug="cup" reload={0} onChanged={onChanged} />);
  await settle();
  expect(rules).toHaveBeenCalledTimes(1);

  act(() => void buttonNamed(t("payments.links.remove"))?.click());
  await settle();

  expect(remove).toHaveBeenCalledWith("cup", 11);
  // removal unapplies the link server-side; what that leaves is read back, not
  // guessed at
  expect(rules).toHaveBeenCalledTimes(2);
  expect(onChanged).toHaveBeenCalled();
});

it("shows no number while the count is not yet known", () => {
  mount(
    <QueueCard title="x" count={null} loading>
      <p>body</p>
    </QueueCard>,
  );
  expect(host?.querySelector(".rail-count")).toBeNull();
  expect(host?.textContent).not.toContain("body");
});

it("puts the phase's queues above the fencer table", () => {
  mount(
    <SheetArea
      phase="payments"
      queues={<div className="test-queue">queues</div>}
      rows={[]}
      visibleRows={[]}
      columns={["vs"]}
      activeRows={[]}
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

  const queues = host?.querySelector(".sheet-queues");
  const table = host?.querySelector(".sheet-scroll");
  expect(queues).not.toBeNull();
  // the exceptions first, the ledger below: the phase reads top to bottom in
  // that order (design D1)
  expect(queues?.compareDocumentPosition(table!)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
});

it("gives a phase without queues no room for them", () => {
  mount(
    <SheetArea
      phase="fencers"
      rows={[]}
      visibleRows={[]}
      columns={["vs"]}
      activeRows={[]}
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

  expect(host?.querySelector(".sheet-queues")).toBeNull();
});
