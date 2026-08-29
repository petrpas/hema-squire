// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, type Discipline, type ExtraItem, type TournamentDetail, api } from "../api";
import i18n from "../i18n";
import ManualEntryDialog from "./ManualEntryDialog";
import ManualEntryPanel from "./ManualEntryPanel";
import { nowInZone } from "./nowInZone";

// The manual entry dialog: built from the tournament's own structure, and
// strict about what it accepts (spec `etl-console`, Manual entry fields follow
// the tournament's structure / Strict validation of a manual entry).

const t = i18n.getFixedT("cs");

function discipline(slug: string, name: string, kind: "individual" | "team"): Discipline {
  return { slug, name, kind, ordinal: 0, weapon: "LS", gender: "", material: "" } as Discipline;
}

function item(id: number, name: string, category: string): ExtraItem {
  return { id, name, category, price: 100, max_qty: 1 } as ExtraItem;
}

function detail(overrides: Partial<TournamentDetail> = {}): TournamentDetail {
  return {
    slug: "cup",
    timezone: "Europe/Prague",
    disciplines: [discipline("LS", "Longsword", "individual")],
    extra_items: [],
    ...overrides,
  } as TournamentDetail;
}

let host: HTMLElement | null = null;

function mount(element: React.ReactElement) {
  host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  act(() => root.render(element));
  return host;
}

function fields() {
  return [...(host?.querySelectorAll("label.form-field") ?? [])] as HTMLLabelElement[];
}

function field(label: string): HTMLInputElement | HTMLTextAreaElement {
  const found = fields().find((element) =>
    element.querySelector("span")?.textContent?.includes(label),
  );
  return found?.querySelector("input, textarea") as HTMLInputElement;
}

