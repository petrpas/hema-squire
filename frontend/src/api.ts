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

/** A multipart upload. Its own function rather than an option on `request`,
 *  which sets a JSON content type the browser must choose itself for a
 *  FormData body — the boundary is the browser's to write. */
async function upload<T>(path: string, file: File): Promise<T> {
  const body = new FormData();
  body.append("file", file);
  const token = getToken();
  const response = await fetch(path, {
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
/** What the server says after a feed token is recorded or removed — never the
 *  token. `verified: false` means the bank could not be reached to check it,
 *  not that it was refused; a refusal is an error, not this. */
export interface FioTokenState {
  configured: boolean;
  verified: boolean;
}

export interface TournamentFlags {
  /** Disciplines specify where and when they occur. */
  feature_schedule: boolean;
  /** Squire handles payment processing: the only feature that changes what
   *  the system does rather than which controls Setup offers (D5). */
  feature_payments: boolean;
  feature_teams: boolean;
  feature_extras: boolean;
}

/** Who keeps a tournament's list of entrants.
 *
 *  A different axis from the four features above, and deliberately not a fifth
 *  one: those decide which advanced surfaces the console offers, and rest on
 *  the rule that turning one off hides settings without changing what a fencer
 *  experiences. This closes the registration form outright and takes the
 *  tournament out of the scheduler (design add-registrations-kept-by D1). */
export type RegistrationsKeptBy = "squire" | "organizer";

export const KEPT_BY_VALUES = [
  "squire",
  "organizer",
] as const satisfies readonly RegistrationsKeptBy[];

/** The three features, in the order the settings surface lists them. Payments
 *  is deliberately absent: it suspends machinery rather than hiding controls,
 *  and stands beside the tournament's mode (spec tournament-features,
 *  payments). Anything iterating "the features" iterates these three; a caller
 *  that also wants payments reads `feature_payments` by name, so that no list
 *  quietly puts them back in one category. */
export const TOURNAMENT_FEATURES = [
  "feature_schedule",
  "feature_teams",
  "feature_extras",
] as const satisfies readonly (keyof TournamentFlags)[];

export interface Tournament extends TournamentFlags {
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
  /** How many tournaments this account may open the console of. The account
   *  menu asks only whether there are any, and asks it on every signed-in
   *  page, so the answer rides on the account rather than on a listing. */
  organized_count: number;
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
  cities: string[];
  addresses: string[];
  bank_accounts: string[];
  // name and link travel together: choosing a remembered club fills both
  organizers: Organizer[];
}

/** How a seat is held until the seating deadline. `immediate` is what every
 *  tournament created before the mode existed does. */
export type PaymentMode = "immediate" | "deposit" | "reservation";

export interface TournamentDetail extends Tournament {
  payment_mode: PaymentMode;
  /** Substitutes who pay take free places by themselves (spec
   *  `tournament-admin`); off by default. */
  queue_payment_seats: boolean;
  /** Whether a Fio API token is on file, so the bank can be polled at all.
   *  Never the token itself — the console needs only this. */
  fio_token_configured: boolean;
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
  city: string | null;
  address: string | null;
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
  /** Who keeps the list of entrants. `organizer` means registration is held
   *  outside Squire and reaches it by import; no in-app registration opens and
   *  no lifecycle runs (design add-registrations-kept-by). */
  registrations_kept_by: RegistrationsKeptBy;
  /** Where registration is held when Squire does not hold it. Mandatory to
   *  publish a tournament the organizer keeps; optional otherwise. Squire
   *  never fetches it (design add-external-registration D1). */
  external_registration_url: string | null;
  /** Live registrations fencers made in the application themselves, excluding
   *  ones issued from an imported row. What the confirmation states when the
   *  organizer takes the tournament out of Squire's keeping — the people it
   *  would stop managing. Filled by the detail endpoint; null elsewhere. */
  in_app_registrations: number | null;
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

/** A tournament as a fencer reads it — the answer of the fencer-facing detail
 *  endpoint, which carries no organizer configuration at all (spec
 *  `public-browsing`).
 *
 *  Written as a `Pick` of `TournamentDetail` rather than as its own interface
 *  so the two cannot describe the same field differently, and so a key that
 *  stops existing on the console's type stops compiling here. The server's
 *  `FencerTournamentOut` is the authority on which keys arrive; this list
 *  mirrors it.
 *
 *  Every fencer-facing component takes this type rather than
 *  `TournamentDetail`, which means the console can still hand it its own
 *  fuller object — a superset satisfies it — while the fencer's page cannot
 *  reach for a field that no longer arrives. */
export type FencerTournament = Pick<
  TournamentDetail,
  | "slug"
  | "display_name"
  | "subtitle"
  | "has_logo"
  | "date"
  | "city"
  | "address"
  | "description"
  | "qualification_open"
  | "qualification_criteria"
  | "registration_instructions"
  | "organizers"
  | "disciplines"
  | "extra_items"
  | "discounts"
  | "local_currency"
  | "eur_payments_enabled"
  | "currency_mode"
  | "registration_opens"
  | "registration_opens_time"
  | "registration_closes"
  | "amendments_close"
  | "team_composition_deadline"
  | "timezone"
  | "registration_opens_at"
  | "server_time"
  | "registrations_kept_by"
  | "external_registration_url"
  | "feature_schedule"
  | "feature_payments"
  | "feature_teams"
  | "feature_extras"
>;

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
  /** Each queued placement's queue moment by discipline slug, which orders the
   *  rows below a discipline tab's line (spec `seating-queue`). */
  queued_since: Record<string, string>;
  /** The participation condition's disciplines, by slug; empty for none. */
  conditional: string[];
  /** A payment sent from the queue is held for the organizer. */
  payment_held?: boolean;
  state: string;
  /** The registration standing in this row's place, where one has been issued
   *  for it; null while the row is still a row. Disciplines are the row's to
   *  correct only while it is one — once issued, the entries are the
   *  registration's and a cell edit would show a change the billing never
   *  made. */
  registration_id: number | null;
  vs: number | null;
  paid: boolean;
  /** Settled with nothing passing through Squire, and why. The outstanding
   *  column reads this and states the balance as waived rather than owed: a
   *  reader who took the full total there for a fault would be misreading the
   *  one true thing about the row. */
  settled_by_hand?: boolean;
  settled_by_hand_reason?: string | null;
  /** What the waiver forgave, as a decimal string in `outstanding_currency` —
   *  null where it forgave the whole price, and on every row no waiver
   *  touched. A waiver owes nothing, so `outstanding_amount` is zero on such a
   *  row and cannot say how much was written off; the outstanding column names
   *  the sum wherever a payment already stood against the price. */
  waived_amount?: string | null;
  registered_at: string | null;
  total_amount: number | null;
  /** What is still owed, or negative what is over, as a decimal string — the
   *  same quantity and the same shape as `RegistrationDetail.outstanding_amount`.
   *  Absent on a row with no registration behind it, such as an imported one. */
  outstanding_amount?: string;
  /** The currency that balance is stated in — the lane the money arrived in,
   *  the local one where none has. There is no second figure: the two lanes
   *  are alternative prices, so the one nobody paid into is not a debt. */
  outstanding_currency?: Currency;
  problems: string | null;
  match_verdict?: "confirmed" | "found" | "proposed" | "none_found" | "unknown";
  /** The evidence register: what HEMA Ratings holds for this row's hr_id.
   *  Empty where there is no id, or the fighters index does not know it — an
   *  absence is stated, not omitted (spec `etl-console`, The ledger idiom). */
  hr_name: string | null;
  hr_nationality: string | null;
  hr_club: string | null;
  merge_note?: string | null;
  /** The fencer this seat was taken from, where a substitution took it. A
   *  statement about the row, not a removal: the row is fully live and the
   *  table says whose seat it was (spec `etl-console`, A substituted row states
   *  that it was substituted). */
  _substituted_for?: string | null;
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
  /** Of those, the ones this tournament lends nothing by that name and so
   *  bills nothing for. Empty on a tournament priced by a flat rental fee,
   *  where a rental is billed whatever it is called. */
  unpriced_rentals?: string[];
  afterparty: boolean;
  aftersparring: boolean;
  notes: string | null;
  /** The address this seat is written to: its own contact address where a
   *  substitution left it one, the account holder's otherwise
   *  (`emails.recipient`). Null on a row that carries none. */
  email: string | null;
  [key: string]: unknown;
}

export type Amendment = {
  /** What the registration was priced at before the correction, and after it.
   *  The pair, not the difference: an organizer reads a correction by seeing
   *  where it came from. */
  previous_total: string | null;
  total: string | null;
  /** Whether the fencer was written to. Only a correction that leaves them
   *  owing more is (spec `discipline-amendment`). */
  notified: boolean;
};

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

/** One table of the Export phase's band, derived from the tournament: the
 *  fencer list, one per individual discipline, one per extra-item category it
 *  offers something in. `key` names what the table is of and is empty for the
 *  fencer table, which is of the whole tournament. */
export interface ExportTab {
  kind: "fencers" | "discipline" | "category" | "summary";
  key: string;
  label: string;
  capacity: number | null;
  /** What a discipline tab's line means here: a queue boundary, or a bare
   *  capacity mark on a tournament whose mode queues nobody. */
  line: "queue" | "capacity" | null;
}

/** A tab as the band lists it, with how many it holds: `queued` counts a
 *  discipline's substitute entries and is 0 on every other tab. Neither
 *  follows the tab's active-only switch (spec export-tables). */
export interface ExportBandTab extends ExportTab {
  /** Null on the summary tab, which lists an offer rather than a population. */
  count: number | null;
  queued: number;
}

/** One line of the Export summary (spec export-summary): a discipline's seated
 *  or queued fencers, or the pieces of one item — of one answer to its option
 *  where it asks one, or of the selections that gave none (`missing`).
 *  Structured rather than labelled, so the label is composed in the language
 *  the reader asked for. */
export interface ExportSummaryLine {
  kind: "discipline" | "queue" | "item";
  category: string;
  name: string;
  option: string | null;
  missing: boolean;
  /** Null on a discipline's lines. Two items may share a name. */
  item_id: number | null;
  paid: number;
  unpaid: number;
}

export interface ExportTable extends ExportTab {
  rows: SheetRow[];
}

/** What the Export rail needs before a first export can be run: whether this
 *  deployment holds Google credentials at all, the address they act as — which
 *  the organizer has to share their spreadsheet with for writing — and where
 *  this tournament currently writes. `service_account` is null exactly when
 *  `configured` is false. */
export interface ExportSheetConfig {
  configured: boolean;
  service_account: string | null;
  output_sheet_url: string | null;
}

/** `elsewhere` says the organizer keeps the registrations, so this tournament
 *  has no window here at all — distinct from `closed`, which means a window has
 *  passed (design add-registrations-kept-by D4). */
export type RegistrationStatus = "open" | "opens_on" | "closed" | "elsewhere";
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
  /** The town, and only the town: the card has room for the name and nothing
   *  more, and the address is read on the tournament's own page. */
  city: string | null;
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
  /** The caller's own standing on this tournament — **absent** when there is
   *  no account behind the request, rather than sent as `none` (spec
   *  `public-browsing`). Absence is the fact that there is nobody to have a
   *  standing, which is what separates an anonymous reader from a signed-in
   *  fencer who happens to hold no registration. */
  my_registration_state?: MyRegistrationState;
  /** Whether the caller may manage this tournament: owner or console team
   *  member. Independent of my_registration_state — an entry may carry both —
   *  and absent for the same reason as it, with no account to ask about. */
  organized?: boolean;
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
  /** One of the disciplines the fencer attends only together (spec
   *  `registration`, Participation condition). */
  conditional: boolean;
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
  /** Absent where the registration was never given one: a tournament whose
   *  organizer keeps the roster mints no symbols. */
  vs: number | null;
  total_amount: number;
  /** What is still owed, or negative what is over; a decimal string. */
  outstanding_amount: string;
  /** The currency that balance is stated in. */
  outstanding_currency: Currency;
  /** The stored EUR price, absent (not derived) when the tournament does not
   *  price in EUR. */
  total_eur: number | null;
  expires_at: string | null;
  registered_at: string;
  /** Where the participation condition is not met, its disciplines that have
   *  no free place — what the fencer is waiting for. */
  condition_waits_for: string[];
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
  /** The breakdown behind `total_amount`, one entry per configured discount in
   *  configured order — the lines of a registration state list prices, so the
   *  applied ones are what makes the total add up. Empty for a tournament that
   *  configures none. */
  discounts: DiscountBreakdown[];
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
  /** The participation condition, by slug: every individual discipline
   *  selected where the fencer ticked it, none otherwise. */
  condition?: string[];
  weapon_rentals?: string[];
  afterparty?: boolean;
  aftersparring?: boolean;
  accommodation?: string | null;
  notes?: string | null;
  extras?: ExtraSelectionPayload[];
  teams?: TeamEntryPayload[];
}

/** Where an amendment would place the registration, before it is sent: a
 *  statement, not a reservation (design participation-condition D5). */
export interface AmendmentPlacement {
  queued: string[];
  moves_to_queue: boolean;
  refusal: string | null;
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

/** One individual discipline's places, as the Queue phase states them beside
 *  its roster. The rows are the discipline's export table (design queue-rosters
 *  D1). */
export interface QueueDiscipline {
  slug: string;
  name: string;
  capacity: number;
  taken: number;
  free: number;
  /** How many wait below the line: substitutes, or waitlisted teams. */
  queued: number;
}

/** One team as the Queue phase's team roster lists it, with the money of its
 *  entering fencer's registration in the shape a fencer row states it
 *  (design team-queue D1). */
export interface QueueTeam {
  team_id: number;
  registration_id: number;
  name: string;
  entering_fencer: string;
  members: number;
  team_min: number;
  team_max: number;
  waitlisted: boolean;
  waitlist_position: number | null;
  waitlisted_since: string;
  demoted: boolean;
  paid: boolean;
  settled_by_hand: boolean;
  outstanding_amount: string;
  outstanding_currency: Currency;
  expires_at: string | null;
}

export interface Queue {
  /** The resolved deadline, never the raw column. */
  seating_deadline: string;
  seating_settled_at: string | null;
  /** How many registrations settling now would move below the line, and how
   *  many of their teams would be waitlisted with them. */
  pending_demotions: number;
  pending_team_waitlistings: number;
  disciplines: QueueDiscipline[];
  /** Each team discipline's slots, counted in teams. */
  team_disciplines: QueueDiscipline[];
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

/** `likely` is a **proposal**, not an outcome: the resolver read a fencer's
 *  name in the payer's own words and is asking a person. No money has moved and
 *  nobody has been mailed while a transaction sits in it. */
export type TransactionStatus =
  | "unmatched"
  | "flagged"
  | "matched"
  | "partial"
  | "likely"
  | "resolved";

export interface RankedFencer {
  fencer_id: number;
  name: string;
  registration_id: number;
  /** Null on a tournament whose registrations carry no variable symbol. */
  vs: number | null;
  outstanding_amount: string;
  score: number;
  /** Strong enough and far enough ahead to have been proposed; at most one. */
  proposed: boolean;
  /** The organizer has already refused this fencer for this payment. */
  rejected: boolean;
}

export interface TransactionRoster {
  transaction_id: number;
  /** What the roster was ranked against, stated so a surprising order is
   *  explicable. */
  query: string;
  fencers: RankedFencer[];
}

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
  /** Only meaningful for an unmatched transaction: VS values detected in its
   *  text that resolve to a registration. The link dialog offers these as
   *  one-click choices; empty when the backend recognised nothing. */
  candidate_vs: number[];
  /** Who the payment's own text named, read at parse time — never the payer. */
  named_person: string | null;
  /** Who the resolver proposes while the status is `likely`. A proposal, not
   *  an outcome: nothing is credited until a person confirms. */
  proposed_fencer_id: number | null;
  proposed_fencer_name: string | null;
  /** When the matcher last considered this transaction; null before it has. */
  last_evaluated_at: string | null;
  /** Why the registration this transaction names was already settled, where a
   *  person settled it. Null on every ordinary conflict — a registration paid
   *  by an earlier transaction makes no hand-settled claim. */
  settled_by_hand_reason: string | null;
  /** The payment an organizer recorded that settled this transaction's
   *  registration, where one did. The organizer resolving a flagged row is
   *  deciding whether this is further money or the same money arriving twice,
   *  and needs the earlier act in front of them. */
  settled_by_recorded_payment: ManualPayment | null;
}

/** One registration a credited transaction paid for, and what reversing that
 *  credit would leave it reading. */
export interface CreditReversalRow {
  registration_id: number;
  fencer_name: string;
  vs: number | null;
  /** A decimal string, as every money figure the API states is. */
  amount: string;
  currency: Currency;
  /** Whether this registration stops reading as paid once the credit is gone. */
  unsettles: boolean;
}

/** What reversing one credited transaction would do, asked before it is done. */
export interface CreditReversal {
  transaction_id: number;
  registrations: CreditReversalRow[];
}

/** What carried the money a credit records. */
export type CreditSource = "bank_transaction" | "manual_payment";

/** Why the money was credited, which is not the same question as what carried
 *  it: one transaction the matcher resolved and the same transaction credited
 *  because an organizer paired it are one source with two different decisions
 *  behind them. */
export type CreditOrigin = "auto_vs" | "payment_link" | "reinstate" | "refund_hold" | "recorded";

/** One payment holding a live credit, whichever half of the journal carried it.
 *
 *  One table where the console had three. A transaction the matcher resolved, a
 *  pairing an organizer drew and a cash payment somebody entered are the same
 *  fact — money credited to a fencer — and answering it in three places meant
 *  the pairing view and the credited view listing overlapping rows under
 *  different keys. */
export interface CreditedPayment {
  source_kind: CreditSource;
  source_id: number;
  value_date: string;
  /** A decimal string, as every money figure the API states is. */
  amount: string;
  currency: Currency;
  /** The bank's counterparty, where a statement carried the money. */
  payer_name: string | null;
  /** The organizer who said so, where a person did. */
  recorded_by: string | null;
  method: PaymentMethod | null;
  note: string | null;
  message: string | null;
  origin: CreditOrigin;
  credits: CreditReversalRow[];
}

/** What is to be done with a payment that lies on nobody. Not which table it
 *  belongs to — the credit journal answers that — but what the organizer is
 *  being asked to decide. */
export type Disposition = "proposal" | "refused" | "paired_uncredited" | "none";

/** A registration a pairing names, for a payment that credited nothing. */
export interface PairedRegistration {
  registration_id: number;
  fencer_name: string;
  vs: number | null;
}

/** A payment that arrived and lies on nobody.
 *
 *  Membership is the journal's answer and not the transaction's status: a
 *  pairing marks a transaction resolved even where it credited nothing, and
 *  such a payment used to read as done while its money sat on the account. */
export interface UncreditedPayment extends Transaction {
  disposition: Disposition;
  /** What the proposed fencer still owes, so the organizer confirms against a
   *  balance rather than against a name alone. */
  proposed_outstanding: string | null;
  paired_registrations: PairedRegistration[];
}

/** How money an organizer recorded by hand arrived. */
export type PaymentMethod = "cash" | "transfer" | "card" | "other";

/** A payment the organizer says arrived, which Squire never saw: cash at the
 *  desk, a transfer to another account, a card terminal. Credited exactly as an
 *  ingested transaction is, and never a row in the statement ledger. */
export interface ManualPayment {
  id: number;
  registration_id: number;
  fencer_name: string;
  /** A decimal string, as every money figure the API states is. */
  amount: string;
  currency: Currency;
  received_on: string;
  method: PaymentMethod;
  note: string | null;
  recorded_by: string;
  created_at: string;
  /** Whether removing this payment would return the registration to reserved,
   *  so the console can say what removal will do before it is confirmed. */
  removal_unsettles: boolean;
}

export interface ManualPaymentInput {
  registration_id: number;
  amount: string;
  currency: Currency;
  received_on: string;
  method: PaymentMethod;
  note?: string | null;
}

/** A reservation that lapsed while holding money credited to it. The payment
 *  matched, so it is in neither transaction queue — this is the only view of
 *  it. */
export interface ExpiredHolding {
  registration_id: number;
  fencer_name: string;
  vs: number | null;
  /** A decimal string, as every credited amount the API states is. */
  credited_amount: string;
  credited_eur_amount: string | null;
  expired_at: string;
}

/** A persisted manual operation as the rules API states it. Payment links are
 *  the `payment_link` kind: they replay opaquely and so never reach the edits
 *  log, which is why the payments phase lists them itself. */
export interface Rule {
  id: number;
  phase: string;
  kind: string;
  target: string;
  payload: Record<string, unknown>;
  created_by: number;
  created_at: string;
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
  /** Instructions for a waiting registration's claim: the payment takes the
   *  places waited for only if all are free when it is credited. */
  claim: boolean;
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
  /** The fencer's view: public, and carrying no organizer configuration. */
  tournament: (slug: string) => request<FencerTournament>(`/api/tournaments/${slug}/public`),
  /** The console's view: every field, behind console access. */
  consoleTournament: (slug: string) => request<TournamentDetail>(`/api/tournaments/${slug}`),
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
  /** Its own request, and the only way a token is recorded: the server checks
   *  it against the bank as it arrives, which the tournament PATCH — a save of
   *  forty fields — is the wrong place to do. `verified` is false where the
   *  bank could not be reached; the token is stored either way. */
  setFioToken: (slug: string, token: string) =>
    request<FioTokenState>(`/api/tournaments/${slug}/fio-token`, {
      method: "PUT",
      body: JSON.stringify({ token }),
    }),
  clearFioToken: (slug: string) =>
    request<FioTokenState>(`/api/tournaments/${slug}/fio-token`, { method: "DELETE" }),
  getTournamentFlags: (slug: string) =>
    request<TournamentFlags>(`/api/tournaments/${slug}/features`),
  // written as a whole, never one flag at a time, so the whole set goes in one
  // request (spec tournament-features)
  setTournamentFlags: (slug: string, flags: TournamentFlags) =>
    request<TournamentDetail>(`/api/tournaments/${slug}/features`, {
      method: "PATCH",
      body: JSON.stringify(flags),
    }),
  /** Its own request rather than a field on the mode: the four features are a
   *  shape chosen as a whole, and this is a different axis (design D1). */
  setRegistrationsKeptBy: (slug: string, value: RegistrationsKeptBy) =>
    request<TournamentDetail>(`/api/tournaments/${slug}/registrations-kept-by`, {
      method: "PATCH",
      body: JSON.stringify({ registrations_kept_by: value }),
    }),
  /** Settled with nothing passing through Squire. Writes the verdict and no
   *  amount: what has been credited stays exactly as it was, because nothing
   *  arrived (spec payments).
   *
   *  Where Squire handles the payments this is the waiver and the reason is
   *  required; where it does not, the reason is optional and the mark is the
   *  organizer's word that they collected the money themselves. */
  markSettled: (slug: string, registrationId: number, settled: boolean, reason?: string | null) =>
    request<RegistrationDetail>(
      `/api/tournaments/${slug}/registrations/${registrationId}/settled?settled=${settled}` +
        (reason ? `&reason=${encodeURIComponent(reason)}` : ""),
      { method: "POST" },
    ),
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
  deleteLogo: (slug: string) => request<void>(logoUrl(slug), { method: "DELETE" }),
  sheet: (slug: string) => request<Sheet>(`/api/tournaments/${slug}/sheet`),
  /** Creates a rule. `amendment` comes back only for a discipline amendment:
   *  what the correction did to the registration's total, and whether the
   *  fencer was written to — the half of the edit the cell does not show. */
  createRule: (
    slug: string,
    rule: { phase: string; kind: string; target: string; payload: Record<string, unknown> },
  ) =>
    request<{ id: number; amendment?: Amendment | null }>(`/api/tournaments/${slug}/rules`, {
      method: "POST",
      body: JSON.stringify(rule),
    }),
  /** Hands a fencer-list row's seat to somebody else. A rule like any other —
   *  the seat keeps its number, its symbol, its totals and its journal, and
   *  only the person changes (spec `fencer-substitution`). */
  substituteFencer: (slug: string, target: string, substitute: SubstituteIn) =>
    request<{ id: number }>(`/api/tournaments/${slug}/rules`, {
      method: "POST",
      body: JSON.stringify({
        phase: "fencers",
        kind: "row_substitute",
        target,
        payload: substitute,
      }),
    }),
  /** Links an unmatched transaction to one or more registrations by VS. The
   *  first frontend caller of the manual-link endpoint. Rejects with 404 and
   *  `detail.unknown_vs` when a VS resolves to nothing, 409 `already_matched`
   *  when a concurrent poll matched the transaction first. */
  /** Which registrations a payment covers, addressed either way: by variable
   *  symbol where the payer quoted one, by registration id where there is none
   *  to quote. A registration on a tournament whose organizer keeps the roster
   *  carries no symbol at all. */
  linkTransaction: (
    slug: string,
    transaction_id: number,
    vs: number[],
    registration_ids: number[] = [],
  ) =>
    request<{ rule_id: number; applied: number }>(`/api/tournaments/${slug}/payments/link`, {
      method: "POST",
      body: JSON.stringify({ transaction_id, vs, registration_ids }),
    }),
  expiredHolding: (slug: string) =>
    request<ExpiredHolding[]>(`/api/tournaments/${slug}/payments/expired-holding`),
  recordManualPayment: (slug: string, data: ManualPaymentInput) =>
    request<ManualPayment>(`/api/tournaments/${slug}/payments/manual`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  removeManualPayment: (slug: string, paymentId: number) =>
    request<ManualPayment>(`/api/tournaments/${slug}/payments/manual/${paymentId}`, {
      method: "DELETE",
    }),
  rules: (slug: string, phase: string) =>
    request<Rule[]>(`/api/tournaments/${slug}/rules?phase=${encodeURIComponent(phase)}`),
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
  importTable: (slug: string, file: File): Promise<ImportStarted> =>
    upload<ImportStarted>(`/api/tournaments/${slug}/import`, file),
  /** Import a bank statement from any bank, as a started operation. The ingest
   *  counts land in the operation's outcome, not in this response. Rejects
   *  with 409 `no_statement_parser` where an unrecognised statement arrives on
   *  a deployment with no model configured, and 422
   *  `unsupported_statement_format` for a file that is neither CSV nor XLSX. */
  importStatement: (slug: string, file: File): Promise<OperationStarted & { rows: number }> =>
    upload(`/api/tournaments/${slug}/payments/import-statement`, file),
  /** Pull the tournament's own window from the bank's API. Offered only where
   *  the tournament has a token; without one the endpoint answers 409.
   *
   *  `since` moves the window's start later, and answers one refusal only: 409
   *  `fio_authorization_required`, where Fio will not serve days older than
   *  ninety without the organizer unlocking its history. It cannot widen the
   *  window, and a start past the window's end is refused rather than polled. */
  fioPoll: (slug: string, since?: string) =>
    request<IngestAndMatch>(
      `/api/tournaments/${slug}/payments/fio-poll${since ? `?since=${since}` : ""}`,
      { method: "POST" },
    ),
  /** Run the payment lifecycle passes now — expiries, reminders and
   *  holding-payment events — rather than waiting for the scheduler. */
  processLifecycle: (slug: string) =>
    request<unknown>(`/api/tournaments/${slug}/payments/process`, { method: "POST" }),
  /** Hard, total and final: everything the tournament ever imported. The
   *  console confirms before calling (spec table-import, Clearing is warned
   *  about and irreversible). */
  clearImports: (slug: string) =>
    request<ClearResult>(`/api/tournaments/${slug}/import`, { method: "DELETE" }),
  importStatus: (slug: string) => request<ImportStatus>(`/api/tournaments/${slug}/import/status`),
  createManualRow: (slug: string, entry: ManualEntryIn) =>
    request<ManualEntryOut>(`/api/tournaments/${slug}/manual-rows`, {
      method: "POST",
      body: JSON.stringify(entry),
    }),
  /** What clearing the tournament's payments would remove, and what stands in
   *  its way — read before offering the action, so a refusal is stated rather
   *  than discovered. */
  /** How many short payments the tolerance as it stands would now let
   *  through — stated by the tolerance card before the organizer commits. */
  resettleablePayments: (slug: string) =>
    request<{ resettleable: number }>(`/api/tournaments/${slug}/payments/resettle`),
  /** Re-decide those, crediting nothing: the money is already on the
   *  registration and only the verdict on it is asked again. */
  resettlePayments: (slug: string) =>
    request<{ settled: number }>(`/api/tournaments/${slug}/payments/resettle`, {
      method: "POST",
    }),
  clearablePayments: (slug: string) =>
    request<ClearablePayments>(`/api/tournaments/${slug}/payments/clear`),
  /** Remove every payment taken in, and the stored readings behind them. */
  clearPayments: (slug: string) =>
    request<{ payments: number }>(`/api/tournaments/${slug}/payments`, {
      method: "DELETE",
    }),
  /** How many fencer-list rows the next intake will issue registrations for,
   *  and whether it may run yet — what the intake panel states before the
   *  upload, in place of the confirmation there no longer is. */
  /** The active payment links, resolved into the payment and the fencers each
   *  joins — the rule states neither in a form anyone can read. */
  issuableCount: (slug: string) => request<IssuableCount>(`/api/tournaments/${slug}/import/issue`),
  /** Issue registrations where no intake will do it: a tournament whose
   *  payments Squire does not collect has none, so the Payments phase calls
   *  this on arrival. Refused where payments are on — there, intake issues.
   *  Synchronous: it asks no model, so there is no operation to watch. */
  issueRegistrations: (slug: string) =>
    request<IssueReport>(`/api/tournaments/${slug}/import/issue`, { method: "POST" }),
  runMatching: (slug: string) =>
    request<OperationStarted>(`/api/tournaments/${slug}/import/match`, { method: "POST" }),
  runDedup: (slug: string) =>
    request<OperationStarted>(`/api/tournaments/${slug}/import/dedup`, { method: "POST" }),
  /** What the console polls: the tournament's running operation and the most
   *  recent concluded one of each kind (design D7). */
  operations: (slug: string) => request<OperationsReport>(`/api/tournaments/${slug}/operations`),
  dedupGroups: (slug: string) =>
    request<DedupGroup[]>(`/api/tournaments/${slug}/import/dedup/groups`),
  /** `fields` and `note` carry the conclusion as the organizer left it; omitted,
   *  the recommendation stands in (spec `table-import`, The proposal is
   *  corrected before it is confirmed). */
  dedupDecide: (
    slug: string,
    key: string,
    accept: boolean,
    fields?: Record<string, unknown>,
    note?: string,
  ) =>
    request<{ status: string }>(`/api/tournaments/${slug}/import/dedup/decide`, {
      method: "POST",
      body: JSON.stringify({ key, accept, fields, note }),
    }),
  exportSheet: (slug: string, english = false) =>
    request<{ worksheets: string[]; fencers: number }>(
      `/api/tournaments/${slug}/export/sheet?english=${english}`,
      { method: "POST" },
    ),
  exportSheetConfig: (slug: string) =>
    request<ExportSheetConfig>(`/api/tournaments/${slug}/export/sheet-config`),
  exportTabs: (slug: string) => request<ExportBandTab[]>(`/api/tournaments/${slug}/export/tables`),
  exportSummary: (slug: string) =>
    request<{ lines: ExportSummaryLine[] }>(`/api/tournaments/${slug}/export/summary`),
  exportTable: (slug: string, kind: string, key: string) =>
    request<ExportTable>(
      `/api/tournaments/${slug}/export/table?kind=${encodeURIComponent(kind)}&key=${encodeURIComponent(key)}`,
    ),
  hrStatus: () => request<HRStatus>("/api/hr/status"),
  hrRefresh: () =>
    request<{ status: string; fighters: number }>("/api/hr/refresh", {
      method: "POST",
    }),
  ratingsSnapshot: (slug: string) =>
    request<{ status: string; fencers: number; ratings: number }>(
      `/api/tournaments/${slug}/ratings/snapshot`,
      { method: "POST" },
    ),
  ratingsLatest: (slug: string) =>
    request<{ taken_at: string | null; ratings: number }>(`/api/tournaments/${slug}/ratings`),
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
  availability: (slug: string) => request<Availability[]>(`/api/tournaments/${slug}/availability`),
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
  previewAmendment: (slug: string, data: RegisterPayload) =>
    request<AmendmentPlacement>(`/api/tournaments/${slug}/my-registration/amend/preview`, {
      method: "POST",
      body: JSON.stringify(data),
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
  queueTeams: (slug: string, disciplineSlug: string) =>
    request<QueueTeam[]>(`/api/tournaments/${slug}/queue/teams/${disciplineSlug}`),
  admitTeam: (slug: string, registrationId: number, teamId: number) =>
    request<RegistrationDetail>(
      `/api/tournaments/${slug}/registrations/${registrationId}/teams/${teamId}/admit`,
      { method: "POST" },
    ),
  returnTeamToWaitlist: (slug: string, registrationId: number, teamId: number) =>
    request<RegistrationDetail>(
      `/api/tournaments/${slug}/registrations/${registrationId}/teams/${teamId}/return-to-waitlist`,
      { method: "POST" },
    ),
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
  /** Every payment that arrived and lies on nobody, each stating what is to be
   *  done with it. One table where there were three: proposals, unresolved
   *  money and the money a check refused are one question with the answer to a
   *  second written beside it. */
  uncreditedPayments: (slug: string) =>
    request<UncreditedPayment[]>(`/api/tournaments/${slug}/payments/uncredited`),
  confirmProposal: (slug: string, transactionId: number) =>
    request<{ rule_id: number; applied: number }>(
      `/api/tournaments/${slug}/payments/likely/${transactionId}/confirm`,
      { method: "POST" },
    ),
  rejectProposal: (slug: string, transactionId: number) =>
    request<Transaction>(`/api/tournaments/${slug}/payments/likely/${transactionId}/reject`, {
      method: "POST",
    }),
  /** The whole roster ordered by how well each fencer matches this payment's
   *  own text, with the strongest marked where there is one. */
  transactionRoster: (slug: string, transactionId: number) =>
    request<TransactionRoster>(
      `/api/tournaments/${slug}/payments/transactions/${transactionId}/roster`,
    ),
  reinstateTransaction: (slug: string, transactionId: number) =>
    request<Transaction>(
      `/api/tournaments/${slug}/payments/transactions/${transactionId}/reinstate`,
      { method: "POST" },
    ),
  /** Every payment holding a live credit, the bank's and the hand-recorded
   *  together, each naming who it credited and why. */
  creditedPayments: (slug: string) =>
    request<CreditedPayment[]>(`/api/tournaments/${slug}/payments/credited`),
  reversalPreflight: (slug: string, transactionId: number) =>
    request<CreditReversal>(
      `/api/tournaments/${slug}/payments/transactions/${transactionId}/reversal`,
    ),
  reverseTransactionCredit: (slug: string, transactionId: number) =>
    request<Transaction>(
      `/api/tournaments/${slug}/payments/transactions/${transactionId}/reverse`,
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

/** One record of a candidate duplicate group, as the console renders it: the
 *  fields a merge decides, plus the number that names the row and the evidence
 *  register it is identified by. A member is drawn from this alone — the
 *  deduplication view joins nothing against the sheet (design D2). */
export interface DedupMember {
  id: string;
  number: number | null;
  name: string | null;
  nationality: string | null;
  email: string | null;
  club: string | null;
  hr_id: number | null;
  hr_name: string | null;
  hr_nationality: string | null;
  hr_club: string | null;
  disciplines: string[];
  weapon_rentals: string[];
  afterparty: boolean;
  notes: string | null;
  problems: string | null;
  registered_at: string | null;
  [key: string]: unknown;
}

/** A merged record and the note explaining it: what the system recommends, and
 *  — once a merge stands — what the organizer confirmed. */
export interface DedupConclusion {
  fields: Record<string, unknown>;
  note: string;
}

/** `merged` is true while the group's merge rule stands, so withdrawing the
 *  merge from the manual-edits log returns the group to `pending` rather than
 *  settling it unmerged (design D3). */
export type DedupVerdict = "pending" | "merged" | "separate";

export interface DedupGroup {
  key: string;
  kind: "same_id" | "surely" | "likely";
  verdict: DedupVerdict;
  /** Whose verdict it is, where one has been reached. A `surely` group merged
   *  by the run reads `llm` until someone disagrees with it. */
  decided_by: "llm" | "organizer" | null;
  members: DedupMember[];
  recommendation: DedupConclusion;
  conclusion: DedupConclusion | null;
}

export interface ImportResult {
  batch_id: number;
  /** rows this upload brought that the tournament did not already hold */
  rows: number;
  /** rows of the file the tournament already held, recognised and not taken in
   *  a second time. Absent on an outcome stored before uploads accumulated —
   *  those runs replaced the batch rather than adding to it, and counted
   *  nothing as recognised */
  skipped?: number;
  parsed: number;
  reused: number;
  unparsed: number;
  problems: { row: number; problems: string }[];
  detail?: string;
}

export interface ClearablePayments {
  /** Transactions the tournament holds, whatever their state. */
  payments: number;
  /** Of those, how many have been credited to a registration. Any at all makes
   *  clearing unavailable: money the tournament acted on is not deletable. */
  credited: number;
}

export interface IssuableCount {
  /** Rows that state who is competing and have no registration yet. */
  pending_rows: number;
  /** Duplicate groups still awaiting a verdict. Intake refuses while any
   *  stands: a merge collapses rows, not registrations, so issuing ahead of
   *  the verdict leaves one person holding two. */
  pending_dedup: number;
  /** Rows the next issuing pass would leave alone, with the reason. Stated
   *  before anything runs, because the question is asked elsewhere — a fencer
   *  who is on the list but not billable is missing from every surface that
   *  addresses a registration. */
  skipped: IssuedSkip[];
}

export interface IssuedSkip {
  row_id: string;
  name: string | null;
  /** `no_discipline` | `no_name` — both describe the row itself. An address
   *  is not among them: a record enrolled by the organizer needs none. */
  reason: string;
}

export interface IssueReport {
  issued: number;
  /** Rows left alone because they already had a registration. */
  already: number;
  skipped: IssuedSkip[];
}

/** The kinds of console work that run as an operation. */
export const OPERATION_KINDS = ["parse", "match", "dedup", "statement"] as const;
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

/** The counts a reconciliation pass reports: what arrived, what it matched,
 *  and what it could not. */
export interface IngestAndMatch {
  new: number;
  duplicate: number;
  /** Outgoing transfers the intake dropped: nobody's entry fee, and neither new
   *  nor duplicate. Stated only when there were any — it is what explains a
   *  fifteen-row statement reporting twelve. */
  dropped: number;
  matched: number;
  flagged: number;
  unmatched: number;
  partial: number;
  set_aside: number;
  /** What the issuing pass at the head of this intake did. There is no
   *  confirmation dialog to carry it, so the conclusion does. */
  issued: number;
  already_issued: number;
  skipped: IssuedSkip[];
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
  /** The participation condition, offered on an automatic tournament. */
  condition?: string[];
}

/** What a hand entry became: a source row on a manual tournament, a
 *  registration on an automatic one (design manual-entry-registers D1). */
export interface ManualEntryOut {
  row_id: number | null;
  registration_id: number | null;
}

export interface SubstituteIn {
  name: string;
  /** The profile the organizer picked, or null where the substitute is not in
   *  HEMA Ratings — a name the index does not carry is accepted as typed. */
  hr_id: number | null;
  nationality: string | null;
  club: string | null;
  /** The seat's address. Required where Squire keeps the registrations, since
   *  the substitution is written to it; optional otherwise. */
  email: string | null;
}

export interface HRProfile {
  hr_id: number;
  name: string;
  nationality: string | null;
  club: string | null;
  claimed: boolean;
}
