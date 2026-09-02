// @vitest-environment jsdom
import { describe, expect, it } from "vitest";

import type { NetChange, SheetRow } from "./api";
import {
  DEFAULT_PHASE,
  absorbedInto,
  PHASE_COLUMNS,
  PHASES,
  editableHere,
  editsForPhase,
  rowAction,
  rowsForPhase,
  type Phase,
} from "./Console";

// Which rows and which edits belong to which phase (spec `etl-console`,
// Phase-tabbed fencer table / Import view of one batch / Two manual-edits logs
// with two meanings).

function row(id: string, fields: Partial<SheetRow> = {}): SheetRow {
  return { id, number: 1, name: "Jan Novák", ...fields } as SheetRow;
}

function edit(phase: string, target: string): NetChange {
  return {
    phase,
    target,
    field: "club",
    before: null,
    after: "SK Praha",
    rule_ids: [1],
    actor: "Petr Paščenko",
    at: "2026-08-28T18:41:00+00:00",
  };
}

const ROWS = [
  row("imp:c1aa"),
  row("reg:7"),
  row("imp:d2bb", { _deleted: true, _merged_into: "reg:7" }),
];

describe("the phase list", () => {
  it("names Import and Fencers where Load and Parsing stood", () => {
    expect(PHASES).toContain("import");
    expect(PHASES).toContain("fencers");
    expect(PHASES as readonly string[]).not.toContain("load");
    expect(PHASES as readonly string[]).not.toContain("parsing");
  });

  it("keeps Import and Fencers in that order, after Setup", () => {
    expect(PHASES.slice(0, 3)).toEqual(["setup", "import", "fencers"]);
  });

  it("opens on the fencer list, so an organizer who never imports lands somewhere", () => {
    expect(DEFAULT_PHASE).toBe("fencers");
  });
});

describe("the rows a phase lists", () => {
  it("gives Import the imported rows alone", () => {
    expect(rowsForPhase(ROWS, "import").map((r) => r.id)).toEqual(["imp:c1aa", "imp:d2bb"]);
  });

  it("keeps an absorbed row in the Import view", () => {
    // the view is a record of what a file contained, not a list of who competes
    expect(rowsForPhase(ROWS, "import").map((r) => r.id)).toContain("imp:d2bb");
  });

  it("lists the Import rows in the order of the file, not of the fencer list", () => {
    // the fencer list sorts by registration moment, which would scatter the
    // batch's lines; a reader checking an import against its source follows the
    // file
    const scattered = [
      row("imp:c", { _source: { file: "regs.csv", row: 52 } }),
      row("imp:a", { _source: { file: "regs.csv", row: 3 } }),
      row("imp:b", { _source: { file: "regs.csv", row: 40 } }),
    ];
    expect(rowsForPhase(scattered, "import").map((r) => r._source?.row)).toEqual([3, 40, 52]);
  });

  it("gives the fencer list and every phase after it both populations", () => {
    for (const phase of ["fencers", "matching", "dedup", "payments", "export"] as Phase[]) {
      // the absorbed row is Import's alone; the other two are every phase's
      expect(rowsForPhase(ROWS, phase).map((r) => r.id)).toEqual(["imp:c1aa", "reg:7"]);
    }
  });
});

describe("a row a removal took out of the table", () => {
  const deletedOn = (phase: Phase) => [
    row("reg:1"),
    row("reg:2", { _deleted: true, _removed_in: phase }),
  ];

  it("stays listed on the phase the deletion was made on", () => {
    expect(rowsForPhase(deletedOn("fencers"), "fencers").map((r) => r.id)).toContain("reg:2");
  });

  it("is gone from every phase after that one", () => {
    const rows = deletedOn("fencers");
    for (const phase of ["matching", "dedup", "payments", "export"] as Phase[]) {
      expect(rowsForPhase(rows, phase).map((r) => r.id)).toEqual(["reg:1"]);
    }
  });

  it("is still listed on the phases before it, which have not handled it yet", () => {
    // deleted on Payments, an organizer back on Fencers still sees it and can
    // bring it back from there
    const rows = deletedOn("payments");
    for (const phase of ["fencers", "matching", "dedup"] as Phase[]) {
      expect(rowsForPhase(rows, phase).map((r) => r.id)).toContain("reg:2");
    }
    expect(rowsForPhase(rows, "export").map((r) => r.id)).toEqual(["reg:1"]);
  });

  it("returns to every phase once it is restored", () => {
    const restored = [row("reg:1"), row("reg:2")];
    for (const phase of ["fencers", "matching", "dedup", "payments", "export"] as Phase[]) {
      expect(rowsForPhase(restored, phase)).toHaveLength(2);
    }
  });

  it("stays in the Import view whatever phase deleted it", () => {
    const rows = [row("imp:a", { _deleted: true, _removed_in: "payments" })];
    expect(rowsForPhase(rows, "import").map((r) => r.id)).toEqual(["imp:a"]);
  });

  it("is listed everywhere when its removing phase cannot be placed", () => {
    // a rule left by a retired phase name, or one the mode no longer offers:
    // a row no phase lists is a row no phase can restore
    const rows = [row("reg:2", { _deleted: true, _removed_in: "parsing" })];
    for (const phase of ["fencers", "matching", "export"] as Phase[]) {
      expect(rowsForPhase(rows, phase)).toHaveLength(1);
    }
  });

  it("is listed everywhere when it says no removing phase at all", () => {
    const rows = [row("reg:2", { _deleted: true })];
    expect(rowsForPhase(rows, "export")).toHaveLength(1);
  });

  it("leaves the counts alone, which count the live rows no phase hides", () => {
    const rows = [
      row("reg:1", { paid: true }),
      row("reg:2", { _deleted: true, _removed_in: "fencers" }),
      row("reg:3", { _deleted: true, _merged_into: "reg:1" }),
    ];
    const active = rows.filter((r) => !r._deleted);
    expect(active).toHaveLength(1);
    for (const phase of ["fencers", "export"] as Phase[]) {
      expect(rowsForPhase(rows, phase).filter((r) => !r._deleted)).toEqual(active);
    }
  });
});

