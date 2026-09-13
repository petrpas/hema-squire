import type { ExportBandTab, ExportTab } from "../api";

export const tabId = (tab: ExportTab) => `${tab.kind}:${tab.key}`;

/** A tab's name, as the band and the rail card heading it both state it. */
export function tabLabel(t: (key: string) => string, tab: ExportTab): string {
  if (tab.kind === "fencers") return t("export.tab.fencers");
  if (tab.kind === "category") return t(`export.category.${tab.key}`);
  return tab.label;
}

/** How many a tab lists, as its label states it: `24 + 3` for a discipline
 *  with a queue, `24` otherwise — an empty queue is not stated, a seated zero
 *  is. Takes no switch state: the count is of the whole tab, so two tabs stay
 *  comparable at a glance whatever each is filtered to. */
export function tabCount(tab: Pick<ExportBandTab, "count" | "queued">): string {
  return tab.queued > 0 ? `${tab.count} + ${tab.queued}` : String(tab.count);
}
