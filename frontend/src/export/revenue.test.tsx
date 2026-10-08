// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  api,
  type ExportBandTab,
  type ExportReconciliationLine,
  type ExportRevenue,
  type ExportRevenueLine,
} from "../api";
import ExportPanel from "../ExportPanel";
import i18n from "../i18n";
import ExportTables from "./ExportTables";
import RevenueTable from "./RevenueTable";
import { revenueCount, revenuePrice, revenueTsv } from "./revenue";

// The Export revenue: what the copy carries, how the tables stand on screen,
// the rail card, and the Include finances tick (spec export-revenue).

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const cs = i18n.getFixedT("cs");
const en = i18n.getFixedT("en");

function line(fields: Partial<ExportRevenueLine>): ExportRevenueLine {
  return {
    kind: "item",
    name: "Sabre Open",
    price: 500,
    percent: false,
    paid_count: 12,
    count: 18,
    paid: 6000,
    to_pay: 3000,
    ...fields,
  };
}

function reconciled(fields: Partial<ExportReconciliationLine>): ExportReconciliationLine {
  return { kind: "journal", lane: "local", amount_cents: 0, count: null, ...fields };
}

const REVENUE: ExportRevenue = {
  local_currency: "CZK",
  blocks: [
    {
      key: "",
      lines: [
        line({}),
        line({
          kind: "discount",
          name: "Early",
          price: -10,
          percent: true,
          paid_count: 1,
          count: 2,
          paid: -50,
          to_pay: -50,
        }),
        line({ kind: "total", name: "", price: null, paid: 5950, to_pay: 2950 }),
      ],
    },
    {
      key: "rental",
      lines: [
        line({ name: "Mask", price: 50, paid_count: 2, count: 3, paid: 100, to_pay: 50 }),
        line({ kind: "total", name: "", price: null, paid_count: 2, count: 3, paid: 100 }),
      ],
    },
  ],
  total: line({ kind: "grand_total", name: "", price: null, paid: 6050, to_pay: 3000 }),
  reconciliation: [
    reconciled({ kind: "paid_by_items", amount_cents: 605000 }),
    reconciled({ kind: "credited_settled", lane: "eur", amount_cents: 6000 }),
    reconciled({ kind: "unissued", lane: null, amount_cents: null, count: 2 }),
  ],
};

describe("the revenue's copy", () => {
  it("heads each block, puts the count in two cells and keeps a percentage's %", () => {
    const tables = revenueTsv(cs, REVENUE).split("\n\n");
    expect(tables).toHaveLength(4); // two blocks, the grand total, the reconciliation
    expect(tables[0]?.split("\n")).toEqual([
      "Startovné\tCena\tPočet zaplaceno\tPočet celkem\tZaplaceno\tK zaplacení",
      "Sabre Open\t500\t12\t18\t6000\t3000",
      "Sleva Early\t-10 %\t1\t2\t-50\t-50",
      "Startovné celkem\t\t12\t18\t5950\t2950",
    ]);
    expect(tables[2]).toBe("Celkem\t\t12\t18\t6050\t3000");
    expect(tables[3]?.split("\n")).toEqual([
      "Sesouhlasení\tČástka",
      "Zaplaceno podle položek\t6050",
      "Připsáno na vyrovnané registrace (EUR)\t60",
      "Řádky bez registrace – neoceněno\t2",
    ]);
  });

  it("names Squire's words in English and leaves the organizer's as written", () => {
    const rows = revenueTsv(en, REVENUE).split("\n");
    expect(rows[0]?.startsWith("Entry fees\t")).toBe(true);
    expect(rows).toContain("Entry fees total\t\t12\t18\t5950\t2950");
    expect(rows).toContain("Discount Early\t-10 %\t1\t2\t-50\t-50");
  });
});

