// @vitest-environment jsdom
import { describe, expect, it } from "vitest";

import type { NetChange, SheetRow } from "./api";
import {
  absorbedInto,
  DEFAULT_PHASE,
  editableHere,
  editsForPhase,
  PHASE_COLUMNS,
  PHASES,
  type Phase,
  parseDisciplines,
  phaseRemovesRows,
  phaseSummary,
  rowAction,
  rowsForPhase,
  ruleKindFor,
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

  it("lists the Import rows in arrival order, not that of the fencer list", () => {
    // the fencer list sorts by registration moment, which would scatter an
    // upload's rows; a reader checking an import against its source follows
    // the order the rows arrived, which is what the fixed number counts
    const scattered = [
      row("imp:c", { number: 52 }),
      row("imp:a", { number: 3 }),
      row("imp:b", { number: 40 }),
    ];
    expect(rowsForPhase(scattered, "import").map((r) => r.number)).toEqual([3, 40, 52]);
  });

  it("lists a row of an earlier upload beside one of the latest", () => {
    // uploads accumulate: a row is no less imported for having arrived first,
    // and one issued a registration carries no _source at all
    const across = [
      row("imp:new", { number: 9, _source: { file: "dodatek.csv", row: 1 } }),
      row("imp:old", { number: 2 }),
    ];
    expect(rowsForPhase(across, "import").map((r) => r.id)).toEqual(["imp:old", "imp:new"]);
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
    const rows = [
      row("imp:d2bb", { _deleted: true, _merged_into: "reg:7" }),
      row("reg:7", { number: 4 }),
    ];
    expect(absorbedInto(rows[0], rows)).toBe(4);
  });

  it("says nothing on a row no merge touched", () => {
    expect(absorbedInto(row("imp:c1aa"), ROWS)).toBeNull();
  });
});

