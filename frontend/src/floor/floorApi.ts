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
  /** "n" is check-in's own: a closed discipline's N, added by its gate */
  kind: "day" | "k" | "place" | "sequence" | "n";
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
  pin: (slug: string, pin: Omit<Pin, "id" | "gate" | "kind"> & { kind: "day" | "k" }) =>
    request<Pin>(`${base(slug)}/plan/pins`, { method: "POST", body: JSON.stringify(pin) }),
  unpin: (slug: string, id: number) =>
    request<void>(`${base(slug)}/plan/pins/${id}`, { method: "DELETE" }),
};

// ------------------------------------------------------------ check-in and today

export interface DeskEntry {
  entry_key: string;
  discipline_id: number;
  team: string | null;
  paid: boolean;
  withdrawn: boolean;
}

export interface DeskPerson {
  key: string;
  name: string;
  club: string | null;
  nationality: string | null;
  local: boolean;
  arrived: boolean;
  entries: DeskEntry[];
}

export interface DeskDiscipline {
  id: number;
  slug: string;
  name: string;
  kind: "individual" | "team";
  team_min: number | null;
  team_max: number | null;
  closed: boolean;
  closed_at: string | null;
  entered: number;
  present: number;
  n: number | null;
}

export interface DeskTeam {
  key: string;
  discipline_id: number;
  name: string;
  members: string[];
  lineup: string[];
  present: boolean;
  short_by: number;
  withdrawn: boolean;
}

export interface Desk {
  persons: DeskPerson[];
  disciplines: DeskDiscipline[];
  teams: DeskTeam[];
}

export interface CloseImpact {
  n: number;
  n_pool: number;
  feasible: boolean;
  k: number | null;
  sizes: number[];
  published_k: number | null;
  range: number[] | null;
  day: string | null;
  end_change: number | null;
}

export interface Today {
  rows: {
    discipline_id: number;
    slug: string;
    name: string;
    steps: Record<string, string>;
    slip: number | null;
  }[];
  waiting: { tab: string; discipline: string | null; code: string }[];
}

const enc = encodeURIComponent;

export const checkinApi = {
  desk: (slug: string) => request<Desk>(`${base(slug)}/checkin`),
  arrive: (slug: string, key: string) =>
    request<void>(`${base(slug)}/checkin/arrivals`, {
      method: "POST",
      body: JSON.stringify({ person_key: key }),
    }),
  leave: (slug: string, key: string) =>
    request<void>(`${base(slug)}/checkin/arrivals/${enc(key)}`, { method: "DELETE" }),
  withdraw: (slug: string, entry: string) =>
    request<void>(`${base(slug)}/checkin/withdrawals`, {
      method: "POST",
      body: JSON.stringify({ entry_key: entry }),
    }),
  undoWithdrawal: (slug: string, entry: string) =>
    request<void>(`${base(slug)}/checkin/withdrawals/${enc(entry)}`, { method: "DELETE" }),
  lineup: (slug: string, team: string, keys: string[]) =>
    request<void>(`${base(slug)}/checkin/lineups/${enc(team)}`, {
      method: "PUT",
      body: JSON.stringify({ person_keys: keys }),
    }),
  local: (slug: string, name: string) =>
    request<{ key: string }>(`${base(slug)}/checkin/locals`, {
      method: "POST",
      body: JSON.stringify({ name }),
    }),
  impact: (slug: string, discipline: number) =>
    request<CloseImpact>(`${base(slug)}/checkin/${discipline}/close`),
  close: (slug: string, discipline: number) =>
    request<void>(`${base(slug)}/checkin/${discipline}/close`, { method: "POST" }),
  reopenPreview: (slug: string, discipline: number) =>
    request<{ invalidated: string[]; refusals: string[] }>(
      `${base(slug)}/checkin/${discipline}/reopen`,
    ),
  reopen: (slug: string, discipline: number) =>
    request<void>(`${base(slug)}/checkin/${discipline}/reopen`, { method: "POST" }),
  today: (slug: string) => request<Today>(`${base(slug)}/today`),
};

// ------------------------------------------------------------ pools and pistes

export type Outcome = "win" | "loss" | "draw" | "no";

export interface PoolBout {
  id: number;
  ordinal: number;
  a: string;
  b: string;
  score_a: number | null;
  score_b: number | null;
  outcome_a: Outcome | null;
  outcome_b: Outcome | null;
  note: string | null;
  recorded_by: string | null;
  version: number;
}

export interface DrawPool {
  number: number;
  wave: number;
  piste_id: number | null;
  planned_start: string | null;
  members: { key: string; seed: number }[];
  bouts: PoolBout[];
}

