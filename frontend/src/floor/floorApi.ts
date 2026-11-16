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

// ------------------------------------------------------------ the plan

export interface PlanChoice {
  discipline_id: number;
  k: number;
  day: string;
  sizes: number[];
}

export interface PlanActivity {
  id: string;
  discipline_id: number;
  kind: "pool" | "bout";
  ordinal: number;
  round: number;
  piste_id: number;
  day: string;
  start: string;
  end: string;
  final: boolean;
  size: number;
}

export interface PlanMetrics {
  last_end: Record<string, string>;
  exclusion_load: number;
  collisions: number;
  shortage: number;
  average_pool: number;
}

export interface Variant {
  key: string;
  choices: PlanChoice[];
  metrics: PlanMetrics;
  activities: PlanActivity[];
}

export interface Infeasible {
  reason: "structure" | "pin" | "rule" | "overrun";
  subject: string | { kind: string; target: string; day?: string; k?: number };
  minutes: number;
  detail: string;
}

export interface Variants {
  variants: Variant[];
  infeasible: Infeasible | null;
  capped: number[];
  empty: number[];
}

export interface StoredPlan {
  version: number;
  status: "working" | "published" | "history";
  created_at: string;
  choices: PlanChoice[];
  metrics: PlanMetrics;
  activities: PlanActivity[];
}

export interface Pin {
  id: number;
  kind: "day" | "k" | "place" | "sequence";
  target: string;
  value: Record<string, unknown>;
  gate: string | null;
}

export interface Change {
  activity: string;
  kind: "moved" | "added" | "removed";
  before: [number, string, string] | null;
  after: [number, string, string] | null;
}

export interface Sensitivity {
  thresholds: { discipline_id: number; below: number | null; above: number | null }[];
  days: {
    day: string;
    one_fewer: number | null;
    one_more: number | null;
    two_more: number | null;
    limit: "pistes" | "officials" | "none";
  }[];
}

export interface PlanState {
  working: StoredPlan | null;
  published: StoredPlan | null;
  history: number[];
  diff: Change[];
  pins: Pin[];
  obstacles: string[];
  sensitivity: Sensitivity | null;
  setup_missing: string[];
}

export const planApi = {
  state: (slug: string) => request<PlanState>(`${base(slug)}/plan`),
  variants: (slug: string) => request<Variants>(`${base(slug)}/plan/variants`, { method: "POST" }),
  choose: (slug: string, key: string) =>
    request<void>(`${base(slug)}/plan/choose`, { method: "POST", body: JSON.stringify({ key }) }),
  publish: (slug: string) => request<void>(`${base(slug)}/plan/publish`, { method: "POST" }),
  replan: (slug: string) => request<Variants>(`${base(slug)}/plan/replan`, { method: "POST" }),
  pin: (slug: string, pin: Omit<Pin, "id" | "gate">) =>
    request<Pin>(`${base(slug)}/plan/pins`, { method: "POST", body: JSON.stringify(pin) }),
  unpin: (slug: string, id: number) =>
    request<void>(`${base(slug)}/plan/pins/${id}`, { method: "DELETE" }),
};
