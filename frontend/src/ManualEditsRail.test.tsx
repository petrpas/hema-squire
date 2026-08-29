// @vitest-environment jsdom
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { NetChange, SheetRow } from "./api";
import ManualEditsRail, { entryText } from "./ManualEditsRail";
import { rowsForPhase } from "./Console";
import i18n from "./i18n";

// What an entry of the manual-edits log says (spec `etl-console`, Readable
// manual-edits log): the row as the table numbers it, and the change in the
// organizer's words rather than in field assignments over a row id.

function row(id: string, name: string, number: number | null = null): SheetRow {
  return {
    id,
    number,
    name,
    nationality: null,
    club: null,
    hr_id: null,
    hr_name: null,
    hr_nationality: null,
    hr_club: null,
    disciplines: [],
    substitute_for: [],
    state: "reserved",
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
  } as SheetRow;
}

// numbers deliberately unlike the rows' positions: an entry names the fencer's
// fixed number, never where the row happens to sit
const ROWS = [row("imp:c1aa", "Jan Novák", 31), row("reg:7", "Petra Malá", 4)];

function entry(fields: Partial<NetChange>): NetChange {
  return {
    phase: "import",
    target: "imp:c1aa",
    field: "club",
    before: null,
    after: "SK Praha",
    rule_ids: [4],
    actor: "Petr Paščenko",
    at: "2026-08-28T18:41:00+00:00",
    ...fields,
  };
}

function text(fields: Partial<NetChange>, language = "cs"): string {
  const t = i18n.getFixedT(language);
  return entryText(entry(fields), ROWS, "Europe/Prague", t as never);
}

describe("manual-edits entry", () => {
  it("names the row by its fixed number and the fencer on it", () => {
    expect(text({})).toBe("#31 Jan Novák — Klub: — → SK Praha");
    expect(text({}, "en")).toBe("#31 Jan Novák — Club: — → SK Praha");
  });

  it("keeps naming the same fencer when rows above are removed", () => {
    const t = i18n.getFixedT("cs");
    const shortened = ROWS.slice(1);
    const before = entryText(entry({ target: "reg:7" }), ROWS, null, t as never);
    const after = entryText(entry({ target: "reg:7" }), shortened, null, t as never);
    expect(before).toContain("#4 Petra Malá");
    expect(after).toContain("#4 Petra Malá");
  });

  it("states a deletion as a deletion, not as a _deleted assignment", () => {
    const line = text({ field: "_deleted", before: false, after: true });
    expect(line).toBe("#31 Jan Novák — řádek smazán");
    expect(line).not.toContain("_deleted");
  });

  it("states a merge by naming the surviving row", () => {
    expect(text({ field: "_merged_into", before: null, after: "reg:7" })).toBe(
      "#31 Jan Novák — sloučeno do #4 Petra Malá",
    );
  });

  it("names a row the table no longer holds instead of showing its id", () => {
    const line = text({ target: "imp:gone" });
    expect(line).not.toContain("imp:gone");
    expect(line).toContain("řádek už v tabulce není");
  });

  it("renders values as the table renders them", () => {
    expect(text({ field: "match_verdict", before: "unknown", after: "confirmed" })).toContain(
      "nespárováno → potvrzeno",
    );
    expect(text({ field: "disciplines", before: [], after: ["LS", "RAP"] })).toContain(
      "— → LS, RAP",
    );
  });
});

describe("manual-edits rail", () => {
  it("lets no raw row id reach the log", () => {
    const markup = renderToStaticMarkup(
      <ManualEditsRail
        entries={[entry({}), entry({ target: "reg:7", field: "_deleted", after: true })]}
        rows={ROWS}
        timezone="Europe/Prague"
        onUndo={() => {}}
      />,
    );
    expect(markup).not.toContain("imp:c1aa");
    expect(markup).not.toContain("reg:7");
    expect(markup).toContain("Jan Novák");
    expect(markup).toContain("Petra Malá");
  });
});

describe("an entry naming a row the phase does not list", () => {
  it("still names the fencer, since undoing it is what brings the row back", () => {
    // deleted on Import, the row is gone from the Fencers table; the entry that
    // removed it must still say who it was
    const rows = [
      row("imp:c1aa", "Jan Novák", 31),
      row("reg:7", "Petra Malá", 4),
    ].map((r) =>
      r.id === "imp:c1aa" ? ({ ...r, _deleted: true, _removed_in: "import" } as SheetRow) : r,
    );
    expect(rowsForPhase(rows, "fencers").map((r) => r.id)).toEqual(["reg:7"]);

    // the rail receives the full row set, not the phase's view
    const t = i18n.getFixedT("cs");
    const line = entryText(
      { ...entry({ field: "_deleted", before: false, after: true }) },
      rows,
      null,
      t as never,
    );
    expect(line).toBe("#31 Jan Novák — řádek smazán");
  });
});