describe("the two manual-edits logs", () => {
  const edits = [edit("import", "imp:c1aa"), edit("fencers", "reg:7")];

  it("files a correction to a file under Import", () => {
    expect(editsForPhase(edits, "import").map((e) => e.target)).toEqual(["imp:c1aa"]);
  });

  it("files a decision about a fencer under the fencer list", () => {
    expect(editsForPhase(edits, "fencers").map((e) => e.target)).toEqual(["reg:7"]);
  });

  it("shows neither on a phase that owns neither", () => {
    expect(editsForPhase(edits, "export")).toEqual([]);
  });
});

describe("an absorbed row in the Import view", () => {
  it("says which row it was folded into", () => {
    const rows = [row("imp:d2bb", { _deleted: true, _merged_into: "reg:7" }), row("reg:7", { number: 4 })];
    expect(absorbedInto(rows[0], rows)).toBe(4);
  });

  it("says nothing on a row no merge touched", () => {
    expect(absorbedInto(row("imp:c1aa"), ROWS)).toBeNull();
  });
})

describe("what a row offers to have done to it", () => {
  it("offers to delete a live row", () => {
    expect(rowAction(row("reg:1"))).toBe("delete");
  });

  it("offers to bring back a deleted one", () => {
    expect(rowAction(row("reg:1", { _deleted: true, _removed_in: "fencers" }))).toBe("restore");
  });

  it("offers nothing on an absorbed row, whose removal is the merge's to undo", () => {
    // restoring it alone would leave it un-deleted and still merged
    expect(rowAction(row("imp:d2bb", { _deleted: true, _merged_into: "reg:7" }))).toBeNull();
  });

  it("offers to bring back every removed row a phase lists, and no other", () => {
    const rows = [
      row("reg:1"),
      row("reg:2", { _deleted: true, _removed_in: "fencers" }),
      row("reg:3", { _deleted: true, _removed_in: "payments" }),
    ];
    const restorable = (phase: Phase) =>
      rowsForPhase(rows, phase)
        .filter((r) => rowAction(r) === "restore")
        .map((r) => r.id);
    expect(restorable("fencers")).toEqual(["reg:2", "reg:3"]);
    expect(restorable("payments")).toEqual(["reg:3"]);
    expect(restorable("export")).toEqual([]);
  });
});

describe("the phases that draw no fencer table", () => {
  it("counts Deduplication among them", () => {
    // its work is a handful of rows out of fifty, and the table states it where
    // it is hardest to see (spec etl-console, Deduplication candidate review)
    for (const phase of ["setup", "dedup", "teams", "queue"] as Phase[]) {
      expect(PHASE_COLUMNS[phase]).toEqual([]);
    }
  });

  it("leaves every other processing phase its columns", () => {
    for (const phase of ["import", "fencers", "matching", "payments", "export"] as Phase[]) {
      expect(PHASE_COLUMNS[phase].length).toBeGreaterThan(0);
    }
  });
});

describe("which cells a phase opens for editing", () => {
  const identity = ["name", "nationality", "club"];

  it("holds identity read-only on the phases that read it off the profile", () => {
    for (const phase of ["dedup", "payments", "export"] as Phase[]) {
      for (const column of identity) {
        expect(editableHere(column, phase)).toBe(false);
      }
    }
  });

  it("keeps identity editable where it is claimed", () => {
    // Import, the fencer list, and Matching, where a correction belongs
    for (const phase of ["import", "fencers", "matching"] as Phase[]) {
      for (const column of identity) {
        expect(editableHere(column, phase)).toBe(true);
      }
    }
  });

  it("leaves the HRID cell editable wherever its column is drawn", () => {
    // a typed id is a verdict, and this change does not touch that.
    // Deduplication is not among them any more: it draws no columns at all.
    for (const phase of ["matching", "export"] as Phase[]) {
      expect(editableHere("hr_id", phase)).toBe(true);
    }
  });

  it("opens no cell that was never editable", () => {
    for (const column of ["notes", "problems", "state", "vs"]) {
      expect(editableHere(column, "fencers")).toBe(false);
    }
  });
});


describe("the payments columns", () => {
  it("states the balance beside the total", () => {
    // a part-paid reservation is legible in the table, not only in the
    // fencer's own view (spec `etl-console`)
    const columns = PHASE_COLUMNS.payments;
    expect(columns).toContain("outstanding");
    expect(columns.indexOf("outstanding")).toBe(columns.indexOf("total_amount") + 1);
  });

  it("keeps the fencer table, unlike Deduplication", () => {
    // Payments does something to every row, so the table is the right shape
    // for it; the queues sit above the table rather than replacing it
    expect(PHASE_COLUMNS.payments.length).toBeGreaterThan(0);
    expect(PHASE_COLUMNS.dedup).toEqual([]);
  });
});
