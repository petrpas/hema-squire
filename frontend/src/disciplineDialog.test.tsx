// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import DisciplineDialog, { type DisciplineIdentity } from "./DisciplineDialog";
import i18n from "./i18n";

// A side weapon is a taxonomy weapon that carries no rating: its name is
// generated, and the dialog says up front that it has no HEMA Ratings
// figures (spec discipline-identity, Discipline classification; spec
// hr-integration, Default rating category mapping).

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let host: HTMLElement | null = null;

function mount(onConfirm: (value: DisciplineIdentity) => void) {
  host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  act(() =>
    root.render(
      <DisciplineDialog
        initial={null}
        otherNames={[]}
        otherSlugs={new Set()}
        offerKind={false}
        onConfirm={onConfirm}
        onClose={() => {}}
      />,
    ),
  );
  return document.body;
}

function weaponSelect(page: HTMLElement): HTMLSelectElement {
  const select = [...page.querySelectorAll("select")].find((s) =>
    s.querySelector('option[value="ME"]'),
  );
  expect(select).toBeTruthy();
  return select!;
}

function choose(select: HTMLSelectElement, value: string) {
  act(() => {
    select.value = value;
    select.dispatchEvent(new Event("change", { bubbles: true }));
  });
}

function type(input: HTMLInputElement, value: string) {
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!;
  act(() => {
    setter.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

function confirm(page: HTMLElement) {
  const button = [...page.querySelectorAll<HTMLButtonElement>("button")].find(
    (b) => b.textContent === i18n.t("setup.disciplineDialog.confirm"),
  );
  expect(button).toBeTruthy();
  act(() => button!.click());
}

beforeEach(async () => {
  await i18n.changeLanguage("cs");
});

afterEach(() => {
  host?.remove();
  host = null;
  document.body.innerHTML = "";
});

describe("a side weapon in the discipline dialog", () => {
  it("is a taxonomy weapon with a generated name and states it carries no ratings", () => {
    const onConfirm = vi.fn();
    const page = mount(onConfirm);

    choose(weaponSelect(page), "ME");
    expect(page.textContent).toContain(i18n.t("setup.disciplines.weaponNoRatingHint"));

    confirm(page);
    expect(onConfirm).toHaveBeenCalledWith(
      expect.objectContaining({
        weapon: "ME",
        weaponCustom: false,
        name: "Messer Open",
        slug: "ME",
      }),
    );
  });

  it("says nothing of ratings for a rated weapon", () => {
    const page = mount(vi.fn());

    choose(weaponSelect(page), "SS");
    expect(page.textContent).not.toContain(i18n.t("setup.disciplines.weaponNoRatingHint"));
  });

  it("still requires a name for a weapon typed as the organizer's own", () => {
    const onConfirm = vi.fn();
    const page = mount(onConfirm);

    choose(weaponSelect(page), "__other__");
    const input = page.querySelector<HTMLInputElement>("input[autofocus], input:focus");
    expect(input).toBeTruthy();
    type(input!, "Tešák");
    confirm(page);

    expect(onConfirm).not.toHaveBeenCalled();
    expect(page.textContent).toContain(i18n.t("setup.disciplineDialog.nameRequired"));
  });
});