describe("what a row offers to have done to it", () => {
  it("offers to delete a live row", () => {
    expect(rowAction(row("reg:1"), "fencers")).toBe("delete");
  });

  it("offers to bring back a deleted one", () => {
    expect(rowAction(row("reg:1", { _deleted: true, _removed_in: "fencers" }), "fencers")).toBe(
      "restore",
    );
  });

  it("offers nothing on an absorbed row, whose removal is the merge's to undo", () => {
    // restoring it alone would leave it un-deleted and still merged
    expect(
      rowAction(row("imp:d2bb", { _deleted: true, _merged_into: "reg:7" }), "dedup"),
    ).toBeNull();
  });

  it("offers nothing on the payments table, where fencers are not deleted", () => {
    // a delete at the end of a row about money reads as an action on the money
    expect(rowAction(row("reg:1"), "payments")).toBeNull();
  });

  it("removes rows on Import and the fencer list, and on no other phase", () => {
    // the answer the actions column is drawn from: a phase that offers nothing
    // draws no column rather than an empty one
    const removing = PHASES.filter(phaseRemovesRows);
    expect(removing).toEqual(["import", "fencers"]);
    for (const phase of PHASES.filter((p) => !phaseRemovesRows(p))) {
      expect(rowAction(row("reg:1"), phase)).toBeNull();
    }
  });

  it("offers to bring back every removed row a phase lists, and no other", () => {
    const rows = [
      row("reg:1"),
      row("reg:2", { _deleted: true, _removed_in: "fencers" }),
      row("reg:3", { _deleted: true, _removed_in: "payments" }),
    ];
    const restorable = (phase: Phase) =>
      rowsForPhase(rows, phase)
        .filter((r) => rowAction(r, phase) === "restore")
        .map((r) => r.id);
    expect(restorable("fencers")).toEqual(["reg:2", "reg:3"]);
    // Payments offers nothing on a row at all; a row removed there is still
    // listed, and is brought back from the phase the roster is worked on
    expect(restorable("payments")).toEqual([]);
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
    // Import and the fencer list, where a correction belongs
    for (const phase of ["import", "fencers"] as Phase[]) {
      for (const column of identity) {
        expect(editableHere(column, phase)).toBe(true);
      }
    }
  });

  it("closes the claim on Matching, which compares it rather than corrects it", () => {
    // the claim is the text the evidence is read against: editing it there
    // moves the answer while the question is being asked
    for (const column of identity) {
      expect(editableHere(column, "matching")).toBe(false);
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

  it("opens disciplines on the fencer list", () => {
    expect(editableHere("disciplines", "fencers")).toBe(true);
  });

  it("opens disciplines whether or not a registration stands behind the row", () => {
    // what the edit *does* follows from the registration; whether the cell
    // opens does not. Issuing is a step of payment intake, so a cell closed on
    // a row with a registration is a cell that never opens at all
    expect(ruleKindFor("disciplines", row("imp:a1"))).toBe("field_edit");
    expect(ruleKindFor("disciplines", row("imp:a1", { registration_id: 7 }))).toBe(
      "registration_amendment",
    );
  });

  it("opens the rentals cell on the fencer list and nowhere else", () => {
    // what a row borrows is priced, so a rentals cell that cannot be corrected
    // is a wrong total with no remedy in the console
    expect(editableHere("weapon_rentals", "fencers")).toBe(true);
    for (const phase of ["import", "matching", "payments", "export"] as Phase[]) {
      expect(editableHere("weapon_rentals", phase)).toBe(false);
    }
  });

  it("amends the registration where one stands behind a rentals edit", () => {
    expect(ruleKindFor("weapon_rentals", row("imp:a1"))).toBe("field_edit");
    expect(ruleKindFor("weapon_rentals", row("imp:a1", { registration_id: 7 }))).toBe(
      "registration_amendment",
    );
  });

  it("opens disciplines on no other phase", () => {
    for (const phase of ["import", "matching", "payments", "export"] as Phase[]) {
      expect(editableHere("disciplines", phase)).toBe(false);
    }
  });
});

describe("reading the disciplines typed into a cell", () => {
  it("takes commas, semicolons and spaces alike", () => {
    expect(parseDisciplines("SA, SB")).toEqual(["SA", "SB"]);
    expect(parseDisciplines("SA;SB")).toEqual(["SA", "SB"]);
    expect(parseDisciplines("SA  SB")).toEqual(["SA", "SB"]);
  });

  it("keeps the slug's own case, since a slug is an identity", () => {
    expect(parseDisciplines("sa")).toEqual(["sa"]);
  });

  it("does not repeat one entered twice", () => {
    expect(parseDisciplines("SA, SA")).toEqual(["SA"]);
  });

  it("reads an emptied cell as nothing entered", () => {
    expect(parseDisciplines("   ")).toEqual([]);
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

describe("what a phase states beside its title", () => {
  it("counts the rows Import could not read cleanly", () => {
    const rows = [
      row("imp:a1", { problems: "no email" }),
      row("imp:a2", { problems: null }),
      row("imp:a3", { problems: "   " }),
    ];
    expect(phaseSummary("import", rows)).toEqual({
      key: "console.summary.problems",
      count: 1,
    });
  });

  it("asks the fencer list the same question, since issuing no longer clears the flag", () => {
    const rows = [
      row("imp:a1", { registration_id: 7, problems: "afterparty answer ambiguous" }),
      row("imp:a2", { registration_id: 8 }),
    ];
    expect(phaseSummary("fencers", rows)).toEqual({
      key: "console.summary.problems",
      count: 1,
    });
  });

  it("counts the rows Matching still owes a verdict, a proposal being no verdict", () => {
    const rows = [
      row("imp:a1", { match_verdict: "confirmed" }),
      row("imp:a2", { match_verdict: "none_found" }),
      row("imp:a3", { match_verdict: "proposed" }),
      row("imp:a4"),
    ];
    expect(phaseSummary("matching", rows)?.count).toBe(2);
  });

  it("does not count a settled-by-hand row as unpaid: the money reached the organizer", () => {
    const rows = [
      row("imp:a1", { paid: true }),
      row("imp:a2", { paid: false, settled_by_hand: true }),
      row("imp:a3", { paid: false }),
    ];
    expect(phaseSummary("payments", rows)?.count).toBe(1);
  });

  it("counts nothing that has been deleted, on any phase", () => {
    const rows = [
      row("imp:a1", { problems: "no email", _deleted: true }),
      row("imp:a2", { problems: "no email" }),
    ];
    expect(phaseSummary("import", rows)?.count).toBe(1);
  });

  it("states zero rather than falling silent", () => {
    // a header that appeared only when there was work would move the title
    // every time the last decision was made
    expect(phaseSummary("matching", [row("imp:a1", { match_verdict: "confirmed" })])).toEqual({
      key: "console.summary.unverdicted",
      count: 0,
    });
  });

  it("gives Export no line, which leaves it the button alone", () => {
    expect(phaseSummary("export", [row("imp:a1")])).toBeNull();
  });
});
