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

export const api = {
  login: (email: string, password: string) =>
    request<{ token: string }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  tournaments: () => request<Tournament[]>("/api/tournaments"),
  tournament: (slug: string) => request<TournamentDetail>(`/api/tournaments/${slug}`),
  updateTournament: (slug: string, patch: Record<string, unknown>) =>
    request<TournamentDetail>(`/api/tournaments/${slug}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),
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
  hrSearch: (query: string) =>
    request<HRProfile[]>(`/api/hr/search?q=${encodeURIComponent(query)}`),
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
};

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
