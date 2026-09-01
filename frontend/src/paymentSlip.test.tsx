// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import PaymentSlipBlock, { type SlipField } from "./PaymentSlipBlock";
import i18n from "./i18n";

// Paying on the device the QR is displayed on: the code is inert there, so the
// transfer details have to be copyable and the image has to reach a banking
// app (change `add-mobile-fencer-layout`, group 6).

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const fields: SlipField[] = [
  { key: "amount", label: "Částka", shown: "1 200 Kč", copy: "1200" },
  { key: "vs", label: "VS", shown: "20260042", copy: "20260042" },
  { key: "expires", label: "Platí do", shown: "5. 12. 2026" },
];

// a 1x1 PNG
const PNG =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==";

let host: HTMLElement | null = null;
let root: ReturnType<typeof createRoot> | null = null;

function mount() {
  host = document.createElement("div");
  document.body.append(host);
  root = createRoot(host);
  act(() =>
    root!.render(
      <PaymentSlipBlock fields={fields} qrBase64={PNG} qrAlt="QR" qrFilename="qr-20260042.png" />,
    ),
  );
  return host;
}

function buttonSaying(page: HTMLElement, text: string) {
  return [...page.querySelectorAll("button")].find((b) => b.textContent?.trim() === text);
}

beforeEach(() => {
  vi.restoreAllMocks();
  void i18n.changeLanguage("cs");
});

afterEach(() => {
  // unmounted, not merely detached: the copied-note's fade-out timer is still
  // pending after a copy test and would set state on a torn-down tree
  if (root !== null) act(() => root!.unmount());
  root = null;
  host?.remove();
  host = null;
  Reflect.deleteProperty(navigator, "clipboard");
  Reflect.deleteProperty(navigator, "canShare");
  Reflect.deleteProperty(navigator, "share");
});

describe("the transfer details can be copied", () => {
  it("offers a copy action for every hand-entered value, and none for the rest", () => {
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
      configurable: true,
    });

    const page = mount();
    // amount and VS carry one each; the expiry date is read, never typed
    expect(page.querySelectorAll(".slip-copy")).toHaveLength(2);
  });

  it("copies the bare value, not the value as displayed", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });

    const page = mount();
    const copy = page.querySelectorAll(".slip-copy")[0];
    await act(async () => {
      copy.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    // shown as "1 200 Kč"; a payment form wants "1200"
    expect(writeText).toHaveBeenCalledWith("1200");
  });

  it("confirms a copy in static text beside the field", async () => {
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
      configurable: true,
    });

    const page = mount();
    expect(page.querySelector(".slip-copied.is-shown")).toBeNull();

    await act(async () => {
      page.querySelectorAll(".slip-copy")[0].dispatchEvent(
        new MouseEvent("click", { bubbles: true }),
      );
    });

    const note = page.querySelector(".slip-copied.is-shown");
    expect(note).not.toBeNull();
    expect(note!.textContent).toBe("Zkopírováno");
  });

  it("offers no copy action where the browser exposes no clipboard", () => {
    // navigator.clipboard is absent outside a secure context — over a LAN IP,
    // for instance. Absent is right; present and silently failing is not.
    const page = mount();
    expect(page.querySelectorAll(".slip-copy")).toHaveLength(0);
    // the values are still on screen to be read
    expect(page.textContent).toContain("20260042");
  });
});

describe("the QR image can be taken into a banking app", () => {
  it("hands the image to the share sheet where the device has one", async () => {
    const share = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "canShare", { value: () => true, configurable: true });
    Object.defineProperty(navigator, "share", { value: share, configurable: true });

    const page = mount();
    const save = buttonSaying(page, "Uložit QR kód")!;
    await act(async () => {
      save.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    expect(share).toHaveBeenCalledTimes(1);
    const shared = share.mock.calls[0][0] as { files: File[] };
    expect(shared.files[0].name).toBe("qr-20260042.png");
    expect(shared.files[0].type).toBe("image/png");
  });

  it("falls back to a download where it has none", async () => {
    // no navigator.canShare — a desktop browser, where a download is right
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => undefined);
    globalThis.URL.createObjectURL = vi.fn().mockReturnValue("blob:qr");
    globalThis.URL.revokeObjectURL = vi.fn();

    const page = mount();
    await act(async () => {
      buttonSaying(page, "Uložit QR kód")!.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    expect(click).toHaveBeenCalledTimes(1);
    expect(globalThis.URL.revokeObjectURL).toHaveBeenCalled();
  });

  it("treats a dismissed share sheet as a change of mind, not a failure", async () => {
    Object.defineProperty(navigator, "canShare", { value: () => true, configurable: true });
    Object.defineProperty(navigator, "share", {
      value: vi.fn().mockRejectedValue(new DOMException("cancelled", "AbortError")),
      configurable: true,
    });
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => undefined);

    const page = mount();
    await act(async () => {
      buttonSaying(page, "Uložit QR kód")!.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    // no surprise download after the fencer backed out
    expect(click).not.toHaveBeenCalled();
  });
});
