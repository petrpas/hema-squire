import { request } from "../api";

/** The floor's server answers (backend `app/floor/schemas.py`). Kept beside
 *  the floor rather than in `api.ts`, so the tournament-day console is one
 *  directory. */

export interface FloorBreak {
  start: string;
  end: string;
}

export interface FloorDay {
  date: string;
  start: string;
  end: string;
  breaks: FloorBreak[];
}

export interface FloorPiste {
  id: number | null;
  name: string;
  reserve: boolean;
  tag: string | null;
  days: string[];
}

export interface Staffing {
  referee: number;
  judge: number;
  table: number;
}

export interface FloorFormat {
  discipline_id: number;
  pool_min: number;
  pool_max: number;
  /** null is "all" */
  advance: number | null;
  third_place: boolean;
  /** null until the organizer states it */
  staffing: Staffing | null;
  slot_pool_bout: number;
  slot_elim_bout: number;
  slot_pool_overhead: number;
  slot_team_match: number | null;
}

export type FloorFormatOut = FloorFormat & { stored: boolean; missing: string[] };

export type Role = "referee" | "judge" | "table";

export interface FloorOfficial {
  id: number | null;
  name: string;
  person_key: string | null;
  roles: Role[];
  discipline_ids: number[];
  days: string[];
}

export type FloorOfficialOut = FloorOfficial & { link_lost: boolean };

export interface FloorParams {
  finals_last: boolean;
  prefer_larger_pools: boolean;
  club_weight: number;
  nationality_weight: number;
  min_rest_minutes: number;
}

export interface FloorDiscipline {
  id: number;
  slug: string;
  name: string;
  kind: "individual" | "team";
}

export interface FloorSetup {
  disciplines: FloorDiscipline[];
  persons: { key: string; name: string }[];
  days: { stored: boolean; days: FloorDay[] };
  pistes: FloorPiste[];
  formats: FloorFormatOut[];
  officials: FloorOfficialOut[];
  params: FloorParams;
}

export interface FloorSummary {
  plan_published: boolean;
  badges: Record<string, boolean>;
  setup_missing: string[];
}

export interface FloorPerson {
  key: string;
  name: string;
  club: string | null;
  nationality: string | null;
  hr_id: number | null;
}

export interface FloorRoster {
  date: string;
  timezone: string;
  disciplines: (FloorDiscipline & { id: number })[];
  persons: FloorPerson[];
  individuals: {
    person: string;
    discipline: string;
    rating: number | null;
    rank: number | null;
    paid: boolean;
  }[];
  teams: { key: string; discipline: string; name: string; members: string[]; paid: boolean }[];
}

export type SetupSection = "days" | "pistes" | "formats" | "officials" | "params";

function base(slug: string): string {
  return `/api/tournaments/${slug}/floor`;
}

export const floorApi = {
  summary: (slug: string) => request<FloorSummary>(`${base(slug)}/summary`),
  setup: (slug: string) => request<FloorSetup>(`${base(slug)}/setup`),
  roster: (slug: string) => request<FloorRoster>(`${base(slug)}/roster`),
  save: (slug: string, section: SetupSection, body: unknown) =>
    request<void>(`${base(slug)}/setup/${section}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
};
