// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";

import { api, type ExportSheetConfig } from "../api";
import ExportPanel from "../ExportPanel";
import i18n from "../i18n";

// The destination the Sheets export writes to: configured beside the export
// rather than in Setup, stated as a procedure rather than as a bare field, and
// shown back as a link that withdraws for the duration of a run (spec
// data-export).

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const t = i18n.getFixedT(i18n.language);
const ACCOUNT = "squire@proj.iam.gserviceaccount.com";
const SHEET = "https://docs.google.com/spreadsheets/d/abc";

let host: HTMLElement | null = null;

afterEach(() => {
  host?.remove();
  host = null;
  vi.restoreAllMocks();
});

async function mount(config: Partial<ExportSheetConfig> = {}) {
  vi.spyOn(api, "exportSheetConfig").mockResolvedValue({
    configured: true,
    service_account: ACCOUNT,
    output_sheet_url: null,
    ...config,
  });
  host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  await act(async () => {
    root.render(<ExportPanel slug="cup" english={false} onEnglishChange={() => {}} />);
  });
  return host;
}

function buttonNamed(text: string) {
  return [...(host?.querySelectorAll("button") ?? [])].find(
    (button) => button.textContent?.trim() === text,
  ) as HTMLButtonElement | undefined;
}

async function click(button: HTMLButtonElement | undefined) {
  await act(async () => {
    button?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  });
}

/** React tracks a controlled input's value on the node, so assigning to
 *  `.value` and firing `input` is seen as no change. The prototype setter is
 *  what a real keystroke goes through. */
async function typeDestination(value: string) {
  const field = document.body.querySelector("input[type=text]") as HTMLInputElement;
  await act(async () => {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set?.call(field, value);
    field.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

function destinationLink() {
  return host?.querySelector(".export-destination a") as HTMLAnchorElement | null;
}

it("opens the procedure instead of exporting when no destination is stored", async () => {
  const exported = vi.spyOn(api, "exportSheet");
  await mount({ output_sheet_url: null });

  await click(buttonNamed(t("export.runSheets")));

  expect(exported).not.toHaveBeenCalled();
  expect(document.body.textContent).toContain(t("export.wizard.share"));
  expect(document.body.textContent).toContain(ACCOUNT);
});

it("exports without asking once a destination is stored", async () => {
  const exported = vi
    .spyOn(api, "exportSheet")
    .mockResolvedValue({ worksheets: ["Fencers"], fencers: 3 });
  await mount({ output_sheet_url: SHEET });

  await click(buttonNamed(t("export.runSheets")));

  expect(exported).toHaveBeenCalledWith("cup", false);
  expect(document.body.textContent).not.toContain(t("export.wizard.share"));
});

it("states a stored destination as a link before any export is run", async () => {
  await mount({ output_sheet_url: SHEET });

  expect(destinationLink()?.getAttribute("href")).toBe(SHEET);
});

it("leaves the link in place after a failed run", async () => {
  vi.spyOn(api, "exportSheet").mockRejectedValue(new Error("network"));
  await mount({ output_sheet_url: SHEET });

  await click(buttonNamed(t("export.runSheets")));

  expect(host?.textContent).toContain(t("export.failed"));
  expect(destinationLink()?.getAttribute("href")).toBe(SHEET);
});

it("offers no Sheets export where the server has no Google access", async () => {
  await mount({ configured: false, service_account: null, output_sheet_url: null });

  expect(buttonNamed(t("export.runSheets"))).toBeUndefined();
  expect(host?.textContent).toContain(t("export.noGoogle"));
  // the canonical document touches no Google service, so it stays
  expect(buttonNamed(t("export.downloadJson"))).toBeDefined();
});

it("states the missing access in place of the share step", async () => {
  await mount({ configured: false, service_account: null });

  await click(buttonNamed(t("export.wizard.open")));

  expect(document.body.textContent).toContain(t("export.wizard.notConfigured"));
  expect(document.body.textContent).not.toContain(t("export.wizard.share"));
});

it("stores the pasted destination and runs the export the organizer pressed for", async () => {
  const update = vi.spyOn(api, "updateTournament").mockResolvedValue({} as never);
  const exported = vi
    .spyOn(api, "exportSheet")
    .mockResolvedValue({ worksheets: ["Fencers"], fencers: 1 });
  await mount({ output_sheet_url: null });

  await click(buttonNamed(t("export.runSheets")));
  await typeDestination(SHEET);
  // the wizard the export button opened names its confirm after what it goes
  // on to do, so the organizer gets the word they pressed
  await click(buttonNamed(t("export.wizard.confirmExport")));

  expect(update).toHaveBeenCalledWith("cup", { output_sheet_url: SHEET });
  expect(exported).toHaveBeenCalledWith("cup", false);
});

it("does not export when the procedure was opened on its own", async () => {
  const update = vi.spyOn(api, "updateTournament").mockResolvedValue({} as never);
  const exported = vi.spyOn(api, "exportSheet");
  await mount({ output_sheet_url: SHEET });

  await click(buttonNamed(t("export.wizard.change")));
  await typeDestination(`${SHEET}2`);
  await click(buttonNamed(t("export.wizard.confirm")));

  expect(update).toHaveBeenCalled();
  expect(exported).not.toHaveBeenCalled();
});

it("stores nothing when the procedure is dismissed", async () => {
  const update = vi.spyOn(api, "updateTournament");
  await mount({ output_sheet_url: null });

  await click(buttonNamed(t("export.wizard.open")));
  await typeDestination(SHEET);
  await click(buttonNamed(t("common.cancel")));

  expect(update).not.toHaveBeenCalled();
});

it("names the confirm after what it does in each of the two ways in", async () => {
  await mount({ output_sheet_url: SHEET });

  await click(buttonNamed(t("export.runSheets")));
  expect(buttonNamed(t("export.wizard.confirm"))).toBeUndefined();

  await click(buttonNamed(t("export.wizard.change")));
  // opened on its own, confirming stores an address and stops there
  expect(buttonNamed(t("export.wizard.confirm"))).toBeDefined();
  expect(buttonNamed(t("export.wizard.confirmExport"))).toBeUndefined();
});

it("forgets the destination, and the next export asks for one again", async () => {
  const update = vi.spyOn(api, "updateTournament").mockResolvedValue({} as never);
  const exported = vi.spyOn(api, "exportSheet");
  await mount({ output_sheet_url: SHEET });

  await click(buttonNamed(t("export.forgetSheet")));

  expect(update).toHaveBeenCalledWith("cup", { output_sheet_url: null });
  expect(destinationLink()).toBeNull();
  // and the card offers to set one rather than to change one
  expect(buttonNamed(t("export.wizard.open"))).toBeDefined();

  await click(buttonNamed(t("export.runSheets")));
  expect(exported).not.toHaveBeenCalled();
  expect(document.body.textContent).toContain(t("export.wizard.share"));
});

it("offers nothing to forget where no destination is stored", async () => {
  await mount({ output_sheet_url: null });

  expect(buttonNamed(t("export.forgetSheet"))).toBeUndefined();
});
