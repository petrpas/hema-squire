// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "./i18n";
import ResendManageLinkDialog from "./ResendManageLinkDialog";

// The organizer sends a guest their manage link again, asked first and
// stated once done (change `guest-registration`).

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let host: HTMLElement | null = null;

function mount(onConfirm: () => Promise<void>) {
  host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  act(() =>
    root.render(
      <ResendManageLinkDialog name="Petr Nový" onConfirm={onConfirm} onClose={() => {}} />,
    ),
  );
  return document.body;
}

function send(page: HTMLElement) {
  return act(async () => {
    [...page.querySelectorAll("button")]
      .find((b) => b.textContent === i18n.t("console.resendLink.confirm"))
      ?.click();
  });
}

beforeEach(async () => {
  await i18n.changeLanguage("en");
});

afterEach(() => {
  host?.remove();
  host = null;
});

describe("sending the manage link again", () => {
  it("sends nothing until confirmed, then says it was sent", async () => {
    const onConfirm = vi.fn().mockResolvedValue(undefined);
    const page = mount(onConfirm);
    expect(onConfirm).not.toHaveBeenCalled();
    expect(page.textContent).toContain(i18n.t("console.resendLink.meaning"));

    await send(page);

    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(page.textContent).toContain(i18n.t("console.resendLink.sent"));
    const labels = [...page.querySelectorAll("button")].map((b) => b.textContent);
    expect(labels).not.toContain(i18n.t("console.resendLink.confirm"));
  });

  it("states a failure and stays open", async () => {
    const page = mount(vi.fn().mockRejectedValue(new Error("down")));
    await send(page);
    expect(page.textContent).toContain(i18n.t("console.resendLink.failed"));
  });
});
