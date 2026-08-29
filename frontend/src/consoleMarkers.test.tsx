// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";

import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";

import type { SheetRow } from "./api";
import { CellDisplay, rowNumber } from "./Console";
import NoteMarker from "./NoteMarker";

// The note and problem markers, and the number the leftmost column shows
// (spec `etl-console`, Note and problem markers / Fixed fencer number).

// React only treats updates as batched test work when it is told it is under
// test; without this every act() call warns.
(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

function row(fields: Partial<SheetRow>): SheetRow {
  return {
    id: "reg:1",
    number: 1,
    name: "Jan Novák",
    nationality: null,
    club: null,
    hr_id: null,
    disciplines: [],
    substitute_for: [],
    state: "reserved",
    vs: null,
    paid: false,
    registered_at: null,
    total_amount: null,
    problems: null,
    expires_at: null,
    paid_at: null,
    weapon_rentals: [],
    afterparty: false,
    aftersparring: false,
    notes: null,
    ...fields,
  } as SheetRow;
}

function cell(column: string, fields: Partial<SheetRow>): string {
  return renderToStaticMarkup(
    <CellDisplay row={row(fields)} column={column} timezone="Europe/Prague" />,
  );
}

describe("note and problem cells", () => {
  it("show nothing at all on a row that carries none", () => {
    expect(cell("notes", {})).toBe("");
    expect(cell("problems", {})).toBe("");
    expect(cell("notes", { notes: "   " })).toBe("");
  });

  it("show a marker, not the text, where there is something to read", () => {
    const note = cell("notes", { notes: "dorazím později" });
    expect(note).toContain("[i]");
    expect(note).not.toContain("dorazím později");

    const problem = cell("problems", { problems: "afterparty answer ambiguous" });
    expect(problem).toContain("[!]");
    expect(problem).not.toContain("ambiguous");
  });
});

let host: HTMLElement | null = null;

/** Mounts a marker into the document and returns its button and a reader for
 *  whatever the panel currently discloses. The project renders components with
 *  React itself rather than a testing library, so events are dispatched the way
 *  a browser dispatches them. */
function mount(element: React.ReactElement) {
  host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  act(() => root.render(element));
  const button = host.querySelector("button") as HTMLButtonElement;
  return {
    button,
    click: () => act(() => void button.dispatchEvent(new MouseEvent("click", { bubbles: true }))),
    panel: () => host?.querySelector(".note-marker-panel"),
    container: () => host as HTMLElement,
  };
}

afterEach(() => {
  host?.remove();
  host = null;
});

describe("the marker's disclosure", () => {
  it("opens on activation and closes on Escape", () => {
    const marker = mount(<NoteMarker kind="note" text="dorazím později" />);
    expect(marker.panel()).toBeNull();

    marker.click();
    expect(marker.panel()?.textContent).toContain("dorazím později");
    expect(marker.button.getAttribute("aria-expanded")).toBe("true");

    act(() => {
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    });
    expect(marker.panel()).toBeNull();
  });

  it("closes on a click outside it", () => {
    const marker = mount(<NoteMarker kind="problem" text="discipline ambiguous" />);
    marker.click();
    expect(marker.panel()?.textContent).toContain("discipline ambiguous");

    act(() => {
      document.body.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    });
    expect(marker.panel()).toBeNull();
  });

  it("discloses the text as text, offering nothing to edit it with", () => {
    const marker = mount(<NoteMarker kind="note" text="dorazím později" />);
    marker.click();
    const container = marker.container();
    expect(container.querySelector("input")).toBeNull();
    expect(container.querySelector("textarea")).toBeNull();
    expect(container.querySelector("[contenteditable]")).toBeNull();
  });
});

describe("the leftmost number", () => {
  it("is the fencer's fixed number on the fencer list, whatever the row's place", () => {
    expect(rowNumber(row({ number: 31 }), "fencers")).toBe("31");
    expect(rowNumber(row({ number: 31 }), "matching")).toBe("31");
  });

  it("is the file's own line on Import", () => {
    const imported = row({
      id: "imp:c1aa",
      number: 31,
      _source: { file: "regs.csv", row: 7 },
    });
    expect(rowNumber(imported, "import")).toBe("7");
    expect(rowNumber(imported, "fencers")).toBe("31");
  });

  it("shows a dash rather than a position where no number was allocated", () => {
    expect(rowNumber(row({ number: null }), "fencers")).toBe("—");
  });
});
