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
  /** the disciplines held that day; each belongs to exactly one day */
  discipline_ids: number[];
}

/** What the floor plans (spec floor-setup, Scope decides what is planned). */
export interface FloorScope {
  plan_schedule: boolean;
  multi_day: boolean;
  plan_officials: boolean;
}

/** A piste or an official serves a discipline, as regular or as reserve. */
export interface Serves {
  discipline_id: number;
  reserve: boolean;
}

export interface FloorPiste {
  id: number | null;
  name: string;
  serves: Serves[];
}

export interface FloorFormat {
  discipline_id: number;
  pool_min: number;
  pool_max: number;
  /** null is "all" */
  advance: number | null;
  third_place: boolean;
  referees_pool: number;
  referees_elim: number;
  slot_pool_bout: number;
  slot_elim_bout: number;
  pause_between_pools: number;
  slot_team_match: number | null;
  points_pool: number | null;
  points_elim: number | null;
  points_team_bout: number | null;
  /** the discipline whose pool results this one takes over */
  takes_pools_from: number | null;
}

export type FloorFormatOut = FloorFormat & { stored: boolean; missing: string[] };

export interface FloorOfficial {
  id: number | null;
  name: string;
  /** "Šermuje jako": with a link, the person's name is the official's */
  person_key: string | null;
  main: boolean;
  serves: Serves[];
  days: string[];
}

export type FloorOfficialOut = FloorOfficial & { link_lost: boolean };

export type Finals = "elimination" | "day" | "tournament";

export interface FloorParams {
  finals: Finals;
  min_rest_minutes: number;
}

/** The plan's preferences, edited on the `plan` tab (spec floor-plan). */
export interface FloorPreferences {
  pool_size: "larger" | "smaller";
  club_weight: number;
  nationality_weight: number;
}

export interface FloorDiscipline {
  id: number;
  slug: string;
  name: string;
  kind: "individual" | "team";
  weapon?: string;
  team_min?: number | null;
}

export interface FloorSetup {
  disciplines: FloorDiscipline[];
  persons: { key: string; name: string }[];
  scope: FloorScope;
  days: { stored: boolean; days: FloorDay[] };
  pistes: FloorPiste[];
  formats: FloorFormatOut[];
  officials: FloorOfficialOut[];
  params: FloorParams;
  preferences: FloorPreferences;
}

