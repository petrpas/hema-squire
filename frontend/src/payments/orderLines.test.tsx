// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";

import type { OrderLine, OrderLines } from "../api";
import i18n from "../i18n";
import ContentsCell from "./ContentsCell";
import OrderLineRows from "./OrderLineRows";
import { orderSummary } from "./orderLines";

// What an order holds, summarised and unfolded (spec payments-console, The
// registration table states what each order holds / Every order unfolds into
// its priced lines / Queued placements are shown and not counted / A
// difference to the issued total is stated, not hidden).

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const cs = i18n.getFixedT("cs");

function line(overrides: Partial<OrderLine>): OrderLine {
  return {
    kind: "discipline",
    label: null,
    discipline_slug: null,
    qty: 1,
    unit_price: 0,
    amount: 0,
    queued: false,
    ...overrides,
  };
}

const teamA = line({ kind: "team", label: "Hema Praha A", discipline_slug: "SA", amount: 1200 });
const teamB = line({ kind: "team", label: "Hema Praha B", discipline_slug: "SA", amount: 1200 });
const longsword = line({ kind: "discipline", discipline_slug: "LS", amount: 800 });
const rentals = line({ kind: "item", label: "Zápůjčka", qty: 3, unit_price: 150, amount: 450 });

it("names a single team", () => {
  expect(orderSummary([teamA], cs)).toBe("Hema Praha A");
});

it("counts teams and pieces in a mixed order", () => {
  expect(orderSummary([teamA, teamB, longsword, rentals], cs)).toBe("2 týmy · LS · 3 položky");
});

it("leaves a queued team out of the summary", () => {
  expect(orderSummary([teamA, { ...teamB, queued: true }], cs)).toBe("Hema Praha A");
});

it("states nothing for an order that bills nothing", () => {
  expect(orderSummary([{ ...longsword, queued: true }], cs)).toBeNull();
});

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

const COLUMNS = ["name", "club", "contents", "vs", "total_amount", "outstanding", "state"];

function unfold(order: OrderLines, issued: number | null) {
  return mount(
    <table>
      <tbody>
        <OrderLineRows order={order} issued={issued} columns={COLUMNS} trailing={1} />
      </tbody>
    </table>,
  );
}

it("marks a queued line and counts it nowhere", () => {
  const order: OrderLines = {
    registration_id: 1,
    currency: "CZK",
    lines: [teamA, { ...teamB, queued: true }],
  };
  const table = unfold(order, 1200);
  const rows = [...table.querySelectorAll("tr")];
  expect(rows).toHaveLength(2);
  expect(rows[1]?.className).toContain("order-line-queued");
  expect(rows[0]?.className).not.toContain("order-line-queued");
});

it("states the difference only where the lines miss the issued total", () => {
  const order: OrderLines = { registration_id: 1, currency: "CZK", lines: [longsword, rentals] };
  expect(unfold(order, 1250).querySelectorAll("tr")).toHaveLength(2);
  act(() => host?.remove());

  const rows = [...unfold(order, 1100).querySelectorAll("tr")];
  expect(rows).toHaveLength(3);
  expect(rows[2]?.textContent).toContain(i18n.t("payments.order.difference"));
});

it("puts each amount under the amount column", () => {
  const order: OrderLines = { registration_id: 1, currency: "CZK", lines: [longsword] };
  const cells = [...unfold(order, 800).querySelectorAll("td")];
  // gutter, number, the words spanning the four columns before the amount,
  // the amount, and the rest with the actions
  expect(cells[2]?.getAttribute("colspan")).toBe("4");
  expect(cells[3]?.textContent).toContain("800");
});

it("states an EUR tournament's lines in EUR", () => {
  const order: OrderLines = { registration_id: 1, currency: "EUR", lines: [longsword] };
  expect(unfold(order, 800).textContent).toContain("€");
});

it("offers every order with lines to unfold, a single line included", () => {
  const onToggle = vi.fn();
  const cell = mount(
    <ContentsCell
      order={{ registration_id: 1, currency: "CZK", lines: [teamA] }}
      open={false}
      onToggle={onToggle}
    />,
  );
  const toggle = cell.querySelector("button");
  expect(toggle?.getAttribute("aria-expanded")).toBe("false");
  act(() => toggle?.click());
  expect(onToggle).toHaveBeenCalled();
});

it("offers nothing to unfold where there are no lines", () => {
  const cell = mount(<ContentsCell order={undefined} open={false} onToggle={vi.fn()} />);
  expect(cell.querySelector("button")).toBeNull();
  expect(cell.textContent).toBe("—");
});

it("closes the order with a rule under its last line", () => {
  const order: OrderLines = { registration_id: 1, currency: "CZK", lines: [longsword, rentals] };
  const rows = [...unfold(order, 1250).querySelectorAll("tr")];
  expect(rows.map((row) => row.classList.contains("order-line-last"))).toEqual([false, true]);
  act(() => host?.remove());

  // where a difference is stated, it is the last line
  const withDifference = [...unfold(order, 1100).querySelectorAll("tr")];
  expect(withDifference[withDifference.length - 1]?.classList.contains("order-line-last")).toBe(
    true,
  );
  expect(withDifference[1]?.classList.contains("order-line-last")).toBe(false);
});
