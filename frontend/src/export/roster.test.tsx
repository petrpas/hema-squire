// @vitest-environment jsdom
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { ExportTab, SheetRow } from "../api";
import i18n from "../i18n";
import { activeOnly } from "./ordering";
import { rosterPrint } from "./roster";
import TableOperations from "./TableOperations";

// The printed discipline roster: which actions the rail card offers, and that
// what is sent to be typeset is the tab as it stands (spec roster-print).

const t = i18n.getFixedT(i18n.language);
const en = i18n.getFixedT("en");

function row(id: string, name: string, fields: Partial<SheetRow> = {}): SheetRow {
  return {
    id,
    name,
    nationality: "CZE",
    club: "Klub",
    hr_id: null,
    disciplines: ["SA"],
    substitute_for: [],
    queued_since: {},
    paid: false,
    ...fields,
  } as SheetRow;
}

const sabre: ExportTab = {
  kind: "discipline",
  key: "SA",
  label: "Sabre Open",
  capacity: 2,
  line: "queue",
};

const card = (discipline: boolean) =>
  renderToStaticMarkup(
    <TableOperations
      title="Sabre Open"
      onCopy={() => {}}
      print={discipline ? { onPrint: () => {}, printing: null } : undefined}
      refreshing={false}
      ratingsMessage={null}
      message={null}
    />,
  );

describe("the rail card's actions", () => {
  it("offers the copy as an icon with a hint, not a text button, on every tab", () => {
    for (const html of [card(false), card(true)]) {
      const page = new DOMParser().parseFromString(html, "text/html");
      const copy = [...page.querySelectorAll(".export-actions button")].find((button) =>
        button.textContent?.includes(t("export.copy")),
      );
      expect(copy?.querySelector("svg")).not.toBeNull();
      expect(copy?.querySelector(".visually-hidden")?.textContent).toBe(t("export.copy"));
      const hint = page.getElementById(copy?.getAttribute("aria-describedby") ?? "");
      expect(hint?.textContent).toBe(t("export.hints.copy"));
    }
  });

  it("offers PDF and PNG on a discipline only, in the copy's row", () => {
    const names = (html: string) =>
      [
        ...new DOMParser()
          .parseFromString(html, "text/html")
          .querySelectorAll(".export-actions .visually-hidden"),
      ].map((name) => name.textContent);
    expect(names(card(false))).toEqual([t("export.copy")]);
    expect(names(card(true))).toEqual([t("export.copy"), t("export.pdf"), t("export.png")]);
  });

  it("puts the ratings refresh between the copy and the printouts, its scope in its hint", () => {
    const html = renderToStaticMarkup(
      <TableOperations
        title="Sabre Open"
        onCopy={() => {}}
        onRefreshRatings={() => {}}
        print={{ onPrint: () => {}, printing: null }}
        refreshing={false}
        ratingsMessage={null}
        message={null}
      />,
    );
    const page = new DOMParser().parseFromString(html, "text/html");
    const buttons = [...page.querySelectorAll(".export-actions button")];
    expect(buttons.map((button) => button.textContent)).toEqual([
      t("export.copy"),
      t("export.fetchRatings"),
      t("export.pdf"),
      t("export.png"),
    ]);
    const hint = page.getElementById(buttons[1]?.getAttribute("aria-describedby") ?? "");
    expect(hint?.textContent).toBe(t("export.hints.fetchRatings"));
  });

  it("holds back the format being typeset, and only it", () => {
    const html = renderToStaticMarkup(
      <TableOperations
        title="Sabre Open"
        onCopy={() => {}}
        print={{ onPrint: () => {}, printing: "png" }}
        refreshing={false}
        ratingsMessage={null}
        message={null}
      />,
    );
    const page = new DOMParser().parseFromString(html, "text/html");
    const disabled = [...page.querySelectorAll(".export-actions button:disabled")];
    expect(disabled.map((button) => button.textContent)).toEqual([t("export.png")]);
  });
});

describe("the roster sent to be typeset", () => {
  const low = row("reg:1", "Low One", { ratings: { SA: 1000 }, paid: true } as Partial<SheetRow>);
  const high = row("reg:2", "High Two", { ratings: { SA: 1500 } } as Partial<SheetRow>);
  const mid = row("reg:3", "Mid Three", { ratings: { SA: 1200 }, paid: true } as Partial<SheetRow>);
  const queued = row("reg:4", "Queued Four", {
    disciplines: [],
    substitute_for: ["SA"],
    queued_since: { SA: "2026-09-01T10:00:00Z" },
    paid: true,
  });
  const rows = [low, high, mid, queued];

  it("lists the tab's rows in seeding order, numbered as on screen, with the line", () => {
    const body = rosterPrint(t, rows, sabre, true, false);
    expect(body.rows.map((cells) => cells.slice(0, 2))).toEqual([
      ["1", "High Two"],
      ["2", "Mid Three"],
      ["3", "Low One"],
      ["4", "Queued Four"],
    ]);
    expect(body.line_after).toBe(3);
    expect(body.discipline).toBe("SA");
  });

  it("follows the active-only switch", () => {
    const body = rosterPrint(t, activeOnly(rows, true), sabre, false, false);
    expect(body.rows.map((cells) => [cells[0], cells[1]])).toEqual([
      ["1", "Low One"],
      ["2", "Mid Three"],
      ["3", "Queued Four"],
    ]);
  });

  it("carries the seven printed cells, the paid in the language asked for", () => {
    const body = rosterPrint(en, [low], { ...sabre, capacity: 10 }, false, true);
    expect(body.rows).toEqual([["1", "Low One", "CZE", "Klub", "", "", en("export.yes")]]);
    expect(body.line_after).toBeNull();
    expect(body.english).toBe(true);
  });
});
