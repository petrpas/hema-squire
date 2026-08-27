import { describe, expect, it } from "vitest";

import type { ExtraCategory, ExtraItem } from "./api";
import { groupGoods, isAction } from "./extraItems";

// The organizer's category is what heads a goods section on the register form,
// so the grouping is the whole of that screen's structure (design
// `goods-sections-by-category`, task 1.3).

let nextId = 1;

function item(name: string, category: ExtraCategory): ExtraItem {
  return {
    id: nextId++,
    name,
    category,
    price: 5000,
    price_eur: null,
    max_qty: 1,
    schedule_when: null,
    schedule_where: null,
    remark: null,
    option_label: null,
    option_choices: [],
  };
}

describe("groupGoods", () => {
  it("gives each item category its own group, in render order", () => {
    const groups = groupGoods([
      item("Tričko", "merch"),
      item("Parkovné", "other_item"),
      item("Šavle", "rental"),
    ]);
    expect(groups.map((group) => group.category)).toEqual(["rental", "merch", "other_item"]);
    expect(groups.map((group) => group.items.map((i) => i.name))).toEqual([
      ["Šavle"],
      ["Tričko"],
      ["Parkovné"],
    ]);
  });

  it("omits a category with no rows", () => {
    const groups = groupGoods([item("Tričko", "merch")]);
    expect(groups.map((group) => group.category)).toEqual(["merch"]);
  });

  it("gives a lending-only tournament exactly one group", () => {
    const groups = groupGoods([
      item("Šavle", "rental"),
      item("Meč", "rental"),
      item("Puklíř", "rental"),
    ]);
    expect(groups).toHaveLength(1);
    expect(groups[0].category).toBe("rental");
    expect(groups[0].items).toHaveLength(3);
  });

  it("keeps the tournament's row order within a group", () => {
    const groups = groupGoods([
      item("Šavle", "rental"),
      item("Tričko", "merch"),
      item("Meč", "rental"),
      item("Puklíř", "rental"),
    ]);
    expect(groups[0].items.map((i) => i.name)).toEqual(["Šavle", "Meč", "Puklíř"]);
  });

  it("leaves the programme's categories out of every group", () => {
    const groups = groupGoods([
      item("Seminář", "seminar"),
      item("Afterparty", "afterparty"),
      item("Prohlídka města", "other_action"),
    ]);
    expect(groups).toEqual([]);
  });

  it("yields nothing for a tournament offering no extras at all", () => {
    expect(groupGoods([])).toEqual([]);
  });
});

describe("isAction", () => {
  it.each<[ExtraCategory, boolean]>([
    ["seminar", true],
    ["afterparty", true],
    ["other_action", true],
    ["rental", false],
    ["merch", false],
    ["other_item", false],
  ])("places %s", (category, expected) => {
    expect(isAction(item("x", category))).toBe(expected);
  });
});
