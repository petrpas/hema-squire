// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api, type ExportBandTab, type ExportSummaryLine } from "../api";
import i18n from "../i18n";
import ExportTables from "./ExportTables";
import SummaryTable from "./SummaryTable";
import { summaryLabel, summaryTsv } from "./summary";
import TableOperations from "./TableOperations";
import { tabCount } from "./tabs";

// The Export summary: how each line is named, what the copy carries, and how
// the tab stands in the band and the rail (spec export-summary).

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const cs = i18n.getFixedT("cs");
const en = i18n.getFixedT("en");

function line(fields: Partial<ExportSummaryLine>): ExportSummaryLine {
  return {
    kind: "item",
    category: "merch",
    name: "Triko",
    option: null,
    missing: false,
    item_id: 1,
    paid: 0,
    unpaid: 0,
    ...fields,
  };
}

const LINES = [
  line({ kind: "discipline", category: "", name: "LSM", item_id: null, paid: 44, unpaid: 4 }),
  line({ kind: "queue", category: "", name: "LSM", item_id: null, paid: 2, unpaid: 12 }),
  line({ option: "XL", paid: 3, unpaid: 1 }),
  line({ missing: true, unpaid: 1 }),
];

describe("a summary line's name", () => {
  it("adds only Squire's own words to the organizer's names", () => {
    expect(LINES.map((l) => summaryLabel(cs, l))).toEqual([
      "LSM",
      "LSM (fronta)",
      "Triko – XL",
      "Triko – neuvedeno",
    ]);
    expect(LINES.map((l) => summaryLabel(en, l)).slice(1)).toEqual([
      "LSM (queue)",
      "Triko – XL",
      "Triko – not given",
    ]);
  });
});

describe("the summary's copy", () => {
  it("is a header and one line per row, counts as digits, no position column", () => {
    expect(summaryTsv(en, LINES).split("\n")).toEqual([
      "Item\tPaid\tUnpaid",
      "LSM\t44\t4",
      "LSM (queue)\t2\t12",
      "Triko – XL\t3\t1",
      "Triko – not given\t0\t1",
    ]);
  });
});

describe("the summary on screen", () => {
  it("states the counts right-aligned beside the names", () => {
    const html = renderToStaticMarkup(<SummaryTable lines={LINES} />);
    expect(html).toContain('<td class="col-number">44</td>');
    expect(html).not.toContain("col-index");
  });

  it("states no count in the band", () => {
    expect(tabCount({ count: null, queued: 0 })).toBeNull();
  });

  it("offers the copy but no switch in the rail", () => {
    const html = renderToStaticMarkup(
      <TableOperations
        title="Souhrn"
        onCopy={() => {}}
        refreshing={false}
        ratingsMessage={null}
        message={null}
      />,
    );
    expect(html).toContain(en("export.copy"));
    expect(html).not.toContain(en("export.activeOnly"));
    expect(html).not.toContain(en("export.seedByRating"));
  });
});

const BAND: ExportBandTab[] = [
  { kind: "fencers", key: "", label: "fencers", capacity: null, line: null, count: 3, queued: 0 },
  {
    kind: "category",
    key: "merch",
    label: "merch",
    capacity: null,
    line: null,
    count: 1,
    queued: 0,
  },
  {
    kind: "summary",
    key: "",
    label: "summary",
    capacity: null,
    line: null,
    count: null,
    queued: 0,
  },
];

describe("the summary tab", () => {
  let host: HTMLElement | null = null;

  afterEach(() => {
    host?.remove();
    host = null;
    vi.restoreAllMocks();
  });

  async function mount() {
    vi.spyOn(api, "exportTabs").mockResolvedValue(BAND);
    vi.spyOn(api, "exportTable").mockImplementation(async (_slug, kind, key) => ({
      ...(BAND.find((tab) => tab.kind === kind && tab.key === key) ?? BAND[0]!),
      rows: [],
    }));
    vi.spyOn(api, "exportSummary").mockResolvedValue({ lines: LINES });
    vi.spyOn(api, "exportSheetConfig").mockResolvedValue({
      configured: false,
      service_account: null,
      output_sheet_url: null,
    });
    host = document.createElement("div");
    document.body.append(host);
    const root = createRoot(host);
    await act(async () => {
      root.render(
        <ExportTables
          slug="cup"
          edits={[]}
          english={false}
          onEnglishChange={() => {}}
          onChanged={() => {}}
          revision={0}
          renderRail={(panel) => panel}
        />,
      );
    });
    return host;
  }

  const tabButton = (name: string) =>
    [...(host?.querySelectorAll("nav button") ?? [])].find((button) =>
      button.textContent?.startsWith(name),
    ) as HTMLButtonElement;

  const activeSwitch = () =>
    [...(host?.querySelectorAll("label.rail-check") ?? [])]
      .find((label) => label.textContent === en("export.activeOnly"))
      ?.querySelector("input");

  async function click(element: HTMLElement | null | undefined) {
    await act(async () => {
      element?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });
  }

  it("is last in the band, carries no count, and lists the lines", async () => {
    await mount();
    const summary = tabButton(en("export.tab.summary"));
    expect(summary.querySelector(".tab-count")).toBeNull();
    await click(summary);
    expect(host?.textContent).toContain("LSM (queue)");
    expect(activeSwitch()).toBeUndefined();
  });

  it("leaves the active-only switch as it was on the other tabs", async () => {
    await mount();
    await click(tabButton(en("export.category.merch")));
    await click(activeSwitch());
    expect(activeSwitch()?.checked).toBe(true);
    await click(tabButton(en("export.tab.summary")));
    await click(tabButton(en("export.category.merch")));
    expect(activeSwitch()?.checked).toBe(true);
  });
});
