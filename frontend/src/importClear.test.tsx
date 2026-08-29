// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ImportPanel from "./ImportPanel";
import { api } from "./api";
import i18n from "./i18n";

// the panel reads its words from the catalogue, so the test asks the catalogue
// for the same ones rather than hard-coding a translation
const t = i18n.getFixedT("cs");

// Clearing the imported table: offered only when there is something to clear,
// stated before it happens, and final once confirmed (spec `table-import`,
// Clearing is warned about and irreversible).

let host: HTMLElement | null = null;

function mount(element: React.ReactElement) {
  host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  act(() => root.render(element));
  return host;
}

function buttons() {
  return [...(host?.querySelectorAll("button") ?? [])] as HTMLButtonElement[];
}

function labelled(text: string) {
  return buttons().find((button) => button.textContent?.includes(text));
}

function click(button: HTMLButtonElement | undefined) {
  act(() => void button?.dispatchEvent(new MouseEvent("click", { bubbles: true })));
}

/** Lets the panel's status fetch settle before the assertions read the DOM. */
async function settle() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

function withImports(rows = 40, files = 2) {
  vi.spyOn(api, "importStatus").mockResolvedValue({
    batch: { id: 1, filename: "regs.csv", uploaded_at: "2026-04-01T10:00:00", rows },
    total: { rows, files },
  });
}

beforeEach(() => {
  vi.restoreAllMocks();
});

afterEach(() => {
  host?.remove();
  host = null;
});

describe("the clear action", () => {
  it("is not offered on a tournament that has imported nothing", async () => {
    vi.spyOn(api, "importStatus").mockResolvedValue({
      batch: null,
      total: { rows: 0, files: 0 },
    });
    mount(<ImportPanel slug="cup" onImported={() => {}} />);
    await settle();

    expect(labelled(t("import.clear"))).toBeUndefined();
  });

  it("states the rows, the files and the finality before acting", async () => {
    withImports();
    const clear = vi.spyOn(api, "clearImports");
    mount(<ImportPanel slug="cup" onImported={() => {}} />);
    await settle();

    click(labelled(t("import.clear")));

    const modal = host?.querySelector(".modal")?.textContent ?? "";
    expect(modal).toContain("40");
    expect(modal).toContain("2");
    expect(modal).toContain(t("import.clearConfirm.final"));
    expect(clear).not.toHaveBeenCalled();
  });

  it("changes nothing when the confirmation is dismissed", async () => {
    withImports();
    const clear = vi.spyOn(api, "clearImports");
    const onImported = vi.fn();
    mount(<ImportPanel slug="cup" onImported={onImported} />);
    await settle();

    click(labelled(t("import.clear")));
    click(labelled(t("common.cancel")));

    expect(host?.querySelector(".modal")).toBeNull();
    expect(clear).not.toHaveBeenCalled();
    expect(onImported).not.toHaveBeenCalled();
  });

  it("clears and refreshes the table once confirmed", async () => {
    withImports();
    const clear = vi
      .spyOn(api, "clearImports")
      .mockResolvedValue({ rows: 40, files: 2 });
    const onImported = vi.fn();
    mount(<ImportPanel slug="cup" onImported={onImported} />);
    await settle();

    click(labelled(t("import.clear")));
    click(labelled(t("import.clearConfirm.confirm")));
    await settle();

    expect(clear).toHaveBeenCalledWith("cup");
    expect(onImported).toHaveBeenCalled();
    expect(host?.querySelector(".modal")).toBeNull();
  });
});
