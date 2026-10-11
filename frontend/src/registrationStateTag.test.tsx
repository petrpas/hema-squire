// @vitest-environment jsdom
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { FencerTournament, RegistrationDetail } from "./api";
import i18n from "./i18n";
import { RegistrationStateTag } from "./TournamentDetail";

// A payments-off tournament reads a reservation as confirmed; one waiting
// entirely in the queue holds a place nowhere and must not (spec fencer-home,
// "A payments-off registration presents no money to settle").

function tag(substitutes: boolean[], featurePayments: boolean): string {
  void i18n.changeLanguage("cs");
  const registration = {
    state: "reserved",
    vs: null,
    registered_at: "2026-10-01T10:00:00Z",
    entries: substitutes.map((is_substitute, index) => ({
      slug: `d${index}`,
      is_substitute,
      queue_position: is_substitute ? index + 1 : null,
      conditional: true,
    })),
    teams: [],
  } as unknown as RegistrationDetail;
  const detail = { feature_payments: featurePayments } as unknown as FencerTournament;
  return renderToStaticMarkup(<RegistrationStateTag registration={registration} detail={detail} />);
}

describe("the registration state tag", () => {
  it("reads a payments-off registration waiting in every queue as substitute", () => {
    const html = tag([true, true], false);
    expect(html).toContain("Náhradník");
    expect(html).not.toContain("Zaplaceno");
  });

  it("reads one waiting in every queue as substitute with payments on too", () => {
    expect(tag([true, true], true)).toContain("Náhradník");
  });

  it("still reads a payments-off registration holding a seat as confirmed", () => {
    expect(tag([false, true], false)).toContain("Zaplaceno");
  });
});
