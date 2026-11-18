import {
  type Icon,
  IconCalendarCog,
  IconCalendarTime,
  IconDatabase,
  IconGridDots,
  IconLayoutDashboard,
  IconSettings,
  IconTournament,
  IconTrophy,
  IconUserCheck,
} from "@tabler/icons-react";

/** The tournament-day console's tabs, in their fixed order (spec
 *  floor-console, Eight tabs in a fixed order). No setting adds, removes or
 *  reorders one, with one named exception: "Rozvrh" exists only where a
 *  schedule is planned. What a setting changes otherwise is a tab's content. */
export const FLOOR_TABS = [
  "setup",
  "data",
  "plan",
  "schedule",
  "today",
  "checkin",
  "pools",
  "bracket",
  "results",
] as const;

export type FloorTab = (typeof FLOOR_TABS)[number];

/** The tabs that work on one discipline at a time and choose it from a
 *  strip of discipline tabs, the choice kept across them (spec
 *  floor-console, Step tabs choose their discipline by tabs). */
export const STEP_TABS: ReadonlySet<FloorTab> = new Set([
  "data",
  "checkin",
  "pools",
  "bracket",
  "results",
]);

/** The tabs whose change has landed. The rest say so in one line. */
export const IMPLEMENTED: ReadonlySet<FloorTab> = new Set([
  "setup",
  "data",
  "plan",
  "schedule",
  "today",
  "checkin",
]);

export function isFloorTab(value: string | undefined): value is FloorTab {
  return value !== undefined && (FLOOR_TABS as readonly string[]).includes(value);
}

/** Where an address naming no tab, or none that exists, lands: the day's
 *  overview once a plan is published, Setup before then. */
export function defaultTab(planPublished: boolean): FloorTab {
  return planPublished ? "today" : "setup";
}

/** The tabs the rail offers: all of them where a schedule is planned, and
 *  every one but "Rozvrh" where none is. The same on every width. */
export function barTabs(schedule: boolean): FloorTab[] {
  return schedule ? [...FLOOR_TABS] : FLOOR_TABS.filter((tab) => tab !== "schedule");
}

/** Each rail tab's outline icon, beside the order so the two cannot drift
 *  apart (design rework-floor-setup D1). */
export const TAB_ICONS: Record<FloorTab, Icon> = {
  setup: IconSettings,
  data: IconDatabase,
  plan: IconCalendarCog,
  today: IconLayoutDashboard,
  checkin: IconUserCheck,
  pools: IconGridDots,
  bracket: IconTournament,
  results: IconTrophy,
  schedule: IconCalendarTime,
};
