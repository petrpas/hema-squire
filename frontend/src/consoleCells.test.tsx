// @vitest-environment jsdom
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { SheetRow } from "./api";
import { CellDisplay, ruleKindFor } from "./Console";

// What the fencer table's Registered column states (spec `etl-console`,
// Registration moment in the fencer table). The neighbouring day columns are
// checked too, since the change deliberately leaves them as days.

function row(fields: Partial<SheetRow>): SheetRow {
  return {
    id: "reg:1",
    name: "Jan Novák",
    nationality: null,
    club: null,
    hr_id: null,
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
    ...fields,
  } as SheetRow;
}

function cell(column: string, fields: Partial<SheetRow>, timezone: string | null): string {
  return renderToStaticMarkup(
    <CellDisplay row={row(fields)} column={column} timezone={timezone} />,
  );
}

describe("registered cell", () => {
  it("states the day and the clock in the tournament's zone", () => {
    expect(
      cell("registered_at", { registered_at: "2026-03-14T13:32:52+00:00" }, "Europe/Prague"),
    ).toBe("14. 3. 2026 14:32");
  });

  it("shows an imported row's zone-less stamp unshifted", () => {
    expect(
      cell("registered_at", { registered_at: "2026-03-14T09:07:00" }, "Pacific/Auckland"),
    ).toBe("14. 3. 2026 09:07");
  });

  it("keeps the em dash where nothing was recorded", () => {
    expect(cell("registered_at", {}, "Europe/Prague")).toBe("—");
  });

  it("leaves the payment day columns as days", () => {
    expect(cell("paid_at", { paid_at: "2026-03-14T13:32:52+00:00" }, "Europe/Prague")).toBe(
      "14. 3. 2026",
    );
    expect(cell("expires_at", { expires_at: "2026-03-21T13:32:52+00:00" }, "Europe/Prague")).toBe(
      "21. 3. 2026",
    );
  });
});

describe("an edited cell", () => {
  it("records a typed HR id as a verdict, not as a correction", () => {
    expect(ruleKindFor("hr_id")).toBe("match_resolution");
  });

  it("records every other cell as the organizer's correction", () => {
    for (const column of ["name", "nationality", "club"]) {
      expect(ruleKindFor(column)).toBe("field_edit");
    }
  });
});