function type(control: HTMLInputElement | HTMLTextAreaElement, value: string) {
  act(() => {
    const setter = Object.getOwnPropertyDescriptor(
      control instanceof HTMLTextAreaElement
        ? HTMLTextAreaElement.prototype
        : HTMLInputElement.prototype,
      "value",
    )?.set;
    setter?.call(control, value);
    control.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

function check(label: string) {
  const chip = [...(host?.querySelectorAll("label.checkbox-chip") ?? [])].find((element) =>
    element.textContent?.includes(label),
  );
  const box = chip?.querySelector("input") as HTMLInputElement;
  // a click is what toggles a checkbox, in jsdom as in a browser; setting
  // `checked` by hand would leave React reading the value it already had
  act(() => void box.dispatchEvent(new MouseEvent("click", { bubbles: true })));
}

function buttonNamed(text: string) {
  return [...(host?.querySelectorAll("button") ?? [])].find((button) =>
    button.textContent?.includes(text),
  ) as HTMLButtonElement | undefined;
}

function click(button: HTMLButtonElement | undefined) {
  act(() => void button?.dispatchEvent(new MouseEvent("click", { bubbles: true })));
}

async function settle() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

beforeEach(() => {
  vi.restoreAllMocks();
});

afterEach(() => {
  host?.remove();
  host = null;
});

describe("the dialog's fields", () => {
  it("offers the tournament's individual disciplines and not its team ones", () => {
    mount(
      <ManualEntryDialog
        detail={detail({
          disciplines: [
            discipline("LS", "Longsword", "individual"),
            discipline("TEAM", "Team longsword", "team"),
          ],
        })}
        slug="cup"
        onEntered={() => {}}
        onClose={() => {}}
      />,
    );

    const text = host?.textContent ?? "";
    expect(text).toContain("Longsword");
    expect(text).not.toContain("Team longsword");
  });

  it("asks nothing about an afterparty the tournament does not hold, and offers only lent items", () => {
    mount(
      <ManualEntryDialog
        detail={detail({ extra_items: [item(1, "T-shirt", "merch")] })}
        slug="cup"
        onEntered={() => {}}
        onClose={() => {}}
      />,
    );

    const text = host?.textContent ?? "";
    expect(text).not.toContain(t("column.afterparty"));
    expect(text).not.toContain("T-shirt");
    expect(text).not.toContain(t("column.weapon_rentals"));
  });

  it("offers the afterparty and the lent items when the tournament has them", () => {
    mount(
      <ManualEntryDialog
        detail={detail({
          extra_items: [item(1, "mask", "rental"), item(2, "Saturday party", "afterparty")],
        })}
        slug="cup"
        onEntered={() => {}}
        onClose={() => {}}
      />,
    );

    const text = host?.textContent ?? "";
    expect(text).toContain("mask");
    expect(text).toContain(t("column.afterparty"));
  });

  it("opens on the present moment in the tournament's own zone", () => {
    mount(
      <ManualEntryDialog
        detail={detail({ timezone: "Pacific/Auckland" })}
        slug="cup"
        onEntered={() => {}}
        onClose={() => {}}
      />,
    );

    const moment = field(t("column.registered_at")) as HTMLInputElement;
    expect(moment.value).toBe(nowInZone("Pacific/Auckland"));
  });
});

describe("what the dialog accepts", () => {
  it("sends the entry the organizer filled in", async () => {
    const create = vi.spyOn(api, "createManualRow").mockResolvedValue({} as never);
    const onEntered = vi.fn();
    const onClose = vi.fn();
    mount(
      <ManualEntryDialog
        detail={detail({ extra_items: [item(1, "mask", "rental")] })}
        slug="cup"
        onEntered={onEntered}
        onClose={onClose}
      />,
    );

    type(field(t("column.name")), "Jan Novák");
    type(field(t("column.club")), "Twerchhau");
    check("Longsword");
    check("mask");
    click(buttonNamed(t("manualEntry.submit")));
    await settle();

    expect(create).toHaveBeenCalledWith(
      "cup",
      expect.objectContaining({
        name: "Jan Novák",
        club: "Twerchhau",
        disciplines: ["LS"],
        weapon_rentals: ["mask"],
      }),
    );
    expect(onEntered).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });

  it("refuses a blank name and adds nothing", async () => {
    const create = vi.spyOn(api, "createManualRow");
    mount(
      <ManualEntryDialog detail={detail()} slug="cup" onEntered={() => {}} onClose={() => {}} />,
    );

    check("Longsword");
    click(buttonNamed(t("manualEntry.submit")));
    await settle();

    expect(create).not.toHaveBeenCalled();
    expect(field(t("column.name")).getAttribute("aria-invalid")).toBe("true");
  });

  it("refuses an entry with no discipline, saying so", async () => {
    const create = vi.spyOn(api, "createManualRow");
    mount(
      <ManualEntryDialog detail={detail()} slug="cup" onEntered={() => {}} onClose={() => {}} />,
    );

    type(field(t("column.name")), "Jan Novák");
    click(buttonNamed(t("manualEntry.submit")));
    await settle();

    expect(create).not.toHaveBeenCalled();
    expect(host?.textContent).toContain(t("manualEntry.refusal.no_disciplines"));
  });

  it("keeps the rest of the form when the server refuses one field", async () => {
    vi.spyOn(api, "createManualRow").mockRejectedValue(
      new ApiError(422, { errors: [{ field: "email", code: "bad_email", params: {} }] }),
    );
    mount(
      <ManualEntryDialog detail={detail()} slug="cup" onEntered={() => {}} onClose={() => {}} />,
    );

    type(field(t("column.name")), "Jan Novák");
    type(field(t("column.club")), "Twerchhau");
    type(field(t("manualEntry.email")), "not-an-address");
    check("Longsword");
    click(buttonNamed(t("manualEntry.submit")));
    await settle();

    expect(field(t("manualEntry.email")).getAttribute("aria-invalid")).toBe("true");
    expect((field(t("column.club")) as HTMLInputElement).value).toBe("Twerchhau");
    expect((field(t("column.name")) as HTMLInputElement).value).toBe("Jan Novák");
  });
});

describe("the panel", () => {
  it("offers the action once the tournament's structure has arrived", () => {
    mount(<ManualEntryPanel detail={null} slug="cup" onEntered={() => {}} />);
    expect(buttonNamed(t("manualEntry.open"))?.disabled).toBe(true);

    host?.remove();
    mount(<ManualEntryPanel detail={detail()} slug="cup" onEntered={() => {}} />);
    expect(buttonNamed(t("manualEntry.open"))?.disabled).toBe(false);
  });

  it("opens the dialog on the action", () => {
    mount(<ManualEntryPanel detail={detail()} slug="cup" onEntered={() => {}} />);
    expect(host?.querySelector(".modal")).toBeNull();

    click(buttonNamed(t("manualEntry.open")));
    expect(host?.querySelector(".modal")?.textContent).toContain("Longsword");
  });
});
