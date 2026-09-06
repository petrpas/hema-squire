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

/** A money cell, with the currency context the Payments phase passes in
 *  (design add-payments-console-ui D5). */
function moneyCell(
  column: string,
  fields: Partial<SheetRow>,
  currency: { local_currency: "CZK" | "EUR"; eur_payments_enabled: boolean } | null = {
    local_currency: "CZK",
    eur_payments_enabled: false,
  },
): string {
  return renderToStaticMarkup(
    <CellDisplay row={row(fields)} column={column} timezone={null} currency={currency} />,
  );
}

/** An identity cell as a phase after matching draws it (spec `etl-console`,
 *  HR identity in the phases after matching). */
function identityCell(column: string, fields: Partial<SheetRow>): string {
  return renderToStaticMarkup(
    <CellDisplay row={row(fields)} column={column} timezone={null} hrIdentity />,
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

  it("records a disciplines edit as an amendment where a registration stands behind the row", () => {
    // the registration's entries decide what it is billed and where it is
    // seated, so the edit moves both or neither (spec `discipline-amendment`)
    expect(ruleKindFor("disciplines", row({ registration_id: 7 }))).toBe(
      "discipline_amendment",
    );
    expect(ruleKindFor("disciplines", row({}))).toBe("field_edit");
  });
});

describe("an identity cell after matching", () => {
  const REGISTERED = { name: "Lukáš Müller", nationality: "DE", club: "Berlin" };
  const PROFILE = {
    hr_id: 8821,
    hr_name: "Lukas Mueller",
    hr_nationality: "DE",
    hr_club: "Berlin Schwert",
  };

  it("states the fencer's own words in italic while no profile is bound", () => {
    expect(identityCell("club", REGISTERED)).toBe(
      '<span class="identity-declared">Berlin</span>',
    );
  });

  it("states the profile's words, unmarked, once the match is resolved", () => {
    // the same row after the organizer bound an id on Matching
    expect(identityCell("club", { ...REGISTERED, ...PROFILE })).toBe("Berlin Schwert");
    expect(identityCell("name", { ...REGISTERED, ...PROFILE })).toBe("Lukas Mueller");
  });

  it("draws no italic on a phase that identifies by the registered values", () => {
    expect(cell("club", REGISTERED, null)).toBe("Berlin");
  });
});


describe("money cells", () => {
  it("states the outstanding balance with its unit", () => {
    expect(moneyCell("outstanding", { outstanding_amount: "400.00" })).toBe("400 Kč");
  });

  it("states the balance in one currency even where the tournament takes both", () => {
    // the two lanes are alternative prices, so the lane nobody paid into is
    // not a second debt: printed as a pair it read as a conversion, and a
    // fencer who had paid in full was shown "0 Kč (45 €)"
    expect(
      moneyCell(
        "outstanding",
        { outstanding_amount: "400.00", outstanding_currency: "CZK" },
        { local_currency: "CZK", eur_payments_enabled: true },
      ),
    ).toBe("400 Kč");
  });

  it("states the balance in the lane the money arrived in", () => {
    expect(
      moneyCell(
        "outstanding",
        { outstanding_amount: "16.00", outstanding_currency: "EUR" },
        { local_currency: "CZK", eur_payments_enabled: true },
      ),
    ).toBe("16 €");
  });

  it("names what a partial waiver forgave, not the bare word", () => {
    // a fencer who paid 1 250 Kč of 1 750 Kč and had the rest written off is
    // not the same fact as one who paid nothing (owner decision, 2026-09-06)
    const html = moneyCell("outstanding", {
      outstanding_amount: "0.00",
      settled_by_hand: true,
      settled_by_hand_reason: null,
      waived_amount: "500.00",
      outstanding_currency: "CZK",
    });
    expect(html).toContain("odpuštěno 500 Kč");
  });

  it("says the whole price was forgiven where nothing had been credited", () => {
    const html = moneyCell("outstanding", {
      outstanding_amount: "0.00",
      settled_by_hand: true,
      settled_by_hand_reason: null,
      waived_amount: null,
    });
    expect(html).toContain("odpuštěno vše");
  });

  it("names no sum where the money had already covered the price", () => {
    // the waiver forgave nothing, so there is nothing to name
    const html = moneyCell("outstanding", {
      outstanding_amount: "0.00",
      settled_by_hand: true,
      settled_by_hand_reason: null,
      waived_amount: "0.00",
    });
    expect(html).toContain("odpuštěno");
    expect(html).not.toContain("odpuštěno vše");
    expect(html).not.toContain("0 Kč");
  });

  it("reads a waived balance as the words alone, with the reason on hover", () => {
    // an organizer's reason runs as long as a sentence — "volný vstup za čtvrté
    // místo dosažené v loňském roce" — and a money column set to the width of
    // the longest one stops being a money column
    const html = moneyCell("outstanding", {
      outstanding_amount: "1750.00",
      settled_by_hand: true,
      settled_by_hand_reason: "volný vstup za čtvrté místo dosažené v loňském roce",
    });
    expect(html).toContain("odpuštěno vše");
    // the figure it would otherwise owe is gone: nothing was credited and
    // nothing is due, so it is true of neither
    expect(html).not.toContain("1750");
    // the reason is present but in the hint box, not in the cell's own line
    expect(html).toContain("help-hint-box");
    expect(html).toContain("volný vstup za čtvrté místo");
  });

  it("marks nothing on a waiver given without a reason", () => {
    // there is nothing to open, so no marker is drawn
    const html = moneyCell("outstanding", {
      outstanding_amount: "1750.00",
      settled_by_hand: true,
      settled_by_hand_reason: null,
    });
    expect(html).toContain("odpuštěno");
    expect(html).not.toContain("help-hint-box");
  });

  it("gives the total a unit, which it rendered without before", () => {
    // grouped for the locale: the separator is a non-breaking space
    expect(moneyCell("total_amount", { total_amount: 1000 })).toBe("1\u00a0000 Kč");
  });

  it("reads a dash where no registration stands behind the row", () => {
    // an imported row owes nothing; a zero would be a figure it never agreed to
    expect(moneyCell("outstanding", {})).toBe("—");
    expect(moneyCell("total_amount", { total_amount: null })).toBe("—");
  });

  it("states the bare figure until the tournament detail has arrived", () => {
    // unitless beats wrongly-united: the currency is not known yet
    expect(moneyCell("outstanding", { outstanding_amount: "400.00" }, null)).toBe("400.00");
  });

  it("settles to zero rather than to a dash once fully paid", () => {
    expect(moneyCell("outstanding", { outstanding_amount: "0.00" })).toBe("0 Kč");
  });
});
