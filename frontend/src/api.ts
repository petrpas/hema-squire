const TOKEN_KEY = "hema_squire_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token === null) localStorage.removeItem(TOKEN_KEY);
  else localStorage.setItem(TOKEN_KEY, token);
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: unknown,
  ) {
    super(`API ${status}`);
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (!response.ok) {
    let detail: unknown = null;
    try {
      detail = (await response.json()).detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

/** The four features that make up a tournament's mode. Easy mode is the
 *  absence of all four, advanced mode at least one — there is no separately
 *  stored mode value, so the name a tournament is given and the sections its
 *  console offers can never disagree (design tournament-modes D2). */
export interface TournamentMode {
  /** Disciplines specify where and when they occur. */
  feature_schedule: boolean;
  /** Squire handles payment processing: the only feature that changes what
   *  the system does rather than which controls Setup offers (D5). */
  feature_payments: boolean;
  feature_teams: boolean;
  feature_extras: boolean;
}

export const MODE_FEATURES = [
  "feature_schedule",
  "feature_payments",
  "feature_teams",
  "feature_extras",
] as const satisfies readonly (keyof TournamentMode)[];

export const EASY_MODE: TournamentMode = {
  feature_schedule: false,
  feature_payments: false,
  feature_teams: false,
  feature_extras: false,
};

export function isEasyMode(mode: TournamentMode): boolean {
  return !MODE_FEATURES.some((feature) => mode[feature]);
}

export interface Tournament extends TournamentMode {
  slug: string;
  display_name: string;
  subtitle: string | null;
  has_logo: boolean;
  date: string;
  language: string;
  owner_id: number | null;
  cancelled_at: string | null;
  /** Null means draft: invisible to fencers, closed to registration. Set
   *  once, for good, by the publish action — never cleared. */
  published_at: string | null;
}

/** Public URL of a tournament logo (unauthenticated, so it works in <img>). */
export function logoUrl(slug: string): string {
  return `/api/tournaments/${slug}/logo`;
}

/** A tournament's local currency; amounts are whole units of it. */
export type Currency = "CZK" | "EUR";

/** The three currency modes a tournament can be in (design Decision 2). */
export type CurrencyMode = "local" | "local_eur" | "eur";

export type Role = "fencer" | "organizer" | "admin";

export interface Account {
  id: number;
  email: string;
  display_name: string;
  hr_id: number | null;
  nationality: string | null;
  club: string | null;
  language: string;
  role: Role;
  is_deployment_owner: boolean;
}

export type PleaState = "pending" | "granted" | "denied" | "cancelled" | null;

export interface Plea {
  state: PleaState;
  message: string | null;
  created_at: string | null;
  decided_at: string | null;
}

export interface TeamMember {
  fencer_id: number;
  email: string;
  display_name: string;
}

export interface AdminAccount {
  id: number;
  email: string;
  display_name: string;
  role: Role;
  hr_id: number | null;
  is_deployment_owner: boolean;
  has_pending_plea: boolean;
  hr_shared: boolean;
}

export interface PleaQueueItem {
  id: number;
  fencer_id: number;
  email: string;
  display_name: string;
  message: string | null;
  created_at: string;
}

/** Individual is the default and behaves exactly as before team disciplines
 *  existed; for a team discipline, capacity counts teams and fee is per team
 *  (design team-disciplines D2). */
export type DisciplineKind = "individual" | "team";

/** Gender stays a closed set: Open, Women, Men (design discipline-identity D4). */
export type DisciplineGender = "" | "W" | "M";
/** Material stays a closed set: Steel, Plastic (design discipline-identity D4). */
export type DisciplineMaterial = "" | "Plastic";

export interface Discipline {
  /** Identity: unique within the tournament, generated or overridden, frozen
   *  once referenced (design discipline-identity). Never shown to fencers. */
  slug: string;
  name: string;
  /** Display order among the tournament's disciplines; organizer-set via the
   *  Setup table's up arrow. */
  ordinal: number;
  /** The five taxonomy weapons are offered as suggestions; any weapon is
   *  accepted (design discipline-identity D4). */
  weapon: string;
  gender: DisciplineGender;
  material: DisciplineMaterial;
  kind: DisciplineKind;
  /** Roster bounds; present only when kind is "team". */
  team_min: number | null;
  team_max: number | null;
  capacity: number;
  fee: number | null;
  fee_early: number | null;
  /** EUR prices, authoritative and independent of fee/fee_early — filled
   *  only in local + EUR mode, never computed from the local price. */
  fee_eur: number | null;
  fee_early_eur: number | null;
  schedule_when: string | null;
  schedule_where: string | null;
  ruleset: string | null;
  /** Whether slug, classification, and kind are frozen — derived from
   *  whether any entry or team references the discipline, not from occupied
   *  seats (design discipline-identity-modal D6). The name is never covered. */
  identity_frozen: boolean;
}

/** Editable discipline payload (Setup add/patch). */
export interface DisciplineInput {
  /** Omitted on creation to let the server generate one from the
   *  classification (design discipline-identity D3). */
  slug?: string | null;
  name?: string | null;
  ordinal?: number | null;
  weapon: string;
  gender: DisciplineGender;
  material: DisciplineMaterial;
  kind: DisciplineKind;
  team_min?: number | null;
  team_max?: number | null;
  capacity: number;
  fee: number | null;
  fee_eur?: number | null;
  schedule_when?: string | null;
  schedule_where?: string | null;
  ruleset?: string | null;
}

export type ExtraCategory =
  | "seminar"
  | "rental"
  | "afterparty"
  | "merch"
  | "other_action"
  | "other_item";

/** Editable extra-item payload (Setup add/patch). */
export interface ExtraItemInput {
  name: string;
  category: ExtraCategory;
  price: number;
  /** EUR price, authoritative and independent of `price` — filled only in
   *  local + EUR mode. */
  price_eur?: number | null;
  max_qty: number;
  schedule_when?: string | null;
  schedule_where?: string | null;
  remark?: string | null;
  /** Label of the single option the fencer answers on selection ("size"). */
  option_label?: string | null;
  /** Allowed answers; empty means the option is free text. */
  option_choices?: string[];
}

export interface ExtraItem {
  id: number;
  name: string;
  category: ExtraCategory;
  price: number;
  price_eur: number | null;
  max_qty: number;
  schedule_when: string | null;
  schedule_where: string | null;
  remark: string | null;
  option_label: string | null;
  option_choices: string[];
}

export type DiscountCategory = "discipline" | ExtraCategory;

export interface DiscountCondition {
  kind: "discipline_count" | "early";
  count?: number | null;
  until?: string | null;
}

export interface DiscountEffect {
  kind: "fixed" | "percent";
  value: number;
  /** The EUR amount of a fixed discount — a price decision like any other,
   *  filled only in local + EUR mode. Percent effects carry no second value. */
  value_eur?: number | null;
}

export interface Discount {
  name: string;
  condition: DiscountCondition;
  effect: DiscountEffect;
  scope: DiscountCategory[];
}

export interface Organizer {
  name: string;
  link: string | null;
}

/** Values the signed-in account has used on its own earlier tournaments, offered
 *  back on the three Setup fields that recall them. Derived per request from
 *  those tournaments — nothing is stored, so a value corrected at its source
 *  stops being offered. Empty lists mean an organizer with no history yet, which
 *  renders no affordance at all. */
export interface SetupSuggestions {
  locations: string[];
  bank_accounts: string[];
  // name and link travel together: choosing a remembered club fills both
  organizers: Organizer[];
}

/** How a seat is held until the seating deadline. `immediate` is what every
 *  tournament created before the mode existed does. */
export type PaymentMode = "immediate" | "deposit" | "reservation";

export interface TournamentDetail extends Tournament {
  payment_mode: PaymentMode;
  /** The date seating settles — a soft boundary inside registration_closes,
   *  not the hard close. Unset it resolves to the registration close, which
   *  itself resolves to the tournament date. */
  seating_deadline: string | null;
  /** Set once seating has settled, by the deadline or by the organizer;
   *  settlement never runs twice. */
  seating_settled_at: string | null;
  /** Flat deposit owed at registration in deposit mode, with its independent
   *  EUR counterpart — never derived from it (design D4). */
  deposit_amount: number | null;
  deposit_amount_eur: number | null;
  reservation_validity_days: number;
  reminder_day: number;
  amount_tolerance_percent: number;
  refundable_until: string | null;
  bank_account: string | null;
  expiry_grace_hours: number;
  unpaid_list_treatment: string;
  output_sheet_url: string | null;
  early_bird_until: string | null;
  weapon_rental_fee: number;
  weapon_rental_fee_early: number | null;
  afterparty_fee: number;
  afterparty_fee_early: number | null;
  location: string | null;
  description: string | null;
  qualification_open: boolean;
  qualification_criteria: string | null;
  registration_instructions: string | null;
  local_currency: Currency;
  eur_payments_enabled: boolean;
  /** Local-currency units per 1 EUR; a Setup convenience for recalculate-
   *  missing only, never required and never read outside Setup. */
  eur_rate: string | null;
  organizers: Organizer[];
  registration_opens: string | null;
  /** The wall clock registration opens on `registration_opens`, read in
   *  `timezone`. Null means the start of that local day. */
  registration_opens_time: string | null;
  /** The tournament's own zone as an IANA identifier; every date and time on
   *  its timeline is read in it. */
  timezone: string;
  /** The opening moment resolved to an absolute instant — null when no
   *  opening date is set. Derived by the server so no client resolves this
   *  tournament's daylight-saving rules itself (design D6). */
  registration_opens_at: string | null;
  /** This response's own instant, for measuring the device clock against the
   *  server's rather than counting down on a clock that may be wrong. */
  server_time: string;
  registration_closes: string | null;
  /** Unset means "same window as registration" (Decision 4). */
  amendments_close: string | null;
  /** Checks, never enforces; meaningful only with a team discipline (design
   *  team-disciplines D7). Independent of registration/amendment windows. */
  team_composition_deadline: string | null;
  discounts: Discount[];
  extra_items: ExtraItem[];
  setup_missing: string[] | null;
  /** Derived from local_currency + eur_payments_enabled (design Decision 2). */
  currency_mode: CurrencyMode;
  disciplines: Discipline[];
  vs_year: number;
  vs_series: number;
  /** YYNN every variable symbol this tournament issues starts with. */
  vs_prefix: number;
  /** False once the tournament has a first registration (design Decision 2). */
  vs_series_editable: boolean;
}

export interface SheetRow {
  id: string;
  /** The fixed number this row carries in the tournament, allocated once and
   *  never reissued; null where none has been (spec `etl-console`, Fixed
   *  fencer number). Never derived from the row's position in the list. */
  number: number | null;
  name: string;
  nationality: string | null;
  club: string | null;
  hr_id: number | null;
  disciplines: string[];
  substitute_for: string[];
  state: string;
  vs: number | null;
  paid: boolean;
  registered_at: string | null;
  total_amount: number | null;
  problems: string | null;
  match_verdict?: "confirmed" | "found" | "proposed" | "none_found" | "unknown";
  /** The evidence register: what HEMA Ratings holds for this row's hr_id.
   *  Empty where there is no id, or the fighters index does not know it — an
   *  absence is stated, not omitted (spec `etl-console`, The ledger idiom). */
  hr_name: string | null;
  hr_nationality: string | null;
  hr_club: string | null;
  merge_note?: string | null;
  _merged_into?: string;
  /** True once a deletion or a merge has taken the row out of the table. */
  _deleted?: boolean;
  /** The phase whose rule removed the row, absent while no rule has. Derived
   *  on every replay and stored nowhere, so it is never a column of the row
   *  (spec `edit-rules`, A removed row states where it was removed). */
  _removed_in?: string;
  /** Provenance of an imported row: the file it came from and its line there. */
  _source?: { file: string; row: number };
  expires_at: string | null;
  paid_at: string | null;
  weapon_rentals: string[];
  afterparty: boolean;
  aftersparring: boolean;
  notes: string | null;
  [key: string]: unknown;
}

/** One entry of the manual-edits log: a cell's difference from the source
 *  data, carrying every rule behind it so it can be undone whole. */
export interface NetChange {
  phase: string;
  target: string;
  field: string;
  before: unknown;
  after: unknown;
  rule_ids: number[];
  actor: string;
  at: string;
}

export interface Sheet {
  rows: SheetRow[];
  edits: NetChange[];
}

export type RegistrationStatus = "open" | "opens_on" | "closed";
export type MyRegistrationState = "none" | "reserved" | "paid" | "substitute" | "cancelled";

export interface OpenDiscipline {
  /** Not rendered to fencers (design discipline-identity D6); carried only
   *  as a stable list key. */
  slug: string;
  name: string;
  fee: number | null;
  fee_eur: number | null;
  taken: number;
  capacity: number;
  queue_length: number;
}

export interface OpenTournament {
  slug: string;
  display_name: string;
  subtitle: string | null;
  has_logo: boolean;
  date: string;
  location: string | null;
  description: string | null;
  qualification_open: boolean;
  qualification_criteria: string | null;
  local_currency: Currency;
  organizers: Organizer[];
  registration_status: RegistrationStatus;
  /** The opening *day*, as it always was. */
  registration_opens_on: string | null;
  /** The opening *moment*: absolute and offset-bearing, set only while the
   *  status is `opens_on` (design D6). */
  registration_opens_at: string | null;
  /** The zone the opening hour is stated in. */
  timezone: string;
  /** This response's own instant (see TournamentDetail.server_time). */
  server_time: string;
  disciplines: OpenDiscipline[];
  my_registration_state: MyRegistrationState;
  /** The caller's other bond: owner or console team member. Independent of
   *  my_registration_state — an entry may carry both. */
  organized: boolean;
}

export interface Availability {
  slug: string;
  kind: DisciplineKind;
  capacity: number;
  taken: number;
  free: number;
  queue_length: number;
  /** Roster bounds; present only when kind is "team". */
  team_min: number | null;
  team_max: number | null;
}

export type RegistrationRowState = "reserved" | "paid" | "expired" | "cancelled";
export type RefundState = "not_applicable" | "pending" | "refunded";

export interface RegistrationEntry {
  slug: string;
  is_substitute: boolean;
  queue_position: number | null;
}

export interface RegistrationExtraSelection {
  extra_item_id: number;
  name: string;
  category: ExtraCategory;
  qty: number;
  option_label: string | null;
  option_value: string | null;
}

export interface RosterMember {
  name: string;
  hr_id: number | null;
  club: string | null;
  nationality: string | null;
}

export interface TeamEntry {
  id: number;
  slug: string;
  name: string;
  waitlisted: boolean;
  /** Per-team fee, in each configured currency — never multiplied by roster
   *  size (design team-disciplines D2). */
  fee: number;
  fee_eur: number | null;
  team_min: number;
  team_max: number;
  members: RosterMember[];
  /** The entering fencer's own name/HR binding, suggested as the first
   *  member while the roster is still empty; never persisted as a role. */
  prefill: RosterMember | null;
}

export interface RegistrationDetail {
  state: RegistrationRowState;
  vs: number;
  total_amount: number;
  /** total_amount less what has been credited so far; a decimal string. */
  outstanding_amount: string;
  /** The stored EUR pair, absent (not derived) when the tournament does not
   *  price in EUR. */
  total_eur: number | null;
  outstanding_eur_amount: string | null;
  expires_at: string | null;
  registered_at: string;
  paid_at: string | null;
  weapon_rentals: string[];
  afterparty: boolean;
  aftersparring: boolean;
  accommodation: string | null;
  notes: string | null;
  refundable: boolean | null;
  refund_state: RefundState;
  extras: RegistrationExtraSelection[];
  entries: RegistrationEntry[];
  teams: TeamEntry[];
}

export interface ExtraSelectionPayload {
  extra_item_id: number;
  qty: number;
  option_value?: string | null;
}

export interface TeamEntryPayload {
  /** Matching an existing team's id keeps its roster on amendment; omitted
   *  (or non-matching) starts the team with an empty roster. */
  id?: number | null;
  slug: string;
  name: string;
}

export interface RegisterPayload {
  disciplines: string[];
  weapon_rentals?: string[];
  afterparty?: boolean;
  aftersparring?: boolean;
  accommodation?: string | null;
  notes?: string | null;
  extras?: ExtraSelectionPayload[];
  teams?: TeamEntryPayload[];
}

export interface PricePreviewPayload {
  disciplines: string[];
  weapon_rentals?: string[];
  afterparty?: boolean;
  extras?: ExtraSelectionPayload[];
  teams?: { slug: string }[];
}

export interface RosterMemberInput {
  name: string;
  hr_id?: number | null;
  club?: string | null;
  nationality?: string | null;
}

export interface ConsoleTeam {
  id: number;
  name: string;
  entering_fencer: string;
  waitlisted: boolean;
  waitlist_position: number | null;
  members: RosterMember[];
  below_minimum: boolean;
}

export interface ConsoleTeamDiscipline {
  slug: string;
  name: string;
  team_min: number;
  team_max: number;
  teams: ConsoleTeam[];
}

/** One fencer's placement in one individual discipline, above or below the
 *  line, as the organizer's queue view presents it. */
export interface QueueEntry {
  registration_id: number;
  fencer: string;
  club: string | null;
  vs: number | null;
  registered_at: string;
  /** Place in the queue by registration time; null when seated. */
  queue_position: number | null;
}

export interface QueueDiscipline {
  slug: string;
  name: string;
  capacity: number;
  taken: number;
  free: number;
  seated: QueueEntry[];
  queued: QueueEntry[];
}

export interface Queue {
  /** The resolved deadline, never the raw column. */
  seating_deadline: string;
  seating_settled_at: string | null;
  /** How many registrations settling now would move below the line. */
  pending_demotions: number;
  disciplines: QueueDiscipline[];
}

export interface DiscountBreakdown {
  name: string;
  effect: DiscountEffect;
  applied: boolean;
  /** What the discount deducted, read from the same computation as the
   *  total beside it — per currency for a fixed effect, local-only (design
   *  Decision 3) for a currency-neutral percentage effect; both null when
   *  the discount did not apply. */
  deducted: number | null;
  deducted_eur: number | null;
}

export interface PricePreview {
  total: number;
  currency: Currency;
  /** The stored EUR total, independently summed; null unless the tournament
   *  takes EUR alongside its local currency. */
  eur_total: number | null;
  /** One entry per discount the tournament configures, in configured order;
   *  empty for a tournament that configures none. */
  discounts: DiscountBreakdown[];
}

export type TransactionStatus = "unmatched" | "flagged" | "matched" | "resolved";

export interface Transaction {
  id: number;
  external_id: string;
  source: string;
  date: string;
  amount_cents: number;
  currency: string;
  vs: number | null;
  message: string | null;
  payer_name: string | null;
  payer_account: string | null;
  status: TransactionStatus | null;
  status_reason: string | null;
  matched_registration_id: number | null;
  /** Only meaningful for a flagged transaction: whether the reinstate action
   *  is currently offered (the backend has re-checked capacity). */
  reinstate_available: boolean;
}

export interface PaymentInstructions {
  amount: number;
  currency: Currency;
  iban: string;
  /** The domestic form for a Czech account; null for any other country. */
  account_domestic: string | null;
  vs: number;
  message: string;
  expires_at: string | null;
  spayd: string;
  qr_png_base64: string;
  /** The EUR trio is absent unless the tournament takes EUR as a second option. */
  eur_amount: number | null;
  eur_spayd: string | null;
  eur_qr_png_base64: string | null;
}

export const api = {
  login: (email: string, password: string) =>
    request<{ token: string }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  signup: (data: {
    email: string;
    password: string;
    display_name: string;
    hr_id?: number;
    language: string;
  }) =>
    request<{ token: string }>("/api/auth/signup", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  tournaments: () => request<Tournament[]>("/api/tournaments"),
  tournament: (slug: string) => request<TournamentDetail>(`/api/tournaments/${slug}`),
  createTournament: (data: { slug: string; display_name: string; date: string }) =>
    request<TournamentDetail>("/api/tournaments", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  // no slug: these belong to the account, not to the tournament being edited
  setupSuggestions: () => request<SetupSuggestions>("/api/tournaments/suggestions"),
  updateTournament: (slug: string, patch: Record<string, unknown>) =>
    request<TournamentDetail>(`/api/tournaments/${slug}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),
  getTournamentMode: (slug: string) =>
    request<TournamentMode>(`/api/tournaments/${slug}/mode`),
  // a mode is chosen as a whole, never one feature at a time, so the whole
  // set goes in one request (design tournament-modes D2)
  setTournamentMode: (slug: string, mode: TournamentMode) =>
    request<TournamentDetail>(`/api/tournaments/${slug}/mode`, {
      method: "PATCH",
      body: JSON.stringify(mode),
    }),
  taxonomy: () => request<Record<string, string>>("/api/taxonomy/disciplines"),
  addDiscipline: (slug: string, data: DisciplineInput) =>
    request<Discipline>(`/api/tournaments/${slug}/disciplines`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateDiscipline: (slug: string, disciplineSlug: string, data: DisciplineInput) =>
    request<Discipline>(`/api/tournaments/${slug}/disciplines/${disciplineSlug}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  deleteDiscipline: (slug: string, disciplineSlug: string) =>
    request<void>(`/api/tournaments/${slug}/disciplines/${disciplineSlug}`, {
      method: "DELETE",
    }),
  addExtraItem: (slug: string, data: ExtraItemInput) =>
    request<ExtraItem>(`/api/tournaments/${slug}/extra-items`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateExtraItem: (slug: string, id: number, data: ExtraItemInput) =>
    request<ExtraItem>(`/api/tournaments/${slug}/extra-items/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  deleteExtraItem: (slug: string, id: number) =>
    request<void>(`/api/tournaments/${slug}/extra-items/${id}`, { method: "DELETE" }),
  uploadLogo: async (slug: string, file: File): Promise<TournamentDetail> => {
    const body = new FormData();
    body.append("file", file);
    const token = getToken();
    const response = await fetch(logoUrl(slug), {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body,
    });
    if (!response.ok) {
      let detail: unknown = null;
      try {
        detail = (await response.json()).detail;
      } catch {
        /* non-JSON error body */
      }
      throw new ApiError(response.status, detail);
    }
    return response.json();
  },
  deleteLogo: (slug: string) =>
    request<void>(logoUrl(slug), { method: "DELETE" }),
  sheet: (slug: string) => request<Sheet>(`/api/tournaments/${slug}/sheet`),
  createRule: (
    slug: string,
    rule: { phase: string; kind: string; target: string; payload: Record<string, unknown> },
  ) =>
    request<{ id: number }>(`/api/tournaments/${slug}/rules`, {
      method: "POST",
      body: JSON.stringify(rule),
    }),
  deleteRule: (slug: string, ruleId: number) =>
    request<void>(`/api/tournaments/${slug}/rules/${ruleId}`, { method: "DELETE" }),
  hrSearch: (query: string, nationality?: string | null) =>
    request<HRProfile[]>(
      `/api/hr/search?q=${encodeURIComponent(query)}` +
        (nationality ? `&nationality=${encodeURIComponent(nationality)}` : ""),
    ),
  hrNationalities: () => request<string[]>("/api/hr/nationalities"),
  /** Records the batch and returns; the parse runs as an operation behind it,
   *  reported by `operations` (spec console-operations). A file whose rows are
   *  all already parsed starts no operation and comes back with its outcome. */
  importTable: async (slug: string, file: File): Promise<ImportStarted> => {
    const body = new FormData();
    body.append("file", file);
    const token = getToken();
    const response = await fetch(`/api/tournaments/${slug}/import`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body,
    });
    if (!response.ok) {
      let detail: unknown = null;
      try {
        detail = (await response.json()).detail;
      } catch {
        /* non-JSON error body */
      }
      throw new ApiError(response.status, detail);
    }
    return response.json();
  },
  /** Hard, total and final: everything the tournament ever imported. The
   *  console confirms before calling (spec table-import, Clearing is warned
   *  about and irreversible). */
  clearImports: (slug: string) =>
    request<ClearResult>(`/api/tournaments/${slug}/import`, { method: "DELETE" }),
  importStatus: (slug: string) =>
    request<ImportStatus>(`/api/tournaments/${slug}/import/status`),
  createManualRow: (slug: string, entry: ManualEntryIn) =>
    request<ManualRow>(`/api/tournaments/${slug}/manual-rows`, {
      method: "POST",
      body: JSON.stringify(entry),
    }),
  runMatching: (slug: string) =>
    request<OperationStarted>(`/api/tournaments/${slug}/import/match`, { method: "POST" }),
  runDedup: (slug: string) =>
    request<OperationStarted>(`/api/tournaments/${slug}/import/dedup`, { method: "POST" }),
  /** What the console polls: the tournament's running operation and the most
   *  recent concluded one of each kind (design D7). */
  operations: (slug: string) =>
    request<OperationsReport>(`/api/tournaments/${slug}/operations`),
  dedupQueue: (slug: string) =>
    request<DedupItem[]>(`/api/tournaments/${slug}/import/dedup/queue`),
  dedupDecide: (slug: string, key: string, accept: boolean) =>
    request<{ status: string }>(`/api/tournaments/${slug}/import/dedup/decide`, {
      method: "POST",
      body: JSON.stringify({ key, accept }),
    }),
  exportSheet: (slug: string) =>
    request<{ worksheets: string[]; fencers: number }>(
      `/api/tournaments/${slug}/export/sheet`,
      { method: "POST" },
    ),
  hrStatus: () => request<HRStatus>("/api/hr/status"),
  hrRefresh: () => request<{ status: string; fighters: number }>("/api/hr/refresh", {
    method: "POST",
  }),
  ratingsSnapshot: (slug: string) =>
    request<{ status: string; fencers: number; ratings: number }>(
      `/api/tournaments/${slug}/ratings/snapshot`,
      { method: "POST" },
    ),
  ratingsLatest: (slug: string) =>
    request<{ taken_at: string | null; ratings: number }>(
      `/api/tournaments/${slug}/ratings`,
    ),
  account: () => request<Account>("/api/account"),
  updateAccount: (patch: {
    email?: string;
    display_name?: string;
    club?: string;
    language?: string;
  }) =>
    request<Account>("/api/account", {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),
  bindHr: (hrId: number) =>
    request<Account>("/api/account/hr-binding", {
      method: "POST",
      body: JSON.stringify({ hr_id: hrId }),
    }),
  submitPlea: (message: string | null) =>
    request<Plea>("/api/account/plea", {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
  myPlea: () => request<Plea>("/api/account/plea"),
  cancelPlea: () => request<Plea>("/api/account/plea/cancel", { method: "POST" }),
  team: (slug: string) => request<TeamMember[]>(`/api/tournaments/${slug}/team`),
  addTeamMember: (slug: string, email: string) =>
    request<TeamMember>(`/api/tournaments/${slug}/team`, {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  removeTeamMember: (slug: string, fencerId: number) =>
    request<void>(`/api/tournaments/${slug}/team/${fencerId}`, { method: "DELETE" }),
  transferOwnership: (slug: string, email: string) =>
    request<TournamentDetail>(`/api/tournaments/${slug}/transfer-ownership`, {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  assignOwner: (slug: string, email: string) =>
    request<TournamentDetail>(`/api/tournaments/${slug}/assign-owner`, {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  cancelTournament: (slug: string) =>
    request<TournamentDetail>(`/api/tournaments/${slug}/cancel`, { method: "POST" }),
  publishTournament: (slug: string) =>
    request<TournamentDetail>(`/api/tournaments/${slug}/publish`, { method: "POST" }),
  deleteTournament: (slug: string) =>
    request<void>(`/api/tournaments/${slug}`, { method: "DELETE" }),
  adminAccounts: () => request<AdminAccount[]>("/api/admin/accounts"),
  adminSetRole: (fencerId: number, role: Role) =>
    request<AdminAccount>(`/api/admin/accounts/${fencerId}/role`, {
      method: "PATCH",
      body: JSON.stringify({ role }),
    }),
  adminHrUnbind: (fencerId: number) =>
    request<AdminAccount>(`/api/admin/accounts/${fencerId}/hr-unbind`, { method: "POST" }),
  adminPleas: () => request<PleaQueueItem[]>("/api/admin/pleas"),
  adminGrantPlea: (id: number) =>
    request<{ id: number; state: string }>(`/api/admin/pleas/${id}/grant`, { method: "POST" }),
  adminDenyPlea: (id: number) =>
    request<{ id: number; state: string }>(`/api/admin/pleas/${id}/deny`, { method: "POST" }),
  openTournaments: () => request<OpenTournament[]>("/api/tournaments/open"),
  heldTournaments: () => request<OpenTournament[]>("/api/tournaments/held"),
  myTournaments: () => request<OpenTournament[]>("/api/tournaments/mine"),
  availability: (slug: string) =>
    request<Availability[]>(`/api/tournaments/${slug}/availability`),
  myRegistration: (slug: string) =>
    request<RegistrationDetail>(`/api/tournaments/${slug}/my-registration`),
  registerForTournament: (slug: string, data: RegisterPayload) =>
    request<RegistrationDetail>(`/api/tournaments/${slug}/register`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  cancelRegistration: (slug: string) =>
    request<RegistrationDetail>(`/api/tournaments/${slug}/my-registration/cancel`, {
      method: "POST",
    }),
  amendRegistration: (slug: string, data: RegisterPayload) =>
    request<RegistrationDetail>(`/api/tournaments/${slug}/my-registration/amend`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  pricePreview: (slug: string, data: PricePreviewPayload) =>
    request<PricePreview>(`/api/tournaments/${slug}/price-preview`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  paymentInstructions: (slug: string) =>
    request<PaymentInstructions>(`/api/tournaments/${slug}/my-registration/payment`),
  updateRoster: (slug: string, teamId: number, members: RosterMemberInput[]) =>
    request<TeamEntry>(`/api/tournaments/${slug}/my-registration/teams/${teamId}/roster`, {
      method: "PUT",
      body: JSON.stringify({ members }),
    }),
  consoleTeams: (slug: string) =>
    request<ConsoleTeamDiscipline[]>(`/api/tournaments/${slug}/teams`),
  queue: (slug: string) => request<Queue>(`/api/tournaments/${slug}/queue`),
  /** Promote one queued placement into a free seat: bills it, opens a payment
   *  window and sends instructions. */
  admitSubstitute: (slug: string, registrationId: number, disciplineSlug: string) =>
    request<RegistrationDetail>(
      `/api/tournaments/${slug}/registrations/${registrationId}/admit/${disciplineSlug}`,
      { method: "POST" },
    ),
  /** The inverse: free the seat and close any payment window. Refused on a
   *  paid registration, whose route is cancellation. */
  returnToQueue: (slug: string, registrationId: number, disciplineSlug: string) =>
    request<RegistrationDetail>(
      `/api/tournaments/${slug}/registrations/${registrationId}/return-to-queue/${disciplineSlug}`,
      { method: "POST" },
    ),
  /** Close seating early. Not reversible, and refused once seating has
   *  settled however it was triggered. */
  settleSeating: (slug: string) =>
    request<{ demoted: number; seating_settled_at: string }>(
      `/api/tournaments/${slug}/settle-seating`,
      { method: "POST" },
    ),
  unmatchedTransactions: (slug: string) =>
    request<Transaction[]>(`/api/tournaments/${slug}/payments/unmatched`),
  reinstateTransaction: (slug: string, transactionId: number) =>
    request<Transaction>(
      `/api/tournaments/${slug}/payments/transactions/${transactionId}/reinstate`,
      { method: "POST" },
    ),
  markTransactionForRefund: (slug: string, transactionId: number) =>
    request<Transaction>(
      `/api/tournaments/${slug}/payments/transactions/${transactionId}/mark-for-refund`,
      { method: "POST" },
    ),
};

export interface HRStatus {
  fighters: number;
  last_refresh: {
    at: string;
    status: string;
    fighter_count: number | null;
  } | null;
}

export interface DedupItem {
  key: string;
  kind: "same_id" | "likely";
  rows: { id: string; name: string; club: string | null; email: string | null }[];
  fields: Record<string, unknown>;
  note: string;
}

export interface ImportResult {
  batch_id: number;
  rows: number;
  parsed: number;
  reused: number;
  unparsed: number;
  problems: { row: number; problems: string }[];
  detail?: string;
}

/** The kinds of console work that run as an operation. */
export const OPERATION_KINDS = ["parse", "match", "dedup"] as const;
export type OperationKind = (typeof OPERATION_KINDS)[number];

/** `interrupted` is not a failure: the process running the work did not
 *  survive, what it committed stands, and running it again finishes it
 *  (spec console-operations, Work interrupted by a restart). */
export type OperationStatus = "running" | "done" | "failed" | "interrupted";

export interface Operation {
  id: number;
  kind: OperationKind;
  status: OperationStatus;
  /** Units of work this run will do — never the size of what it was pointed
   *  at, since rows already decided are reused rather than worked on. */
  total: number;
  done: number;
  started_at: string;
  finished_at: string | null;
  /** For a concluded run, what it produced; for a failed one, `{ error }`. */
  outcome: Record<string, unknown>;
}

export interface OperationsReport {
  running: Operation | null;
  concluded: Operation[];
}

export interface OperationStarted {
  operation_id: number;
}

/** An upload either starts a parse or, when every row is already decided,
 *  comes back with the outcome outright. */
export type ImportStarted = (OperationStarted & { batch_id: number; rows: number }) | ImportResult;

export interface ClearResult {
  rows: number;
  files: number;
}

export interface ImportStatus {
  batch: { id: number; filename: string; uploaded_at: string; rows: number } | null;
  /** Everything ever imported — what a clear would remove, which is more than
   *  the latest batch alone. */
  total: { rows: number; files: number };
}

/** A fencer entered by hand: the fields the tournament's own structure offers
 *  (spec etl-console, Manual entry fields follow the tournament's structure). */
export interface ManualEntryIn {
  name: string;
  nationality?: string | null;
  club?: string | null;
  hr_id?: number | null;
  email?: string | null;
  /** The moment the organizer states the fencer registered; absent means now,
   *  read in the tournament's own zone by the server. */
  registered_at?: string | null;
  disciplines: string[];
  weapon_rentals: string[];
  afterparty: boolean;
  notes?: string | null;
}

export interface ManualRow extends ManualEntryIn {
  id: number;
  registered_at: string;
}

export interface HRProfile {
  hr_id: number;
  name: string;
  nationality: string | null;
  club: string | null;
  claimed: boolean;
}
