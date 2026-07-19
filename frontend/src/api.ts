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

export interface Tournament {
  slug: string;
  display_name: string;
  date: string;
  language: string;
  owner_id: number | null;
  cancelled_at: string | null;
}

export type Role = "fencer" | "organizer" | "admin";

export interface Account {
  id: number;
  email: string;
  display_name: string;
  hr_id: number | null;
  nationality: string | null;
  club: string | null;
  role: Role;
  is_deployment_owner: boolean;
}

export type PleaState = "pending" | "granted" | "denied" | null;

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
}

export interface PleaQueueItem {
  id: number;
  fencer_id: number;
  email: string;
  display_name: string;
  message: string | null;
  created_at: string;
}

export interface Discipline {
  code: string;
  name: string;
  capacity: number;
  fee: number | null;
  fee_early: number | null;
}

export type ExtraCategory = "seminar" | "rental" | "afterparty" | "merch";

export interface ExtraItem {
  id: number;
  name: string;
  category: ExtraCategory;
  price: number;
  max_qty: number;
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
}

export interface Discount {
  name: string;
  condition: DiscountCondition;
  effect: DiscountEffect;
  scope: DiscountCategory[];
}

export interface TournamentDetail extends Tournament {
  reservation_validity_days: number;
  reminder_day: number;
  amount_tolerance_percent: number;
  refundable_until: string | null;
  bank_account: string | null;
  unpaid_list_treatment: string;
  output_sheet_url: string | null;
  early_bird_until: string | null;
  weapon_rental_fee: number;
  weapon_rental_fee_early: number | null;
  afterparty_fee: number;
  afterparty_fee_early: number | null;
  location: string | null;
  organizer_names: string[];
  registration_opens: string | null;
  registration_closes: string | null;
  discounts: Discount[];
  extra_items: ExtraItem[];
  setup_missing: string[] | null;
  disciplines: Discipline[];
}

export interface SheetRow {
  id: string;
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
  match_verdict?: "confirmed" | "proposed" | "none_found" | "unknown";
  merge_note?: string | null;
  _merged_into?: string;
  expires_at: string | null;
  paid_at: string | null;
  weapon_rentals: string[];
  afterparty: boolean;
  aftersparring: boolean;
  notes: string | null;
  [key: string]: unknown;
}

export interface AppliedChange {
  rule_id: number;
  phase: string;
  target: string;
  field: string;
  before: unknown;
  after: unknown;
  actor: string;
  at: string;
}

export interface Sheet {
  rows: SheetRow[];
  edits: AppliedChange[];
}

export type RegistrationStatus = "open" | "opens_on" | "closed";
export type MyRegistrationState = "none" | "reserved" | "paid" | "substitute" | "cancelled";

export interface OpenDiscipline {
  code: string;
  name: string;
  fee: number | null;
  taken: number;
  capacity: number;
  queue_length: number;
}

export interface OpenTournament {
  slug: string;
  display_name: string;
  date: string;
  location: string | null;
  organizer_names: string[];
  registration_status: RegistrationStatus;
  registration_opens_on: string | null;
  disciplines: OpenDiscipline[];
  my_registration_state: MyRegistrationState;
}

export interface PastTournament extends OpenTournament {
  organized: boolean;
}

export interface Availability {
  code: string;
  capacity: number;
  taken: number;
  free: number;
  queue_length: number;
}

export type RegistrationRowState = "reserved" | "paid" | "expired" | "cancelled";
export type RefundState = "not_applicable" | "pending" | "refunded";

export interface RegistrationEntry {
  code: string;
  is_substitute: boolean;
  queue_position: number | null;
}

export interface RegistrationExtraSelection {
  extra_item_id: number;
  name: string;
  category: ExtraCategory;
  qty: number;
}

export interface RegistrationDetail {
  state: RegistrationRowState;
  vs: number;
  total_amount: number;
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
}

export interface RegisterPayload {
  disciplines: string[];
  weapon_rentals?: string[];
  afterparty?: boolean;
  aftersparring?: boolean;
  accommodation?: string | null;
  notes?: string | null;
  wait_for_all?: boolean;
  extras?: { extra_item_id: number; qty: number }[];
}

export interface PricePreviewPayload {
  disciplines: string[];
  weapon_rentals?: string[];
  afterparty?: boolean;
  extras?: { extra_item_id: number; qty: number }[];
}

export interface PaymentInstructions {
  amount: number;
  iban: string;
  vs: number;
  message: string;
  expires_at: string | null;
  spayd: string;
  qr_png_base64: string;
}

export const api = {
  login: (email: string, password: string) =>
    request<{ token: string }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  tournaments: () => request<Tournament[]>("/api/tournaments"),
  tournament: (slug: string) => request<TournamentDetail>(`/api/tournaments/${slug}`),
  createTournament: (data: { slug: string; display_name: string; date: string }) =>
    request<TournamentDetail>("/api/tournaments", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateTournament: (slug: string, patch: Record<string, unknown>) =>
    request<TournamentDetail>(`/api/tournaments/${slug}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),
  taxonomy: () => request<Record<string, string>>("/api/taxonomy/disciplines"),
  addDiscipline: (
    slug: string,
    data: { code: string; capacity: number; fee: number | null },
  ) =>
    request<Discipline>(`/api/tournaments/${slug}/disciplines`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateDiscipline: (
    slug: string,
    code: string,
    data: { code: string; capacity: number; fee: number | null },
  ) =>
    request<Discipline>(`/api/tournaments/${slug}/disciplines/${code}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  deleteDiscipline: (slug: string, code: string) =>
    request<void>(`/api/tournaments/${slug}/disciplines/${code}`, { method: "DELETE" }),
  addExtraItem: (
    slug: string,
    data: { name: string; category: ExtraCategory; price: number; max_qty: number },
  ) =>
    request<ExtraItem>(`/api/tournaments/${slug}/extra-items`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateExtraItem: (
    slug: string,
    id: number,
    data: { name: string; category: ExtraCategory; price: number; max_qty: number },
  ) =>
    request<ExtraItem>(`/api/tournaments/${slug}/extra-items/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  deleteExtraItem: (slug: string, id: number) =>
    request<void>(`/api/tournaments/${slug}/extra-items/${id}`, { method: "DELETE" }),
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
  importTable: async (slug: string, file: File): Promise<ImportResult> => {
    const body = new FormData();
    body.append("file", file);
    const token = getToken();
    const response = await fetch(`/api/tournaments/${slug}/import`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body,
    });
    if (!response.ok) throw new ApiError(response.status, null);
    return response.json();
  },
  runMatching: (slug: string) =>
    request<{ matched: number; unmatched: number; reused: number }>(
      `/api/tournaments/${slug}/import/match`,
      { method: "POST" },
    ),
  runDedup: (slug: string) =>
    request<{ proposals: number; auto_merged: number; likely: number }>(
      `/api/tournaments/${slug}/import/dedup`,
      { method: "POST" },
    ),
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
  updateAccount: (patch: { email?: string; display_name?: string; club?: string }) =>
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
  pastTournaments: () => request<PastTournament[]>("/api/tournaments/mine/past"),
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
  pricePreview: (slug: string, data: PricePreviewPayload) =>
    request<{ total: number }>(`/api/tournaments/${slug}/price-preview`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  paymentInstructions: (slug: string) =>
    request<PaymentInstructions>(`/api/tournaments/${slug}/my-registration/payment`),
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

export interface HRProfile {
  hr_id: number;
  name: string;
  nationality: string | null;
  club: string | null;
}
