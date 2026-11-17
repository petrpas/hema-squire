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
 *  reorders one; what a setting changes is a tab's content. */
export const FLOOR_TABS = [
  "setup",
  "data",
  "plan",
  "today",
  "checkin",
  "pools",
  "bracket",
  "results",
] as const;

export type FloorTab = (typeof FLOOR_TABS)[number];

/** The narrow screen's last tab, where the schedule panel goes when it no
 *  longer fits beside the work. Never part of an address. */
export const SCHEDULE_TAB = "schedule";

export type FloorBarTab = FloorTab | typeof SCHEDULE_TAB;

/** The tabs whose change has landed. The rest say so in one line. */
export const IMPLEMENTED: ReadonlySet<FloorTab> = new Set([
  "setup",
  "data",
  "plan",
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

/** The tabs the rail offers: the eight, and on a narrow screen the schedule
 *  last, where a schedule is planned at all. */
export function barTabs(narrow: boolean, schedule = true): FloorBarTab[] {
  return narrow && schedule ? [...FLOOR_TABS, SCHEDULE_TAB] : [...FLOOR_TABS];
}

/** Each rail tab's outline icon, beside the order so the two cannot drift
 *  apart (design rework-floor-setup D1). */
export const TAB_ICONS: Record<FloorBarTab, Icon> = {
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