export interface FloorSummary {
  plan_published: boolean;
  badges: Record<string, boolean>;
  setup_missing: string[];
  /** false where floor Setup plans no schedule: no schedule panel then */
  plan_schedule?: boolean;
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

export type SetupSection =
  | "scope"
  | "days"
  | "pistes"
  | "formats"
  | "officials"
  | "params"
  | "preferences";

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
  /** 0 for a discipline that takes over: it has no pools */
  k: number;
  /** null in a plan made without a schedule */
  day: string | null;
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
  reserve_used?: number[];
  /** moments where more pistes run than the day has main referees: a warning */
  main_warnings?: { day: string; at: string; short: number }[];
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
  kind: "k" | "place" | "sequence" | "n";
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
  pin: (slug: string, pin: Omit<Pin, "id" | "gate" | "kind"> & { kind: "k" }) =>
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
    /** the discipline whose pools this one takes over */
    takes_pools_from?: number | null;
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
  /** where no pool runs: the piste's next elimination bout */
  bout?: {
    id: number;
    round: number;
    a: string;
    b: string;
    score_a: number | null;
    score_b: number | null;
    version: number;
  } | null;
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

// ------------------------------------------------------------ the bracket

export interface BracketBout {
  id: number;
  round: number;
  position: number;
  a: string;
  b: string;
  score_a: number | null;
  score_b: number | null;
  outcome_a: Outcome | null;
  outcome_b: Outcome | null;
  note: string | null;
  piste_id: number | null;
  version: number;
}

export interface BracketView {
  state: "waiting" | "seeded" | "running" | "closed";
  pools_closed: boolean;
  /** the discipline whose pools this one takes over: it waits on them */
  source?: number | null;
  names: Record<string, string>;
  proposal: {
    size: number;
    advancing: number;
    /** entrants the source's ranking does not place, seeded below the rest */
    unplaced?: string[];
    slots: { position: number; seed: number | null; key: string | null }[];
  } | null;
  bracket: {
    size: number;
    advancing: number;
    third_place: boolean;
    closed_at: string | null;
    slots: {
      round: number;
      position: number;
      key: string | null;
      seed: number | null;
      bye: boolean;
    }[];
    bouts: BracketBout[];
  } | null;
}

const brackets = (slug: string, discipline: number) => `${base(slug)}/bracket/${discipline}`;

export const bracketApi = {
  view: (slug: string, discipline: number) => request<BracketView>(brackets(slug, discipline)),
  confirm: (slug: string, discipline: number) =>
    request<void>(`${brackets(slug, discipline)}/confirm`, { method: "POST" }),
  reopen: (slug: string, discipline: number) =>
    request<void>(`${brackets(slug, discipline)}/reopen`, { method: "POST" }),
  record: (slug: string, discipline: number, bout: number, result: ResultIn) =>
    request<void>(`${brackets(slug, discipline)}/bouts/${bout}`, {
      method: "PUT",
      body: JSON.stringify(result),
    }),
  sheetUrl: (slug: string, discipline: number) => `${brackets(slug, discipline)}/sheet`,
};

// ------------------------------------------------------------ officials on blocks

export interface Seat {
  id: number;
  role: string;
  /** slot 0 is the block's main place */
  slot: number;
  official_id: number | null;
  name: string | null;
  pinned: boolean;
  main_place?: boolean;
  /** the official serves the block's discipline as reserve */
  reserve?: boolean;
  /** the official is a main referee */
  main?: boolean;
}

export interface AssignmentBlock {
  key: string;
  discipline_id: number;
  piste_id: number;
  day: string;
  start: string;
  end: string;
  activities: string[];
  stage?: "pool" | "elim";
  /** staffed with no main referee among them: tolerated, stated */
  without_main?: boolean;
  seats: Seat[];
}

export interface Assignments {
  published: boolean;
  blocks: AssignmentBlock[];
  unmatched: { id: number; block: string; role: string; name: string | null }[];
  conflicts: { block: string; official_id: number; club: string }[];
}

export const officialsApi = {
  view: (slug: string) => request<Assignments>(`${base(slug)}/officials`),
  run: (slug: string) => request<void>(`${base(slug)}/officials/run`, { method: "POST" }),
  seat: (slug: string, seat: number, official: number | null, pinned: boolean) =>
    request<void>(`${base(slug)}/officials/seats/${seat}`, {
      method: "PUT",
      body: JSON.stringify({ official_id: official, pinned }),
    }),
  printUrl: (slug: string, kind: "official" | "piste", id: number) =>
    `${base(slug)}/officials/print/${kind}/${id}`,
};

// ------------------------------------------------------------ results and the public floor

export interface StandingRow {
  place: number;
  key?: string;
  name: string;
  club: string | null;
  nationality: string | null;
}

export interface DisciplineResults {
  discipline_id: number;
  slug: string;
  name: string;
  standing: StandingRow[] | null;
  published_at: string | null;
}

export const resultsApi = {
  list: (slug: string) => request<DisciplineResults[]>(`${base(slug)}/results`),
  publish: (slug: string, discipline: number) =>
    request<void>(`${base(slug)}/results/${discipline}/publish`, { method: "POST" }),
  withdraw: (slug: string, discipline: number) =>
    request<void>(`${base(slug)}/results/${discipline}/publish`, { method: "DELETE" }),
  exportUrl: (slug: string, discipline: number, fmt: "csv" | "pdf") =>
    `${base(slug)}/results/${discipline}/${fmt}`,
};

export interface ProgramItem {
  kind: "pool" | "bout";
  round: number;
  ordinal: number;
  final: boolean;
  day: string;
  start: string;
  end: string;
  piste: string;
}

export const publicFloorApi = {
  summary: (slug: string) =>
    request<{ program: boolean; results: boolean }>(`${base(slug)}/public`),
  program: (slug: string) =>
    request<{ discipline: string; slug: string; slip: number | null; items: ProgramItem[] }[]>(
      `${base(slug)}/public/program`,
    ),
  results: (slug: string) =>
    request<{ discipline: string; slug: string; standing: StandingRow[] }[]>(
      `${base(slug)}/public/results`,
    ),
  itinerary: (slug: string) =>
    request<
      {
        discipline: string;
        kind: "pool" | "bout";
        number: number;
        piste: string;
        day: string;
        start: string;
      }[]
    >(`${base(slug)}/public/itinerary`),
};
