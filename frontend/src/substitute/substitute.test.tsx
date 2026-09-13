// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api, type NetChange, type SheetRow } from "../api";
import { CellDisplay, canSubstitute } from "../Console";
import i18n from "../i18n";
import ManualEditsRail, { entryText } from "../ManualEditsRail";
import SubstituteDialog from "./SubstituteDialog";

// A seat handed on (spec `fencer-substitution`): who may be named, what the
// dialog requires in each mode, and where the action is offered at all.

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const t = i18n.getFixedT(i18n.language);

function row(fields: Partial<SheetRow> = {}): SheetRow {
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
    email: null,
    ...fields,
  } as SheetRow;
}

let host: HTMLElement | null = null;

function mount(element: React.ReactElement) {
  host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  act(() => root.render(element));
  return host;
}

function open(fields: Partial<SheetRow> = {}, automatic = true) {
  return mount(
    <SubstituteDialog
      slug="cup"
      row={row(fields)}
      automatic={automatic}
      onSubstituted={() => {}}
      onClose={() => {}}
    />,
  );
}

function text() {
  return document.body.textContent ?? "";
}

function nameField(): HTMLInputElement {
  const label = [...document.querySelectorAll("label.form-field")].find((element) =>
    element.querySelector("span")?.textContent?.includes(t("column.name")),
  );
  return label?.querySelector("input") as HTMLInputElement;
}

function emailField(): HTMLInputElement {
  const label = [...document.querySelectorAll("label.form-field")].find((element) =>
    element.querySelector("span")?.textContent?.includes(t("substitute.email")),
  );
  return label?.querySelector("input") as HTMLInputElement;
}

function keepBox(): HTMLInputElement {
  return document.querySelector('label.checkbox-line input[type="checkbox"]') as HTMLInputElement;
}

