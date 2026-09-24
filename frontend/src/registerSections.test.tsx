// @vitest-environment jsdom
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { ExtraItem, RegistrationDetail, TournamentDetail } from "./api";
import i18n from "./i18n";
import { RegistrationForm } from "./TournamentFace";

// The headings a fencer reads down the register form, rendered from the real
// locale bundles — the point of the change is that a goods row is explained by
// the section it sits under (design `goods-sections-by-category`, task 2.2).

let nextId = 1;

function item(name: string, category: ExtraItem["category"]): ExtraItem {
  return {
    id: nextId++,
    name,
    category,
    price: 50,
    price_eur: null,
    max_qty: 1,
    schedule_when: null,
    schedule_where: null,
    remark: null,
    option_label: null,
    option_choices: [],
  };
}

function headings(extraItems: ExtraItem[], language: string): string[] {
  void i18n.changeLanguage(language);
  const detail = {
    slug: "na-duel-2026",
    display_name: "Na Duel! 2026",
    subtitle: null,
    language: "cs",
    local_currency: "CZK",
    currency_mode: "local",
    eur_payments_enabled: false,
    registration_instructions: null,
    team_composition_deadline: null,
    disciplines: [],
    discounts: [],
    extra_items: extraItems,
  } as unknown as TournamentDetail;
  const html = renderToStaticMarkup(
    <RegistrationForm detail={detail} availability={[]} mode={{ kind: "preview" }} />,
  );
  return [...html.matchAll(/class="register-section">([^<]*)</g)].map((match) => match[1]!);
}

describe("register form sections", () => {
  it("heads each goods category with its own name, in render order", () => {
    expect(
      headings(
        [item("Tričko turnaje", "merch"), item("Šavle", "rental"), item("Parkovné", "other_item")],
        "cs",
      ),
    ).toEqual(["Turnaj", "Zapůjčení vybavení", "Merch", "Ostatní zboží", "Ostatní"]);
  });

  it("gives a lending-only tournament one goods heading naming the lending", () => {
    expect(headings([item("Šavle", "rental"), item("Meč", "rental")], "cs")).toEqual([
      "Turnaj",
      "Zapůjčení vybavení",
      "Ostatní",
    ]);
  });

  it("keeps the actions together under the one programme heading", () => {
    expect(
      headings([item("Páteční seminář", "seminar"), item("Afterparty", "afterparty")], "cs"),
    ).toEqual(["Turnaj", "Volitelný program", "Ostatní"]);
  });

  it("heads the goods in English too", () => {
    expect(headings([item("Sabre", "rental"), item("T-shirt", "merch")], "en")).toEqual([
      "Tournament",
      "Equipment rental",
      "Merch",
      "Other",
    ]);
  });
});

describe("the participation condition tick", () => {
  function form(entries: { slug: string; conditional: boolean }[]): string {
    void i18n.changeLanguage("cs");
    const discipline = (slug: string) => ({
      slug,
      name: slug,
      kind: "individual",
      capacity: 10,
      fee: 1000,
      fee_eur: null,
      schedule_when: null,
      schedule_where: null,
    });
    const detail = {
      slug: "cup",
      display_name: "Cup",
      subtitle: null,
      language: "cs",
      local_currency: "CZK",
      currency_mode: "local",
      eur_payments_enabled: false,
      registration_instructions: null,
      team_composition_deadline: null,
      disciplines: [discipline("LS"), discipline("SA")],
      discounts: [],
      extra_items: [],
    } as unknown as TournamentDetail;
    const initial = {
      entries: entries.map((entry) => ({ ...entry, is_substitute: false, queue_position: null })),
      teams: [],
      extras: [],
      weapon_rentals: [],
      afterparty: false,
      notes: null,
      total_amount: 0,
      total_eur: null,
    } as unknown as RegistrationDetail;
    return renderToStaticMarkup(
      <RegistrationForm
        detail={detail}
        availability={[]}
        mode={{ kind: "amend", initial, onRegistered: () => {} }}
      />,
    );
  }

  it("is not offered for one individual discipline", () => {
    expect(form([{ slug: "LS", conditional: false }])).not.toContain("Pojedu jen, pokud");
  });

  it("is offered, unticked, from two, stating its consequence", () => {
    const html = form([
      { slug: "LS", conditional: false },
      { slug: "SA", conditional: false },
    ]);
    expect(html).toContain("Pojedu jen, pokud dostanu místo ve všech vybraných disciplínách");
    expect(html).toContain("čekáš ve frontě na všechny");
    expect(html).not.toMatch(/type="checkbox" checked=""[^>]*\/><span>Pojedu/);
  });

  it("stands ticked on an amendment of a registration carrying a condition", () => {
    const html = form([
      { slug: "LS", conditional: true },
      { slug: "SA", conditional: true },
    ]);
    expect(html).toMatch(/checked=""[^>]*\/><span>Pojedu jen/);
  });
});
