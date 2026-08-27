import type { ExtraCategory, ExtraItem } from "./api";

// The two halves of `ExtraCategory`, mirroring the backend's ACTION_CATEGORIES.
// Action categories happen at a time and place: they are shown as informational
// "other actions" on the information screen — where gear lending and merch are
// deliberately omitted — and grouped as the optional programme on the register
// screen. Item categories are goods, and each heads its own register-form
// section, in the order spelled out here.
export const ACTION_CATEGORIES = ["seminar", "afterparty", "other_action"] as const;
export const ITEM_CATEGORIES = ["rental", "merch", "other_item"] as const;

// Both halves are named rather than one being "whatever the other is not", so
// a seventh category has to be placed by hand: this assertion stops compiling
// the moment their union stops covering `ExtraCategory`.
type Covered = (typeof ACTION_CATEGORIES)[number] | (typeof ITEM_CATEGORIES)[number];
type Uncovered = Exclude<ExtraCategory, Covered> | Exclude<Covered, ExtraCategory>;
const _everyCategoryIsPlaced: [Uncovered] extends [never] ? true : never = true;
void _everyCategoryIsPlaced;

export function isAction(item: ExtraItem): boolean {
  return ACTION_CATEGORIES.includes(item.category as (typeof ACTION_CATEGORIES)[number]);
}

export interface GoodsGroup {
  category: (typeof ITEM_CATEGORIES)[number];
  items: ExtraItem[];
}

/** The goods a tournament offers, one group per item category that has rows,
 *  in `ITEM_CATEGORIES` order. Rows keep the order they arrive in. */
export function groupGoods(items: ExtraItem[]): GoodsGroup[] {
  return ITEM_CATEGORIES.map((category) => ({
    category,
    items: items.filter((item) => item.category === category),
  })).filter((group) => group.items.length > 0);
}