export interface DrawScore {
  snake: number;
  club: number;
  nationality: number;
  wave: number;
  total: number;
}

export interface StatsRow {
  key: string;
  v: number;
  m: number;
  vm: number;
  ts: number;
  tr: number;
  ind: number;
}

export interface PoolsView {
  state: "waiting" | "running" | "complete" | "closed";
  checkin_closed: boolean;
  names: Record<string, string>;
  draw: {
    score: DrawScore;
    previous_score: DrawScore | null;
    announced_at: string | null;
    closed_at: string | null;
    pools: DrawPool[];
  } | null;
  standings?: {
    pools: { number: number; stats: StatsRow[] }[];
    ranking: StatsRow[];
    warnings: {
      pool: number | null;
      code: string;
      subject: string;
      expected: number;
      found: number;
    }[];
  };
  call_list?: {
    pool: number;
    wave: number;
    piste_id: number | null;
    planned_start: string | null;
    members: string[];
  }[];
}

export interface ResultIn {
  score_a: number;
  score_b: number;
  outcome_a: Outcome;
  outcome_b: Outcome;
  note?: string | null;
  version: number;
}

const pools = (slug: string, discipline: number) => `${base(slug)}/pools/${discipline}`;

export const poolsApi = {
  view: (slug: string, discipline: number) => request<PoolsView>(pools(slug, discipline)),
  draw: (slug: string, discipline: number) =>
    request<void>(`${pools(slug, discipline)}/draw`, { method: "POST" }),
  swap: (slug: string, discipline: number, a: string, b: string) =>
    request<void>(`${pools(slug, discipline)}/swap`, {
      method: "POST",
      body: JSON.stringify({ a, b }),
    }),
  announce: (slug: string, discipline: number) =>
    request<void>(`${pools(slug, discipline)}/announce`, { method: "POST" }),
  reopenPreview: (slug: string, discipline: number) =>
    request<{ invalidated: string[]; refusals: string[] }>(`${pools(slug, discipline)}/reopen`),
  reopen: (slug: string, discipline: number) =>
    request<void>(`${pools(slug, discipline)}/reopen`, { method: "POST" }),
  record: (slug: string, bout: number, result: ResultIn) =>
    request<void>(`${base(slug)}/pools/bouts/${bout}`, {
      method: "PUT",
      body: JSON.stringify(result),
    }),
  transcribe: (slug: string, discipline: number, bouts: (ResultIn & { id: number })[]) =>
    request<void>(`${pools(slug, discipline)}/sheet`, {
      method: "PUT",
      body: JSON.stringify({ bouts }),
    }),
  closePreview: (slug: string, discipline: number) =>
    request<{ ranking: StatsRow[]; advance: number }>(`${pools(slug, discipline)}/close`),
  close: (slug: string, discipline: number) =>
    request<void>(`${pools(slug, discipline)}/close`, { method: "POST" }),
  reopenPools: (slug: string, discipline: number) =>
    request<void>(`${pools(slug, discipline)}/reopen-pools`, { method: "POST" }),
  sheetUrl: (slug: string, discipline: number, number: number) =>
    `${pools(slug, discipline)}/sheets/${number}`,
  ringKeys: (slug: string) =>
    request<{ piste_id: number; name: string; issued_at: string | null }[]>(`${base(slug)}/ring`),
  issue: (slug: string, piste: number) =>
    request<{ key: string; qr_png_base64: string }>(`${base(slug)}/ring/${piste}`, {
      method: "POST",
      body: JSON.stringify({ origin: window.location.origin }),
    }),
  revoke: (slug: string, piste: number) =>
    request<void>(`${base(slug)}/ring/${piste}`, { method: "DELETE" }),
};

export interface RingWork {
  piste: string;
  pool: {
    discipline_id: number | null;
    number: number;
    members: { key: string; name: string }[];
    bouts: {
      id: number;
      ordinal: number;
      a: string;
      b: string;
      score_a: number | null;
      score_b: number | null;
      outcome_a: Outcome | null;
      outcome_b: Outcome | null;
      version: number;
    }[];
  } | null;
}

export const ringApi = {
  current: (key: string) =>
    request<RingWork>("/api/floor/ring/current", { headers: { "X-Floor-Ring-Key": key } }),
  record: (key: string, bout: number, result: ResultIn) =>
    request<void>(`/api/floor/ring/bouts/${bout}`, {
      method: "PUT",
      body: JSON.stringify(result),
      headers: { "X-Floor-Ring-Key": key },
    }),
};