function type(control: HTMLInputElement, value: string) {
  act(() => {
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
    setter?.call(control, value);
    control.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

function buttonNamed(label: string) {
  return [...document.querySelectorAll("button")].find((button) =>
    button.textContent?.includes(label),
  ) as HTMLButtonElement | undefined;
}

// a checkbox is toggled by a click, in jsdom as in a browser; setting `checked`
// by hand would leave React reading the value it already had
function click(control: HTMLElement | undefined) {
  act(() => void control?.dispatchEvent(new MouseEvent("click", { bubbles: true })));
}

async function settle() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

beforeEach(() => {
  vi.restoreAllMocks();
  // the HR picker asks for the nationality list as it mounts; the dialog is
  // what is under test here, not the index behind it
  vi.spyOn(api, "hrNationalities").mockResolvedValue([]);
});

afterEach(() => {
  host?.remove();
  host = null;
  for (const dialog of document.querySelectorAll("dialog")) dialog.remove();
});

describe("the address the seat carries", () => {
  it("offers the seat's current address to keep", () => {
    open({ email: "klub@example.com" });

    expect(text()).toContain(t("substitute.keepAddress", { address: "klub@example.com" }));
  });

  it("offers nothing to keep on a row that carries no address", () => {
    open({ email: null });

    expect(text()).not.toContain("klub@example.com");
    expect(text()).toContain(t("substitute.mailNoticeBlank"));
  });

  it("asks for a new address by default, the kept one being the exception", () => {
    open({ email: "klub@example.com" });

    // the field is the substitute's own address, empty and ready to type into;
    // keeping the seat's is a box under it, unticked
    expect(emailField().disabled).toBe(false);
    expect(emailField().value).toBe("");
    expect(keepBox().checked).toBe(false);
    expect(text()).toContain(t("substitute.mailNoticeBlank"));
  });

  it("takes the seat's address once the box is ticked", () => {
    open({ email: "klub@example.com" });

    click(keepBox());

    expect(emailField().disabled).toBe(true);
    expect(text()).toContain(t("substitute.mailNotice", { address: "klub@example.com" }));
  });

  it("says nothing about mail where the organizer keeps the registrations", () => {
    open({ email: "klub@example.com" }, false);

    expect(text()).not.toContain(t("substitute.mailNoticeBlank"));
    expect(text()).not.toContain(t("substitute.mailNotice", { address: "klub@example.com" }));
  });

  it("refuses an automatic tournament's substitution with no address at all", async () => {
    const call = vi.spyOn(api, "substituteFencer").mockResolvedValue({ id: 1 });
    open({ email: null });
    type(nameField(), "Petr Náhradník");

    click(buttonNamed(t("substitute.submit")));
    await settle();

    expect(call).not.toHaveBeenCalled();
    expect(text()).toContain(t("substitute.refusal.substitute_email_required"));
  });

  it("takes a substitution with no address where the organizer keeps the list", async () => {
    const call = vi.spyOn(api, "substituteFencer").mockResolvedValue({ id: 1 });
    open({ email: null }, false);
    type(nameField(), "Petr Náhradník");

    click(buttonNamed(t("substitute.submit")));
    await settle();

    expect(call).toHaveBeenCalledWith(
      "cup",
      "reg:1",
      expect.objectContaining({ name: "Petr Náhradník", email: null, hr_id: null }),
    );
  });

  it("sends the kept address as the seat's own", async () => {
    const call = vi.spyOn(api, "substituteFencer").mockResolvedValue({ id: 1 });
    open({ email: "klub@example.com" });
    type(nameField(), "Petr Náhradník");
    click(keepBox());

    click(buttonNamed(t("substitute.submit")));
    await settle();

    expect(call).toHaveBeenCalledWith(
      "cup",
      "reg:1",
      expect.objectContaining({ email: "klub@example.com" }),
    );
  });
});

describe("naming the substitute", () => {
  it("states whose seat is being handed on", () => {
    open();
    expect(text()).toContain(t("substitute.replacing", { name: "Jan Novák" }));
  });

  it("says a profile is optional", () => {
    open();
    expect(text()).toContain(t("substitute.profileOptional"));
  });

  it("shows the server's refusal against the reason it names", async () => {
    vi.spyOn(api, "substituteFencer").mockRejectedValue({
      detail: "substitute_already_registered",
    });
    open({ email: "jan@example.com" });
    type(nameField(), "Petr Náhradník");
    click(keepBox());

    click(buttonNamed(t("substitute.submit")));
    await settle();

    expect(text()).toContain(t("substitute.refusal.substitute_already_registered"));
  });
});

describe("where the action is offered", () => {
  it("is offered on a live row of the fencer list", () => {
    expect(canSubstitute(row(), "fencers")).toBe(true);
  });

  it("is offered nowhere else", () => {
    expect(canSubstitute(row(), "import")).toBe(false);
    expect(canSubstitute(row(), "payments")).toBe(false);
    expect(canSubstitute(row(), "matching")).toBe(false);
  });

  it("is not offered on a deleted or an absorbed row", () => {
    expect(canSubstitute(row({ _deleted: true }), "fencers")).toBe(false);
    expect(canSubstitute(row({ _merged_into: "imp:2" }), "fencers")).toBe(false);
  });
});

describe("the mark a substituted row carries", () => {
  function cell(fields: Partial<SheetRow>): string {
    return renderToStaticMarkup(
      <CellDisplay row={row(fields)} column="name" timezone="Europe/Prague" />,
    );
  }

  it("marks the row without striking it through", () => {
    const rendered = cell({ name: "Petr Náhradník", _substituted_for: "Jan Novák" });

    expect(rendered).toContain("Petr Náhradník");
    expect(rendered).toContain(t("marker.substituted"));
    expect(rendered).not.toContain("deleted");
  });

  it("names the fencer whose seat it was, read from the row", () => {
    // the name is disclosed in place, as a note is: the column belongs to the
    // person competing
    mount(
      <CellDisplay
        row={row({ name: "Petr Náhradník", _substituted_for: "Jan Novák" })}
        column="name"
        timezone="Europe/Prague"
      />,
    );

    click(host?.querySelector(".note-marker-button") as HTMLButtonElement);

    expect(text()).toContain(t("marker.substitutedFor", { name: "Jan Novák" }));
  });

  it("marks nothing on a row that never changed hands", () => {
    expect(cell({})).not.toContain("note-marker");
  });
});

describe("the substitution in the manual-edits log", () => {
  // A substitution is a rule like any other: it stands in the log as one line,
  // and removing it there returns the seat to the fencer it was taken from
  // (spec `edit-rules`, The substitution reads as a sentence in the log).
  function entry(): NetChange {
    return {
      phase: "fencers",
      target: "reg:1",
      field: "_substituted",
      before: "Jan Novák",
      after: "Petr Náhradník",
      rule_ids: [12],
      actor: "Petr Paščenko",
      at: "2026-09-13T18:41:00+00:00",
    };
  }

  it("reads as a sentence naming both fencers, in either language", () => {
    const line = (language: string) =>
      entryText(
        entry(),
        [row({ id: "reg:1", name: "Petr Náhradník" })],
        null,
        i18n.getFixedT(language) as never,
      );
    expect(line("cs")).toBe("#1 Petr Náhradník — místo Jan Novák nastupuje Petr Náhradník");
    expect(line("en")).toBe("#1 Petr Náhradník — Petr Náhradník takes Jan Novák's place");
  });

  it("offers to be withdrawn, carrying the rule that made it", () => {
    const withdrawn: number[][] = [];
    mount(
      <ManualEditsRail
        entries={[entry()]}
        rows={[row({ id: "reg:1", name: "Petr Náhradník" })]}
        timezone={null}
        onUndo={(ruleIds) => withdrawn.push(ruleIds)}
      />,
    );

    click(host?.querySelector("button.row-action") as HTMLButtonElement);

    expect(withdrawn).toEqual([[12]]);
  });
});
