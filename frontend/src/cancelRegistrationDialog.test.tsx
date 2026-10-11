// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import CancelRegistrationDialog from "./CancelRegistrationDialog";
import i18n from "./i18n";

// The organizer's cancellation, confirmed in a dialog that says what will
// happen (spec registration, An organizer may cancel a registration).

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let host: HTMLElement | null = null;

function mount(paid: boolean, onConfirm: (note: string | null) => Promise<void>) {
  host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  act(() =>
    root.render(
      <CancelRegistrationDialog
        name="Jan Novák"
        paid={paid}
        onConfirm={onConfirm}
        onClose={() => {}}
      />,
    ),
  );
  return document.body;
}

function confirmButton(page: HTMLElement): HTMLButtonElement {
  const button = [...page.querySelectorAll<HTMLButtonElement>(".modal-actions button")].find(
    (b) => b.textContent === i18n.t("console.cancelRegistration.confirm"),
  );
  expect(button).toBeTruthy();
  return button!;
}

beforeEach(async () => {
  await i18n.changeLanguage("cs");
});

afterEach(() => {
  host?.remove();
  host = null;
  document.body.innerHTML = "";
});

describe("the cancellation dialog", () => {
  it("states that it frees the seat, cannot be undone, and mails the fencer", () => {
    const page = mount(false, vi.fn());

    expect(page.textContent).toContain(i18n.t("console.cancelRegistration.meaning"));
    expect(page.textContent).toContain(i18n.t("console.cancelRegistration.mail"));
    expect(page.textContent).not.toContain(i18n.t("console.cancelRegistration.refund"));
    expect(confirmButton(page).className).toBe("btn-danger");
  });

  it("says the money is the organizer's to return where some has arrived", () => {
    const page = mount(true, vi.fn());

    expect(page.textContent).toContain(i18n.t("console.cancelRegistration.refund"));
  });

  it("sends the note, trimmed, or nothing when none was written", async () => {
    const onConfirm = vi.fn().mockResolvedValue(undefined);
    const page = mount(false, onConfirm);

    await act(async () => confirmButton(page).click());
    expect(onConfirm).toHaveBeenLastCalledWith(null);

    const field = page.querySelector("textarea")!;
    act(() => {
      const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")!.set!;
      setter.call(field, "  duplicitní přihláška ");
      field.dispatchEvent(new Event("input", { bubbles: true }));
    });
    await act(async () => confirmButton(page).click());
    expect(onConfirm).toHaveBeenLastCalledWith("duplicitní přihláška");
  });
});
