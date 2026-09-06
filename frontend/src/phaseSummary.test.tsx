// @vitest-environment jsdom
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import PhaseSummary from "./PhaseSummary";
import i18n from "./i18n";

/** The header line and the button behind it: what the phase says about its own
 *  outstanding work, and the one control that reads it again. */
function header(text: string | null): string {
  void i18n.changeLanguage("cs");
  return renderToStaticMarkup(<PhaseSummary text={text} onRefresh={() => {}} />);
}

describe("a phase's header line", () => {
  it("states the count beside the button", () => {
    const html = header("3 řádky čekají na verdikt");
    expect(html).toContain("3 řádky čekají na verdikt");
    expect(html).toContain("<button");
  });

  it("keeps the button where the phase has no line of its own", () => {
    const html = header(null);
    expect(html).toContain("<button");
    expect(html).not.toContain("phase-count");
  });

  it("names the button for a reader who cannot see the arrow", () => {
    expect(header(null)).toContain(`aria-label="${i18n.t("console.refresh")}"`);
  });
});
