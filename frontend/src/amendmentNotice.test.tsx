// @vitest-environment jsdom
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import AmendmentNotice from "./AmendmentNotice";
import i18n from "./i18n";

/** What the organizer is told after a discipline correction: the half of the
 *  edit the cell cannot show — what it cost, and whether a letter went out
 *  (spec `discipline-amendment`). */
function notice(props: Parameters<typeof AmendmentNotice>[0]): string {
  void i18n.changeLanguage("en");
  return renderToStaticMarkup(<AmendmentNotice {...props} />);
}

describe("what a discipline correction reports", () => {
  it("states the price either side of the correction", () => {
    const html = notice({
      amendment: { previous_total: "800", total: "1300", notified: true },
      refusal: null,
      currency: "CZK",
    });
    expect(html).toContain("800");
    expect(html).toContain("1\u00a0300");
  });

  it("says a letter went out only where one did", () => {
    const dearer = notice({
      amendment: { previous_total: "800", total: "1300", notified: true },
      refusal: null,
      currency: "CZK",
    });
    const cheaper = notice({
      amendment: { previous_total: "1300", total: "800", notified: false },
      refusal: null,
      currency: "CZK",
    });
    expect(dearer).not.toBe(cheaper);
    expect(dearer).toContain("surcharge");
    expect(cheaper).toContain("No mail");
  });

  it("states a refusal rather than leaving the cell to look saved", () => {
    const html = notice({
      amendment: null,
      refusal: "registration_not_live",
      currency: "CZK",
    });
    expect(html).toContain("no longer live");
  });

  it("shows nothing at all until an edit has been made", () => {
    expect(notice({ amendment: null, refusal: null, currency: "CZK" })).toBe("");
  });
});
