// @vitest-environment jsdom
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { SheetRow } from "../api";
import i18n from "../i18n";
import { FENCERS_COLUMNS, ITEM_COLUMNS, ROSTER_COLUMNS, selectionsOf, toTsv } from "./columns";
import { offersEnglishTick } from "./ExportTables";
import FencersTable from "./FencersTable";
import ItemsTable from "./ItemsTable";
import { activeOnly, rosterOrder, seedingOrder } from "./ordering";
import RosterTable from "./RosterTable";

// The Export phase's tables: what each lists, the order it lists it in, where
// the capacity line falls, and what leaves by the clipboard (spec
// `export-tables`).

function row(id: string, name: string, fields: Partial<SheetRow> = {}): SheetRow {
  return {
    id,
    number: null,
    name,
    nationality: "CZ",
    club: null,
    hr_id: null,
    hr_name: null,
    hr_nationality: null,
    hr_club: null,
    disciplines: ["LS"],
    substitute_for: [],
    state: "reserved",
    registration_id: null,
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
    ...fields,
  } as SheetRow;
}

const t = i18n.getFixedT(i18n.language);
const en = i18n.getFixedT("en");

describe("the active-only switch", () => {
  it("narrows to the paid", () => {
    const rows = [row("reg:1", "Paid One", { paid: true }), row("reg:2", "Unpaid Two")];
    expect(activeOnly(rows, true).map((r) => r.name)).toEqual(["Paid One"]);
    expect(activeOnly(rows, false)).toHaveLength(2);
  });

  it("leaves out a registration credited nothing, whatever it owes", () => {
    // a fencer whose entries all sit in a queue is priced at zero and is still
    // not a fencer who has paid: `paid` is the settled derivation, and it is
    // false with nothing credited and nobody waiving
    const queued = row("reg:3", "Queued Three", { disciplines: [], substitute_for: ["LS"] });
    expect(activeOnly([queued], true)).toEqual([]);
  });
});

describe("a discipline tab as a seeding roster", () => {
  const seeded = row("reg:1", "Mid One", { ratings: { LS: 1200 } } as Partial<SheetRow>);
  const top = row("reg:2", "Top Two", { ratings: { LS: 1400 } } as Partial<SheetRow>);
  const unrated = row("reg:3", "No Rating Three");

  it("orders by rating, the unrated last in the order they arrived", () => {
    const ordered = seedingOrder([seeded, unrated, top], "LS");
    expect(ordered.map((r) => r.name)).toEqual(["Top Two", "Mid One", "No Rating Three"]);
  });

  it("keeps a highly rated substitute below the line", () => {
    const queued = row("reg:4", "Queued Star", {
      disciplines: [],
      substitute_for: ["LS"],
      ratings: { LS: 1900 },
    } as Partial<SheetRow>);
    const { rows, line } = rosterOrder([seeded, top, queued], "LS", 16, "queue", true);
    expect(rows.map((r) => r.name)).toEqual(["Top Two", "Mid One", "Queued Star"]);
    expect(line).toEqual({ after: 2, kind: "queue" });
  });

  it("marks only where capacity falls where nobody is queued", () => {
    const rows = [seeded, top, unrated];
    const { line } = rosterOrder(rows, "LS", 2, "capacity", false);
    expect(line).toEqual({ after: 2, kind: "capacity" });
  });

  it("draws no line on a table shorter than the capacity", () => {
    const { line } = rosterOrder([seeded, top], "LS", 16, "capacity", false);
    expect(line.after).toBeNull();
  });

  it("reorders on a typed rating", () => {
    const corrected = row("reg:1", "Mid One", { ratings: { LS: 1500 } } as Partial<SheetRow>);
    const { rows } = rosterOrder([corrected, top], "LS", 16, "queue", true);
    expect(rows.map((r) => r.name)).toEqual(["Mid One", "Top Two"]);
  });
});

describe("an item tab", () => {
  const buyer = row("reg:1", "Buyer One", {
    extras: { merch: [{ name: "t-shirt", qty: 2, option: "M" }] },
  } as Partial<SheetRow>);

  it("states the item, its option and its quantity", () => {
    const columns = ITEM_COLUMNS(t, "merch");
    const items = columns.find((column) => column.id === "items");
    expect(items?.value(buyer)).toBe("t-shirt (M) x2");
  });

  it("reads nothing for a category the fencer bought nothing in", () => {
    expect(selectionsOf(buyer, "rental")).toEqual([]);
  });
});