describe("the revenue on screen", () => {
  it("is one table per block, then the grand total and the reconciliation", () => {
    const html = renderToStaticMarkup(<RevenueTable revenue={REVENUE} />);
    expect(html.match(/<table/g)).toHaveLength(4);
    expect(html).toContain("12/18");
  });

  it("explains every reconciliation line beside its label", () => {
    const html = renderToStaticMarkup(<RevenueTable revenue={REVENUE} />);
    expect(html.match(/class="help-hint-marker"/g)).toHaveLength(REVENUE.reconciliation.length);
    const kinds: ExportReconciliationLine["kind"][] = [
      "paid_by_items",
      "credited_settled",
      "difference",
      "waived",
      "waived_credited",
      "deposits",
      "queue",
      "cancelled",
      "deleted",
      "unissued",
      "journal",
    ];
    for (const kind of kinds) {
      for (const t of [cs, en]) {
        expect(t(`export.revenue.hint.${kind}`)).not.toBe(`export.revenue.hint.${kind}`);
      }
    }
  });

  it("writes a discount with a true minus", () => {
    expect(revenuePrice(line({ price: -400 }), "CZK")).toBe("−400 Kč");
    expect(revenuePrice(line({ price: -10, percent: true }), "CZK")).toBe("−10 %");
    expect(revenueCount(line({}))).toBe("12/18");
  });
});

const BAND: ExportBandTab[] = [
  { kind: "fencers", key: "", label: "fencers", capacity: null, line: null, count: 3, queued: 0 },
  {
    kind: "revenue",
    key: "",
    label: "revenue",
    capacity: null,
    line: null,
    count: null,
    queued: 0,
  },
];

describe("the revenue tab", () => {
  let host: HTMLElement | null = null;
  let root: Root | null = null;

  afterEach(async () => {
    await act(async () => root?.unmount());
    root = null;
    host?.remove();
    host = null;
    vi.restoreAllMocks();
  });

  async function mount() {
    vi.spyOn(api, "exportTabs").mockResolvedValue(BAND);
    vi.spyOn(api, "exportTable").mockResolvedValue({ ...BAND[0]!, rows: [] });
    vi.spyOn(api, "exportRevenue").mockResolvedValue(REVENUE);
    vi.spyOn(api, "exportSheetConfig").mockResolvedValue({
      configured: true,
      service_account: "squire@example.com",
      output_sheet_url: "https://docs.google.com/spreadsheets/d/abc",
    });
    host = document.createElement("div");
    document.body.append(host);
    const mounted = createRoot(host);
    root = mounted;
    await act(async () => {
      mounted.render(
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
  }

  async function click(element: Element | null | undefined) {
    await act(async () => {
      element?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });
  }

  const tabButton = () =>
    [...(host?.querySelectorAll("nav button") ?? [])].find(
      (button) => button.textContent === en("export.tab.revenue"),
    );

  const financesTick = () =>
    [...(host?.querySelectorAll("label.rail-check") ?? [])]
      .find((label) => label.textContent === en("export.finances"))
      ?.querySelector("input");

  it("carries no count, and its card offers the copy alone", async () => {
    await mount();
    expect(tabButton()?.querySelector(".tab-count")).toBeNull();
    await click(tabButton());
    const card = host?.querySelector("section.rail-card");
    expect(card?.querySelector("h2")?.textContent).toBe(en("export.tab.revenue"));
    expect(card?.querySelectorAll("input")).toHaveLength(0);
    expect(card?.textContent).toContain(en("export.copy"));
    expect(host?.textContent).toContain("Sabre Open");
  });

  it("offers the finances tick off, and sends it with the sheet write", async () => {
    const written = vi
      .spyOn(api, "exportSheet")
      .mockResolvedValue({ worksheets: ["Fencers", "Revenue"], fencers: 3 });
    await mount();
    expect(financesTick()?.checked).toBe(false);
    await click(financesTick());
    expect(financesTick()?.checked).toBe(true);

    const run = [...(host?.querySelectorAll("button") ?? [])].find(
      (button) => button.textContent?.trim() === en("export.runSheets"),
    );
    await click(run);
    expect(written).toHaveBeenCalledWith("cup", false, true);
  });

  it("is off again when the phase is opened anew", async () => {
    await mount();
    await click(financesTick());
    await act(async () => root?.unmount());
    host?.remove();
    await mount();
    expect(financesTick()?.checked).toBe(false);
  });
});

describe("the finances tick in English", () => {
  it("is offered where the English tick is not", async () => {
    await i18n.changeLanguage("en");
    const html = renderToStaticMarkup(
      <ExportPanel slug="cup" english={false} finances={false} onFinancesChange={() => {}} />,
    );
    expect(html).not.toContain(en("export.english"));
    expect(html).toContain(en("export.finances"));
    expect(html).toContain(en("export.financesHint"));
  });
});
