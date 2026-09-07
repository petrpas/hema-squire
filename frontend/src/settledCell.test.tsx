// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";

import type { SheetRow, TournamentFlags } from "./api";
import { BONED_PAYMENTS_COLUMNS, offeredPhases, PHASE_COLUMNS, paymentsBonedOut } from "./Console";
import i18n from "./i18n";
import SettledCell from "./SettledCell";

// Settled with nothing passing through Squire (spec payments, etl-console).
// The Payments phase is offered whichever way the tournament is run — what
// varies is its contents. This cell is the boned-out phase's whole content;
// where Squire collects, the same mark is a waiver offered on the state cell
// it changes (see `stateCell.test.tsx`), not in a column of its own.

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

function flags(overrides: Partial<TournamentFlags> = {}): TournamentFlags {
  return {
    feature_schedule: false,
    feature_payments: false,
    feature_teams: false,
    feature_extras: false,
    ...overrides,
  };
}

function row(overrides: Partial<SheetRow> = {}): SheetRow {
  return {
    id: "reg:1",
    vs: 2601001,
    paid: false,
    registration_id: 1,
    ...overrides,
  } as unknown as SheetRow;
}

// ------------------------------------------------------------- the phase

it("offers the payments phase whoever handles the payments", () => {
  expect(offeredPhases(flags())).toContain("payments");
  expect(offeredPhases(flags({ feature_payments: true }))).toContain("payments");
});

it("bones the phase out only where Squire collects nothing", () => {
  expect(paymentsBonedOut(flags())).toBe(true);
  expect(paymentsBonedOut(flags({ feature_payments: true }))).toBe(false);
});

it("gives the mark a column only where it is the phase's whole content", () => {
  // in the full phase it would be empty on almost every row, and the table is
  // already seven columns wide
  expect(PHASE_COLUMNS.payments).not.toContain("settled");
  expect(BONED_PAYMENTS_COLUMNS).toContain("settled");
});

it("the boned-out phase keeps what is owed beside the mark", () => {
  // hiding it would make "paid" look like the only truth about a row that
  // still owes its whole total
  expect(BONED_PAYMENTS_COLUMNS).toContain("outstanding");
  expect(BONED_PAYMENTS_COLUMNS).toContain("settled");
  // and none of the machinery's columns
  expect(BONED_PAYMENTS_COLUMNS).not.toContain("vs");
  expect(BONED_PAYMENTS_COLUMNS).not.toContain("expires_at");
});

// -------------------------------------------------------------- the cell

it("marks an unsettled registration", () => {
  const toggle = vi.fn().mockResolvedValue(undefined);
  mount(<SettledCell row={row()} onToggle={toggle} busy={false} />);

  const button = host?.querySelector("button") as HTMLButtonElement;
  expect(button.getAttribute("aria-pressed")).toBe("false");
  expect(host?.textContent).toContain(t("console.settled.no"));

  act(() => button.click());
  expect(toggle).toHaveBeenCalled();
});

it("unmarks a settled one", () => {
  mount(
    <SettledCell
      row={row({ paid: true, settled_by_hand: true })}
      onToggle={vi.fn().mockResolvedValue(undefined)}
      busy={false}
    />,
  );
  const button = host?.querySelector("button") as HTMLButtonElement;
  expect(button.getAttribute("aria-pressed")).toBe("true");
  expect(button.title).toBe(t("console.settled.unset"));
});

it("offers nothing on a row with no registration behind it", () => {
  // an imported row not yet issued cannot be settled, and an action that would
  // answer a refusal is worse than none
  const host = mount(
    <SettledCell
      row={row({ registration_id: null })}
      onToggle={vi.fn().mockResolvedValue(undefined)}
      busy={false}
    />,
  );
  expect(host.querySelector("button")).toBeNull();
});

it("offers the mark on a registration that carries no variable symbol", () => {
  // a registration on a tournament the organizer keeps has none: Squire never
  // told any payer a symbol, so reading its absence as "no registration" would
  // take the mark away from the tournaments it exists for
  const host = mount(
    <SettledCell
      row={row({ vs: null })}
      onToggle={vi.fn().mockResolvedValue(undefined)}
      busy={false}
    />,
  );
  expect(host.querySelector("button")).not.toBeNull();
});

it("does not fire while a mark is in flight", () => {
  const toggle = vi.fn().mockResolvedValue(undefined);
  mount(<SettledCell row={row()} onToggle={toggle} busy />);
  act(() => (host?.querySelector("button") as HTMLButtonElement).click());
  expect(toggle).not.toHaveBeenCalled();
});
