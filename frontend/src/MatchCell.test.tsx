// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, describe, expect, it } from "vitest";

import type { SheetRow } from "./api";
import MatchCell from "./MatchCell";
import i18n from "./i18n";

// What the verdict register offers per verdict (spec `etl-console`, The ledger
// idiom): ratifying costs one click where there is a machine's proposal to
// ratify, and the search is reachable from every row whatever it reads.

const t = i18n.getFixedT("cs");

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let host: HTMLElement | null = null;

afterEach(() => {
  host?.remove();
  host = null;
});

function row(fields: Partial<SheetRow>): SheetRow {
  return {
    id: "imp:1",
    name: "Jan Novak",
    nationality: "CZ",
    club: null,
    hr_id: 10234,
    hr_name: "Jan Novák",
    hr_nationality: "CZE",
    hr_club: "Prague HEMA",
    disciplines: [],
    substitute_for: [],
    state: "imported",
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

/** Renders the cell and returns the actions it fired, in order. */
function render(fields: Partial<SheetRow>) {
  host = document.createElement("div");
  document.body.append(host);
  const calls: string[] = [];
  act(() =>
    createRoot(host as HTMLElement).render(
      <MatchCell
        row={row(fields)}
        onRatify={() => calls.push("ratify")}
        onSearch={() => calls.push("search")}
      />,
    ),
  );
  return calls;
}

function titled(title: string) {
  return host?.querySelector<HTMLButtonElement>(`button[title="${title}"]`) ?? null;
}

function click(button: HTMLButtonElement | null) {
  act(() => button?.click());
}

describe("the verdict cell", () => {
  it("ratifies a proposal on the badge itself", () => {
    const calls = render({ match_verdict: "proposed" });
    expect(host?.textContent).toContain(t("match.verdict.proposed"));
    click(titled(t("match.ratify")));
    expect(calls).toEqual(["ratify"]);
  });

  it("ratifies a found match too — the machine reached it, not the organizer", () => {
    const calls = render({ match_verdict: "found" });
    expect(host?.textContent).toContain(t("match.verdict.found"));
    click(titled(t("match.ratify")));
    expect(calls).toEqual(["ratify"]);
  });

  it("offers the search beside a ratifiable verdict", () => {
    const calls = render({ match_verdict: "proposed" });
    click(titled(t("match.search")));
    expect(calls).toEqual(["search"]);
  });

  it("opens the search from the badge where there is nothing to ratify", () => {
    for (const verdict of ["unknown", "none_found", "confirmed"] as const) {
      const calls = render({ match_verdict: verdict });
      expect(titled(t("match.search"))).toBe(null);
      click(titled(t("match.title")));
      expect(calls).toEqual(["search"]);
      host?.remove();
    }
  });

  it("has no proposal to ratify on a row carrying no id", () => {
    const calls = render({ match_verdict: "proposed", hr_id: null });
    expect(titled(t("match.search"))).toBe(null);
    click(titled(t("match.title")));
    expect(calls).toEqual(["search"]);
  });

  it("does nothing at all on a removed row", () => {
    const calls = render({ match_verdict: "proposed", _deleted: true });
    click(titled(t("match.ratify")));
    click(titled(t("match.search")));
    expect(calls).toEqual([]);
  });
});