describe("the copy action", () => {
  const rows = [
    row("reg:1", "Jan Novák", { paid: true, hr_id: 10234 }),
    row("reg:2", "Petra Malá"),
  ];

  it("carries a header row and the values, in the order given", () => {
    const tsv = toTsv(FENCERS_COLUMNS(t), rows, (id) => t(`export.column.${id}`));
    const lines = tsv.split("\n");
    expect(lines[0]).toBe("Name\tNat.\tClub\tHR_ID\tDisciplines\tPaid");
    expect(lines[1]).toBe("Jan Novák\tCZ\t\t10234\tLS\tYes");
    expect(lines[2]?.endsWith("No")).toBe(true);
  });

  it("renders headers and yes/no in English when the tick is on", () => {
    const tsv = toTsv(FENCERS_COLUMNS(en), rows, (id) => en(`export.column.${id}`));
    const lines = tsv.split("\n");
    expect(lines[0]).toBe("Name\tNat.\tClub\tHR_ID\tDisciplines\tPaid");
    expect(lines[1]?.endsWith("Yes")).toBe(true);
  });

  it("follows the filter", () => {
    const tsv = toTsv(FENCERS_COLUMNS(t), activeOnly(rows, true), (id) => t(`export.column.${id}`));
    expect(tsv.split("\n")).toHaveLength(2); // the header and the one paid row
  });

  it("carries no capacity line", () => {
    const columns = ROSTER_COLUMNS(t, "LS");
    const tsv = toTsv(columns, rows, (id) => t(`export.column.${id}`));
    expect(tsv).not.toContain(t("export.line.queue"));
    expect(tsv).not.toContain(t("export.line.capacity"));
  });
});

describe("what the tables render", () => {
  it("lists every fencer with their disciplines and their paid mark", () => {
    const html = renderToStaticMarkup(
      <FencersTable rows={[row("reg:1", "Jan Novák", { paid: true })]} />,
    );
    expect(html).toContain("Jan Novák");
    expect(html).toContain(t("export.yes"));
  });

  it("lists only the buyers of an item, with what they bought", () => {
    const html = renderToStaticMarkup(
      <ItemsTable
        category="merch"
        rows={[
          row("reg:1", "Buyer One", {
            extras: { merch: [{ name: "mug", qty: 1, option: null }] },
          } as Partial<SheetRow>),
        ]}
      />,
    );
    expect(html).toContain("mug");
  });

  it("draws the line as a row of the table, labelled", () => {
    const html = renderToStaticMarkup(
      <RosterTable
        rows={[
          row("reg:1", "Seated One"),
          row("reg:2", "Queued Two", { disciplines: [], substitute_for: ["LS"] }),
        ]}
        slug="LS"
        capacity={1}
        lineKind="queue"
        seeded={false}
        edited={() => false}
        onRate={() => {}}
      />,
    );
    expect(html).toContain(t("export.line.queue"));
    expect(html.indexOf("Seated One")).toBeLessThan(html.indexOf(t("export.line.queue")));
  });

  it("marks a corrected rating as a manual edit", () => {
    const html = renderToStaticMarkup(
      <RosterTable
        rows={[row("reg:1", "Corrected One", { ratings: { LS: 1555 } } as Partial<SheetRow>)]}
        slug="LS"
        capacity={16}
        lineKind="queue"
        seeded={false}
        edited={() => true}
        onRate={() => {}}
      />,
    );
    expect(html).toContain("cell-edited");
    expect(html).toContain("1555");
  });
});

describe("the English tick", () => {
  it("is not offered to an organizer already working in English", () => {
    expect(offersEnglishTick("en")).toBe(false);
    expect(offersEnglishTick("en-GB")).toBe(false);
    expect(offersEnglishTick("cs")).toBe(true);
  });

  it("does not reach the tables, which stay in the organizer's own language", async () => {
    // the tables take no `english` prop at all: the tick governs what leaves —
    // the copied values and the sheet write — and the table is also where the
    // organizer works (design export-tables D5). Read on an organizer working
    // in Czech, since English is what the console renders in by default and
    // the tick would have nothing to say there.
    const cs = i18n.getFixedT("cs");
    await i18n.changeLanguage("cs");
    try {
      const html = renderToStaticMarkup(<FencersTable rows={[row("reg:1", "Jan Novák")]} />);
      expect(html).toContain(cs("export.column.name"));
      expect(html).not.toContain(en("export.column.paid"));
    } finally {
      await i18n.changeLanguage("en");
    }
  });
});
