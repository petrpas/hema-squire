// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";

import type { SheetRow } from "./api";
import i18n from "./i18n";
import StateCell from "./StateCell";

// The waiver on a tournament Squire collects for. It has no column of its own:
// it changes the state cell, from reserved to paid with no money behind it, so
// it is offered on the state it sets (spec payments, etl-console).

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const t = i18n.getFixedT(i18n.language);

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

function row(overrides: Partial<SheetRow> = {}): SheetRow {
  return {
    id: "reg:1",
    name: "Jan Novák",
    vs: 2601001,
    state: "reserved",
    paid: false,
    registration_id: 1,
    ...overrides,
  } as unknown as SheetRow;
}

function type(input: HTMLInputElement, value: string) {
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value")!.set!;
  act(() => {
    setter.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

it("states the registration's state in the reader's language", () => {
  // the stored value is an enum; the table was printing "reserved" into Czech
  mount(<StateCell row={row()} onToggle={vi.fn().mockResolvedValue(undefined)} busy={false} />);
  expect(host?.textContent).toContain(t("registration.state.reserved"));
  expect(host?.textContent).not.toContain("reserved");
});

it("asks for a reason before waiving a reserved registration", () => {
  const toggle = vi.fn().mockResolvedValue(undefined);
  mount(<StateCell row={row()} onToggle={toggle} busy={false} />);

  act(() => (host!.querySelector("button.state-cell") as HTMLButtonElement).click());
  expect(toggle).not.toHaveBeenCalled();

  const confirm = host?.querySelector(".modal-actions .btn-primary") as HTMLButtonElement;
  expect(confirm.disabled).toBe(true);
});

it("waives it once a reason is given", () => {
  const toggle = vi.fn().mockResolvedValue(undefined);
  mount(<StateCell row={row()} onToggle={toggle} busy={false} />);
  act(() => (host!.querySelector("button.state-cell") as HTMLButtonElement).click());

  type(host!.querySelector(".modal input") as HTMLInputElement, "volná účast");
  act(() => (host!.querySelector(".modal-actions .btn-primary") as HTMLButtonElement).click());

  expect(toggle).toHaveBeenCalledWith(expect.anything(), "volná účast");
});

it("unwaives without asking why", () => {
  // asking why someone is being un-waived would be a question about nothing
  const toggle = vi.fn().mockResolvedValue(undefined);
  mount(
    <StateCell
      row={row({ state: "paid", paid: true, settled_by_hand: true })}
      onToggle={toggle}
      busy={false}
    />,
  );
  act(() => (host!.querySelector("button.state-cell") as HTMLButtonElement).click());

  expect(toggle).toHaveBeenCalled();
  expect(host!.querySelector(".modal")).toBeNull();
});

it("shows the waiver's reason on a waived row", () => {
  mount(
    <StateCell
      row={row({
        state: "paid",
        paid: true,
        settled_by_hand: true,
        settled_by_hand_reason: "sponzor",
      })}
      onToggle={vi.fn().mockResolvedValue(undefined)}
      busy={false}
    />,
  );
  expect((host!.querySelector("button.state-cell") as HTMLButtonElement).title).toBe("sponzor");
});

it("offers nothing on a registration the money settled", () => {
  // unsetting a mark nobody made would return it to reserved and strand its
  // credit; the endpoint refuses it and the cell does not offer it
  mount(
    <StateCell
      row={row({ state: "paid", paid: true, settled_by_hand: false })}
      onToggle={vi.fn().mockResolvedValue(undefined)}
      busy={false}
    />,
  );
  expect(host!.querySelector("button")).toBeNull();
  expect(host?.textContent).toContain(t("registration.state.paid"));
});

it("offers nothing on a state the lifecycle or the fencer chose", () => {
  for (const state of ["expired", "cancelled"]) {
    mount(
      <StateCell
        row={row({ state })}
        onToggle={vi.fn().mockResolvedValue(undefined)}
        busy={false}
      />,
    );
    expect(host!.querySelector("button")).toBeNull();
    host?.remove();
  }
});

it("offers nothing on a row with no registration behind it", () => {
  mount(
    <StateCell
      row={row({ registration_id: null, state: "imported" })}
      onToggle={vi.fn().mockResolvedValue(undefined)}
      busy={false}
    />,
  );
  expect(host!.querySelector("button")).toBeNull();
});

it("does not fire while a mark is in flight", () => {
  const toggle = vi.fn().mockResolvedValue(undefined);
  mount(
    <StateCell
      row={row({ state: "paid", paid: true, settled_by_hand: true })}
      onToggle={toggle}
      busy
    />,
  );
  act(() => (host!.querySelector("button.state-cell") as HTMLButtonElement).click());
  expect(toggle).not.toHaveBeenCalled();
});

it("keeps the dialog open and states a refusal", async () => {
  // the defect this replaced: the dialog closed on a 409, leaving a row that
  // had not changed and nothing at all saying why
  const { ApiError } = await import("./api");
  const toggle = vi.fn().mockRejectedValue(new ApiError(409, "not_settled_by_hand"));
  mount(<StateCell row={row()} onToggle={toggle} busy={false} />);
  act(() => (host!.querySelector("button.state-cell") as HTMLButtonElement).click());
  type(host!.querySelector(".modal input") as HTMLInputElement, "volná účast");

  await act(async () => {
    (host!.querySelector(".modal-actions .btn-primary") as HTMLButtonElement).click();
    await Promise.resolve();
  });

  expect(host!.querySelector(".modal")).not.toBeNull();
  expect(host?.textContent).toContain(t("console.waiver.error.not_settled_by_hand"));
  // and what was typed survives, so the organizer is not made to type it again
  expect((host!.querySelector(".modal input") as HTMLInputElement).value).toBe("volná účast");
});
