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

export interface SheetRow {
  id: string;
  name: string;
  nationality: string | null;
  club: string | null;
  hr_id: number | null;
  disciplines: string[];
  state: string;
  vs: number | null;
  paid: boolean;
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
  sheet: (slug: string) => request<Sheet>(`/api/tournaments/${slug}/sheet`),
};
