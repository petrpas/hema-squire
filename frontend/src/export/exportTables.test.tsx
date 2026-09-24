// @vitest-environment jsdom
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { SheetRow } from "../api";
import ExportPanel, { offersEnglishTick } from "../ExportPanel";
import i18n from "../i18n";
import { FENCERS_COLUMNS, ITEM_COLUMNS, ROSTER_COLUMNS, selectionsOf, toTsv } from "./columns";
import FencersTable from "./FencersTable";
import ItemsTable from "./ItemsTable";
import { activeOnly, rosterOrder, seedingOrder } from "./ordering";
import RosterTable from "./RosterTable";
import TableOperations from "./TableOperations";
import { tabCount, tabLabel } from "./tabs";

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
    queued_since: {},
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

  it("orders the queued by queue moment, so a fencer demoted at settlement waits last", () => {
    // rows arrive in registration order; the early registrant was demoted at
    // settlement, after the later one had already joined the queue
    const queued = (id: string, name: string, moment: string) =>
      row(id, name, { disciplines: [], substitute_for: ["LS"], queued_since: { LS: moment } });
    const demotedEarly = queued("reg:5", "Demoted Early", "2026-05-01T22:00:00+00:00");
    const waitedLater = queued("reg:6", "Waited Later", "2026-03-10T10:00:00+00:00");
    const demotedToo = queued("reg:7", "Demoted Too", "2026-05-01T22:00:00+00:00");
    const { rows, line } = rosterOrder(
      [seeded, demotedEarly, waitedLater, demotedToo],
      "LS",
      1,
      "queue",
      false,
    );
    expect(rows.map((r) => r.name)).toEqual([
      "Mid One",
      "Waited Later",
      "Demoted Early",
      "Demoted Too",
    ]);
    expect(line).toEqual({ after: 1, kind: "queue" });
  });

  it("marks only where capacity falls where nobody is queued", () => {
    const rows = [seeded, top, unrated];
    const { line } = rosterOrder(rows, "LS", 2, "capacity", false);
    expect(line).toEqual({ after: 2, kind: "capacity" });
  });

  it("seeds only those inside capacity where nobody is queued", () => {
    // Mid One and No Rating Three arrived first and fit the capacity of two;
    // Top Two came third. Seeding orders the two above the line and moves
    // nobody across it, however they rate.
    const { rows, line } = rosterOrder([unrated, seeded, top], "LS", 2, "capacity", true);
    expect(rows.map((r) => r.name)).toEqual(["Mid One", "No Rating Three", "Top Two"]);
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
    expect(items?.value(buyer, 0)).toBe("t-shirt (M) x2");
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
    expect(lines[0]).toBe("#\tName\tNat.\tClub\tHR_ID\tDisciplines\tPaid");
    expect(lines[1]).toBe("1\tJan Novák\tCZ\t\t10234\tLS\tYes");
    expect(lines[2]?.endsWith("No")).toBe(true);
  });

  it("renders headers and yes/no in English when the tick is on", () => {
    const tsv = toTsv(FENCERS_COLUMNS(en), rows, (id) => en(`export.column.${id}`));
    const lines = tsv.split("\n");
    expect(lines[0]).toBe("#\tName\tNat.\tClub\tHR_ID\tDisciplines\tPaid");
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

describe("a tab's count", () => {
  it("states a discipline's queue after its seats", () => {
    expect(tabCount({ count: 24, queued: 3 })).toBe("24 + 3");
  });

  it("leaves out an empty queue", () => {
    expect(tabCount({ count: 16, queued: 0 })).toBe("16");
  });

  it("states a seated zero", () => {
    expect(tabCount({ count: 0, queued: 0 })).toBe("0");
  });
});

describe("the rail card of the open tab", () => {
  const card = (discipline: boolean, active: boolean, ratingsMessage: string | null = null) =>
    renderToStaticMarkup(
      <TableOperations
        title="Sabre Open"
        active={{ checked: active, onChange: () => {} }}
        seeded={discipline ? { checked: false, onChange: () => {} } : undefined}
        onCopy={() => {}}
        onRefreshRatings={discipline ? () => {} : undefined}
        refreshing={false}
        ratingsMessage={ratingsMessage}
        message={null}
      />,
    );

  it("is headed by the tab it acts on and offers the switch and the copy", () => {
    const html = card(false, false);
    expect(html).toContain("Sabre Open");
    expect(html).toContain(t("export.activeOnly"));
    expect(html).toContain(t("export.copy"));
  });

  it("offers the ratings refresh only on a discipline", () => {
    expect(card(false, false)).not.toContain(t("export.fetchRatings"));
    expect(card(true, false)).toContain(t("export.fetchRatings"));
  });

  it("states a ratings fetch only where the fetch is offered", () => {
    const done = t("export.ratingsDone", { ratings: 81, fencers: 50 });
    expect(card(true, false, done)).toContain(done);
    expect(card(false, false, done)).not.toContain(done);
  });

  it("offers the seeding order only on a discipline, beside the active-only switch", () => {
    expect(card(false, false)).not.toContain(t("export.seedByRating"));
    const html = card(true, false);
    expect(html).toContain(t("export.seedByRating"));
    expect(html).toContain(t("export.activeOnly"));
  });

  it("states the switch of the tab it is given", () => {
    expect(card(true, true)).toContain("checked");
    expect(card(true, false)).not.toContain("checked");
  });

  it("is headed by the same name the band gives the tab", () => {
    const tab = {
      kind: "category" as const,
      key: "rental",
      label: "rental",
      capacity: null,
      line: null,
    };
    expect(tabLabel(t, tab)).toBe(t("export.category.rental"));
  });
});

describe("the Export card", () => {
  it("carries the English tick beside what leaves the phase", async () => {
    await i18n.changeLanguage("cs");
    try {
      const html = renderToStaticMarkup(
        <ExportPanel slug="cup" english={false} onEnglishChange={() => {}} />,
      );
      expect(html).toContain(i18n.getFixedT("cs")("export.english"));
      // The Sheets control waits on the server's configuration, which a static
      // render never fetches; what it writes to is `sheetWizard.test.tsx`.
      expect(html).toContain(i18n.getFixedT("cs")("export.downloadJson"));
    } finally {
      await i18n.changeLanguage("en");
    }
  });
});

describe("numeric columns", () => {
  it("are the position, the identifier, the rating and the rank, and no other", () => {
    const numeric = ROSTER_COLUMNS(t, "LS")
      .filter((column) => column.numeric)
      .map((column) => column.id);
    expect(numeric).toEqual(["position", "hr_id", "rating", "rank"]);
    expect(
      FENCERS_COLUMNS(t)
        .filter((column) => column.numeric)
        .map((c) => c.id),
    ).toEqual(["position", "hr_id"]);
  });
});

describe("the position column", () => {
  it("opens every table", () => {
    for (const columns of [FENCERS_COLUMNS(t), ROSTER_COLUMNS(t, "LS"), ITEM_COLUMNS(t, "merch")]) {
      expect(columns[0]?.id).toBe("position");
    }
  });

  it("numbers the rows from 1 as they are drawn, straight across the line", () => {
    const { rows, line } = rosterOrder(
      [
        row("reg:1", "Seated One"),
        row("reg:2", "Seated Two"),
        row("reg:3", "Queued Three", { disciplines: [], substitute_for: ["LS"] }),
      ],
      "LS",
      2,
      "queue",
      false,
    );
    const html = renderToStaticMarkup(
      <RosterTable
        rows={rows}
        slug="LS"
        capacity={2}
        lineKind="queue"
        seeded={false}
        edited={() => false}
        onRate={() => {}}
      />,
    );
    const numbers = [...html.matchAll(/<td class="col-index col-number">(\d+)<\/td>/g)].map(
      (m) => m[1],
    );
    expect(line.after).toBe(2);
    expect(numbers).toEqual(["1", "2", "3"]);
  });

  it("travels in the copy, numbering what the filter leaves", () => {
    const rows = activeOnly(
      [row("reg:1", "Unpaid One"), row("reg:2", "Paid Two", { paid: true })],
      true,
    );
    const lines = toTsv(FENCERS_COLUMNS(en), rows, (id) => en(`export.column.${id}`)).split("\n");
    expect(lines[0]?.split("\t")[0]).toBe("#");
    expect(lines[1]?.split("\t").slice(0, 2)).toEqual(["1", "Paid Two"]);
  });
});
