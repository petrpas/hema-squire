import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import AccountMenu from "./AccountMenu";
import AmendmentNotice from "./AmendmentNotice";
import DedupPanel from "./dedup/DedupPanel";
import DedupView from "./dedup/DedupView";
import ExportPanel from "./ExportPanel";
import { IDENTITY_COLUMNS, identityValue, usesHRIdentity } from "./identity";
import ImportPanel from "./ImportPanel";
import IssueOnArrival from "./payments/IssueOnArrival";
import QueueTabs, { QueueTabStrip } from "./payments/QueueTabs";
import MatchDialog from "./MatchDialog";
import MatchPanel from "./MatchPanel";
import NoteMarker from "./NoteMarker";
import OperationsIndicator from "./OperationsIndicator";
import ManualEditsRail from "./ManualEditsRail";
import ManualEntryPanel from "./manual/ManualEntryPanel";
import PaidStamp from "./PaidStamp";
import RentalsCell from "./RentalsCell";
import TolerancePanel from "./TolerancePanel";
import ExpiredHoldingPanel from "./payments/ExpiredHoldingPanel";
import FlaggedPanel from "./payments/FlaggedPanel";
import LikelyPanel from "./payments/LikelyPanel";
import IntakePanel from "./payments/IntakePanel";
import PaymentLinksPanel from "./payments/PaymentLinksPanel";
import RecordedPaymentsPanel from "./payments/RecordedPaymentsPanel";
import RecordPaymentDialog from "./payments/RecordPaymentDialog";
import UnmatchedPanel from "./payments/UnmatchedPanel";
import WaivedBalance from "./WaivedBalance";
import QueuePanel from "./QueuePanel";
import { useAuth } from "./RequireAuth";
import * as routes from "./routes";
import SetupPanel from "./SetupPanel";
import SheetArea from "./SheetArea";
import TeamsPanel from "./TeamsPanel";
import useOperations from "./useOperations";
import { formatMoney, formatMoneyWithEur } from "./money";
import { registeredMoment } from "./momentText";
import { parseInteger } from "./numeric";
import { checkNumeric, checkString, type FieldError } from "./validation";
import {
  ApiError,
  type Account,
  type Amendment,
  type NetChange,
  type Sheet,
  type SheetRow,
  type Tournament,
  type TournamentDetail,
  type TournamentFlags,
  api,
} from "./api";

const STAGES = ["pre", "in", "post"] as const;
// Setup is step 0, ahead of the fencer-list phases (spec: etl-console).
// Teams is a read-only view of team disciplines (design team-disciplines
// 7.2) and Queue is the seating view (design add-payment-modes), both tacked
// on at the end — neither is part of the ETL sequence.
export const PHASES = [
  "setup",
  "import",
  "fencers",
  "matching",
  "dedup",
  "payments",
  "export",
  "teams",
  "queue",
] as const;
export type Phase = (typeof PHASES)[number];

/** The phase the console opens on when the URL names none, and where a URL
 *  naming a phase the mode does not offer lands. The fencer list, not Import:
 *  an organizer who never imports anything would otherwise land on a
 *  permanently empty tab. */
export const DEFAULT_PHASE: Phase = "fencers";

/** Which phases the tournament's settings offer, in the fixed order above — a
 *  setting removes phases, it never reorders them (spec: etl-console). The rest
 *  are always offered, since they are what every tournament is made of.
 *
 *  Payments is offered whoever handles the payments. It is the place a reader
 *  looks for who has paid, and that answer must not move to another phase
 *  depending on a setting the reader may not know about; what varies is the
 *  phase's contents, not its presence (spec add-manual-paid-marking D4). */
export function offeredPhases(mode: TournamentFlags): Phase[] {
  return PHASES.filter((phase) => {
    if (phase === "teams") return mode.feature_teams;
    return true;
  });
}

/** Whether the Payments phase is boned out: on a tournament whose payments
 *  Squire does not handle it holds the settled mark and nothing else — no
 *  queues, no intake, no tolerance, no transactions, none of which has a
 *  meaning when no money passes through Squire. */
export function paymentsBonedOut(mode: TournamentFlags): boolean {
  return !mode.feature_payments;
}

// A phase tab is a view of the whole fencer list plus that operation's
// parameters (design Decision 1). Shared base columns, phase-owned columns.
// Setup, Teams and Queue replace the fencer table entirely, so they own no
// columns.
const BASE_COLUMNS = ["name", "nationality", "club"];

// Columns whose cell is a marker rather than a value: as wide as the marker,
// and empty on most rows.
export const MARKER_COLUMNS = new Set(["notes", "problems"]);

export const PHASE_COLUMNS: Record<Phase, string[]> = {
  setup: [],
  import: ["disciplines", "problems", "notes"],
  fencers: ["disciplines", "weapon_rentals", "afterparty", "registered_at", "notes"],
  matching: ["hr_id", "hr_name", "hr_nationality", "hr_club", "match"],
  // Deduplication shows candidate groups, not the fencer list (design D1)
  dedup: [],
  payments: ["vs", "total_amount", "outstanding", "expires_at", "paid_at", "state"],
  export: ["hr_id", "disciplines", "state"],
  teams: [],
  queue: [],
};

/** The boned-out Payments phase's own columns. A second entry rather than a
 *  condition inside `PHASE_COLUMNS.payments`, so a column stays a property of a
 *  phase and none has to be read as sometimes present (spec etl-console).
 *
 *  The mark has a column of its own only here, where it is the phase's whole
 *  content. Where Squire collects, the table is already wide and a column that
 *  is empty on almost every row would not earn its width: the waiver is
 *  offered on the state cell it changes, and recording a payment sits at the
 *  end of the row with the other row actions. What is owed is kept beside the
 *  mark deliberately: a hand-settled row reads as paid, and its balance says
 *  waived rather than showing a debt nobody has. */
export const BONED_PAYMENTS_COLUMNS = ["total_amount", "outstanding", "settled"];

// Manual edits on these columns become field_edit rules. Notes are not among
// them: a note is the fencer's words or the parser's, and a problem is the
// parser's report — neither is the organizer's to rewrite (spec etl-console,
// Note and problem markers).
const EDITABLE_COLUMNS = new Set(["name", "nationality", "club", "hr_id"]);

/** Columns the fencer list owns, and no other phase.
 *
 *  Disciplines are the one of these. Offered on the fencer list and nowhere
 *  else: the phases after it read the roster rather than settle it, and Import
 *  has no registration to amend.
 *
 *  Whether a registration stands behind the row decides what the edit *does* —
 *  a correction to the row, or an amendment of the registration — and not
 *  whether the cell opens (spec `etl-console`, The disciplines cell is not
 *  closed by the row having a registration). It used to decide both, from a
 *  time when issuing was a button the organizer pressed when they were ready;
 *  issuing is a step of payment intake now, so every imported row has a
 *  registration within seconds of arriving and the cell opened for nothing. */
const FENCER_LIST_COLUMNS = new Set(["disciplines"]);

/** Slugs out of the text a discipline cell is edited as. Separators are loose
 *  on purpose — a comma is what the cell shows, and a space is what someone
 *  types instead — and the case is the slug's own, since a slug is an identity
 *  rather than a word. */
export function parseDisciplines(raw: string): string[] {
  const seen = new Set<string>();
  return raw
    .split(/[,;]|\s+/)
    .map((part) => part.trim())
    .filter((part) => part !== "" && !seen.has(part) && seen.add(part) !== undefined);
}

/** Whether a cell opens for editing here. Identity is the organizer's to
 *  correct where it is claimed — on Import, on the fencer list, or by rebinding
 *  the id on Matching — and not on the phases that read it off the profile
 *  (spec `etl-console`, HR identity in the phases after matching). An italic
 *  cell is read-only there too: making only those editable would put the
 *  affordance on exactly the rows that are hardest to identify, and the rule it
 *  created would stop being displayed the moment the row was matched. */
export function editableHere(column: string, phase: Phase): boolean {
  if (FENCER_LIST_COLUMNS.has(column)) {
    return phase === "fencers";
  }
  // Matching decides one thing: which profile the row is. Its table shows the
  // claim beside the evidence so that decision can be made, and correcting the
  // claim there would edit the very text the reader is comparing against —
  // moving the answer while the question is being asked. The claim is the
  // organizer's to fix on Import and on the fencer list; here only the binding
  // itself is, through `hr_id` and the verdict beside it.
  if (phase === "matching") return column === "hr_id";
  if (IDENTITY_COLUMNS.includes(column)) return !usesHRIdentity(phase);
  return EDITABLE_COLUMNS.has(column);
}

/** The rule an edited cell becomes. An id typed into the table is a verdict,
 *  carrying the same weight and the same consequences as one picked out of
 *  search — an emptied cell says the fencer has no profile (spec
 *  `etl-console`, A typed id is a verdict).
 *
 *  Disciplines become one of two kinds, decided by whether a registration
 *  stands behind the row. A field edit writes the projected row, which is the
 *  right thing for a row that is still a row and carried into the registration
 *  when it is issued. Where a registration already exists, the edit amends it:
 *  its entries are replaced and its total recomputed, so the table and the
 *  money move together (spec `discipline-amendment`).
 *
 *  Every other cell is the organizer's correction of what the fencer told us. */
export function ruleKindFor(
  field: string,
  row?: SheetRow,
): "match_resolution" | "field_edit" | "discipline_amendment" {
  if (field === "hr_id") return "match_resolution";
  if (field === "disciplines" && (row?.registration_id ?? null) !== null) {
    return "discipline_amendment";
  }
  return "field_edit";
}

/** The number the leftmost column shows: the fencer's fixed number, on every
 *  view including Import (spec etl-console, Fixed fencer number). Never the
 *  row's position in the list, and never a line in a file — a line number
 *  describes one upload, and what Import shows is what the tournament imported
 *  across all of them. */
export function rowNumber(row: SheetRow): string {
  return row.number === null || row.number === undefined ? "—" : String(row.number);
}

/** Whether a phase still lists a row a removal has taken out of the table.
 *
 *  A deletion is a decision taken at one step: the steps that follow stand
 *  after it and do not list the row, while the steps before it have not handled
 *  anything yet and still do, struck through and restorable. A merge is not a
 *  step's decision but a statement that two rows are one fencer, as true on the
 *  fencer list as on Export, so an absorbed row is listed nowhere but Import
 *  (spec etl-console, Reversible row deletion).
 *
 *  A removing phase that cannot be placed in the order hides the row from
 *  nothing: a row no phase lists is a row no phase can restore. */
function listsRemovedRow(row: SheetRow, phase: Phase): boolean {
  if (row._merged_into !== undefined) return false;
  const removedIn = PHASES.indexOf(row._removed_in as Phase);
  return removedIn === -1 || removedIn >= PHASES.indexOf(phase);
}

/** The rows a phase lists. Import shows one file, whole: every row it brought,
 *  absorbed and deleted ones included, since the view is a record of what the
 *  file contained and how it was understood. Every other phase shows the fencer
 *  list as the removals before it left it (spec etl-console, Import view of one
 *  batch / Reversible row deletion). */
export function rowsForPhase(rows: SheetRow[], phase: Phase): SheetRow[] {
  if (phase !== "import") {
    return rows.filter((row) => !row._deleted || listsRemovedRow(row, phase));
  }
  // in arrival order, not that of the fencer list: the fencer list is ordered
  // by registration moment, which scatters an upload's rows and sends the ones
  // stating no moment to the end, where a reader checking an import against
  // its source cannot follow them. Arrival order is what the fixed number
  // counts, so the number sorts them
  return rows
    .filter((row) => row.id.startsWith("imp:"))
    .sort((a, b) => (a.number ?? Infinity) - (b.number ?? Infinity));
}

/** What the actions column offers on a row. A listed removed row offers to
 *  come back, which is why it is listed at all — except an absorbed one, whose
 *  removal is not its own to reverse: a merge is undone by withdrawing the
 *  merge, and restoring the row alone would leave it un-deleted and still
 *  merged (spec etl-console, Reversible row deletion).
 *
 *  Nothing is offered on Payments. Taking a fencer off the list is a decision
 *  about the roster, made where the roster is worked; the payments table states
 *  who has paid, and a delete sitting at the end of a row about money reads as
 *  an action on the money. */
/** The phases where a row may be taken out of the table, or put back.
 *
 *  Import and the fencer list, and nowhere else. Those two are where the
 *  roster is settled; every phase after them reads it. A delete at the end of
 *  a row about money reads as an action on the money, and one at the end of a
 *  row about an HR profile reads as unbinding the profile — neither is what it
 *  does, and both are reachable one tab to the left where the row is plainly a
 *  row. */
const ROW_REMOVING_PHASES = new Set<string>(["import", "fencers"]);

/** Whether the phase offers anything at the end of a row at all — asked of the
 *  phase and not of the rows it happens to list, so the table keeps its width
 *  as rows are deleted and restored. */
export function phaseRemovesRows(phase: Phase): boolean {
  return ROW_REMOVING_PHASES.has(phase);
}

export function rowAction(row: SheetRow, phase: Phase): "delete" | "restore" | null {
  if (!phaseRemovesRows(phase)) return null;
  if (row._merged_into !== undefined) return null;
  return row._deleted ? "restore" : "delete";
}

/** The manual-edits log belonging to a phase. Import's holds corrections to how
 *  a file was read; the fencer list's and those after it hold the organizer's
 *  decisions about fencers (spec etl-console, Two manual-edits logs with two
 *  meanings). */
export function editsForPhase(edits: NetChange[], phase: Phase): NetChange[] {
  return edits.filter((edit) => edit.phase === phase);
}

/** The number of the row a merge folded this one into, where one did. An
 *  absorbed row stays listed in the Import view — the view records what a file
 *  contained — so it says where it went rather than merely appearing struck
 *  out (spec etl-console, Import view of one batch). */
export function absorbedInto(row: SheetRow, rows: SheetRow[]): number | null {
  if (row._merged_into === undefined) return null;
  return rows.find((candidate) => candidate.id === row._merged_into)?.number ?? null;
}

export function StateBadge({ id, state }: { id: string; state: string }) {
  const { t } = useTranslation();
  if (state === "paid") return <PaidStamp id={id} label={t("registration.state.paid")} />;
  // the stored value is an enum, not a word anybody reads: every other state
  // was printing its English identifier into a Czech table
  return (
    <span className="state-text">
      {t(`registration.state.${state}`, { defaultValue: state })}
    </span>
  );
}

/** `timezone` is the tournament's own zone, the frame every moment in the
 *  table is read in; it is null until the tournament detail has arrived
 *  beside the sheet, and the moment falls back to the reader's zone until it
 *  does (design show-register-times D5). */
export function CellDisplay({
  row,
  column,
  timezone,
  currency = null,
  hrIdentity = false,
}: {
  row: SheetRow;
  column: string;
  timezone: string | null;
  /** What money on this row is denominated in, and whether a EUR figure sits
   *  beside it. The two fields the decision needs, not the whole tournament: a
   *  cell is a function of what it draws, as `timezone` and `hrIdentity`
   *  already are. Null until the detail has arrived, when an amount reads
   *  unitless rather than wrong. */
  currency?: Pick<TournamentDetail, "local_currency" | "eur_payments_enabled"> | null;
  /** Whether this phase identifies a row by its HR profile (spec `etl-console`,
   *  HR identity in the phases after matching). A flag rather than the phase
   *  itself: the cell is a function of what it draws, not of where the console
   *  is. */
  hrIdentity?: boolean;
}) {
  if (IDENTITY_COLUMNS.includes(column)) {
    const { text, declared } = identityValue(row, column, hrIdentity);
    // the italic is the whole of the marking: no dash, no badge, no second
    // column (spec `etl-console`, HR identity in the phases after matching)
    return declared ? <span className="identity-declared">{text}</span> : <>{text}</>;
  }
  switch (column) {
    case "total_amount":
    case "outstanding": {
      // a registration settled by hand owes nothing, so the figure the balance
      // would show is not what it owes. What the waiver forgave is read from
      // the sheet's own value rather than recomputed here: a reader who took
      // the full total for a fault would be misreading the one true thing
      // about the row (spec etl-console, Outstanding balance in the Payments
      // phase table)
      if (column === "outstanding" && row.settled_by_hand) {
        return (
          <WaivedBalance
            reason={row.settled_by_hand_reason ?? null}
            amount={row.waived_amount ?? null}
            currency={
              currency === null ? null : row.outstanding_currency ?? currency.local_currency
            }
          />
        );
      }
      // an imported row has no registration behind it and so owes nothing —
      // a dash, not a zero it never agreed to
      const value = column === "outstanding" ? row.outstanding_amount : row.total_amount;
      if (value === null || value === undefined) return <>—</>;
      if (currency === null) return <>{value}</>;
      // The price reads in both currencies, because both are what the place
      // costs. The balance reads in one, because a balance has only the lane
      // the money came in: the backend decided which (Registration.
      // balance_cents), and printing the other lane beside it made a pair that
      // read as a conversion — a fencer who had paid 1 100 Kč in full was
      // shown "0 Kč (45 €)".
      if (column === "total_amount") return <>{formatMoneyWithEur(value, null, currency)}</>;
      return <>{formatMoney(value, row.outstanding_currency ?? currency.local_currency)}</>;
    }
    case "state":
      return <StateBadge id={row.id} state={row.state} />;
    case "disciplines":
      return (
        <>
          {row.disciplines.join(", ")}
          {row.substitute_for.length > 0 && (
            <span className="muted"> (+{row.substitute_for.join(", ")})</span>
          )}
        </>
      );
    case "notes":
    case "problems": {
      // nothing at all on a row that carries none: not a dash, not an empty
      // marker (spec etl-console, Note and problem markers)
      const value = row[column];
      if (typeof value !== "string" || value.trim() === "") return null;
      return <NoteMarker kind={column === "notes" ? "note" : "problem"} text={value} />;
    }
    case "weapon_rentals":
      // a name the tournament lends nothing by is billed nothing, and says so
      // here rather than leaving the total quietly short
      return (
        <RentalsCell rentals={row.weapon_rentals} unpriced={row.unpriced_rentals ?? []} />
      );
    case "afterparty":
      return <>{row.afterparty ? "✓" : "—"}</>;
    case "registered_at":
      return <>{registeredMoment(row.registered_at, timezone)}</>;
    case "expires_at":
    case "paid_at": {
      const value = row[column];
      return <>{value ? new Date(value as string).toLocaleDateString("cs") : "—"}</>;
    }
    default: {
      const value = row[column];
      return <>{value === null || value === undefined || value === "" ? "—" : String(value)}</>;
    }
  }
}

export default function Console({
  tournament,
  phase,
}: {
  tournament: Tournament;
  phase: Phase;
}) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { onLogout } = useAuth();
  const [sheet, setSheet] = useState<Sheet | null>(null);
  const [detail, setDetail] = useState<TournamentDetail | null>(null);
  const [error, setError] = useState(false);
  const [matchRow, setMatchRow] = useState<SheetRow | null>(null);
  // the last discipline correction's effect on the money, stated once and then
  // gone; null on every other edit, which the table alone accounts for
  const [amendment, setAmendment] = useState<Amendment | null>(null);
  const [refusal, setRefusal] = useState<string | null>(null);
  const [account, setAccount] = useState<Account | null>(null);
  const [setupDirty, setSetupDirty] = useState(false);
  const [pendingPhase, setPendingPhase] = useState<Phase | null>(null);

  useEffect(() => {
    api.account().then(setAccount, () => setAccount(null));
  }, []);

  // The payments queues each own their data, so the sheet reloading tells them
  // nothing. This counter is the console's one "the money moved" signal: every
  // caller of `refresh` already means exactly that — a landing statement
  // import, the Fio poll, the lifecycle run, a link made or undone — and the
  // queues reload from it rather than each learning about all four
  // (spec etl-console, The fencer list follows a concluded operation).
  const [queueReload, setQueueReload] = useState(0);

  const refresh = useCallback(() => {
    api.sheet(tournament.slug).then(
      (data) => {
        setSheet(data);
        setError(false);
      },
      () => setError(true),
    );
    api.tournament(tournament.slug).then(setDetail, () => {});
    setQueueReload((n) => n + 1);
  }, [tournament.slug]);

  useEffect(refresh, [refresh]);

  // One question about running work, asked once for the whole console: the
  // panels and the indicator read the same answer, and a landing operation
  // reloads the fencer list without the organizer refreshing (design D7).
  const operations = useOperations(tournament.slug, refresh);

  async function addRule(kind: string, target: string, payload: Record<string, unknown>) {
    setAmendment(null);
    setRefusal(null);
    try {
      const created = await api.createRule(tournament.slug, { phase, kind, target, payload });
      // an amendment moved money and may have written to the fencer; every
      // other kind changed only what the table says, which the table shows
      setAmendment(created.amendment ?? null);
    } catch (error) {
      // a refused edit says so rather than leaving the cell to look saved: the
      // table refreshes to what the tournament actually holds either way
      const detail = error instanceof ApiError ? error.detail : null;
      setRefusal(typeof detail === "string" ? detail : "failed");
    }
    refresh();
  }

  /** The disciplines an individual row may enter, by slug. Team disciplines are
   *  not among them: a team is composed rather than entered on a row. */
  const offeredSlugs = (detail?.disciplines ?? [])
    .filter((discipline) => discipline.kind === "individual")
    .map((discipline) => discipline.slug);

  function cellCheck(field: string, raw: string): FieldError | null {
    switch (field) {
      case "disciplines": {
        const slugs = parseDisciplines(raw);
        // emptying it would leave a row that cannot be issued at all, which is
        // the state this edit exists to get out of
        if (slugs.length === 0) return { field, code: "required", params: {} };
        const unknown = slugs.filter((slug) => !offeredSlugs.includes(slug));
        if (unknown.length > 0) {
          return { field, code: "bad_enum", params: { value: unknown.join(", ") } };
        }
        return null;
      }
      case "hr_id":
        return checkNumeric(field, "RosterMemberIn.hr_id", raw);
      case "name":
        return checkString(field, "RosterMemberIn.name", raw, { required: true });
      case "club":
        return checkString(field, "RosterMemberIn.club", raw);
      case "nationality":
        return checkString(field, "RosterMemberIn.nationality", raw);
      default:
        return null;
    }
  }

  function saveEdit(row: SheetRow, field: string, raw: string) {
    if (field === "disciplines") {
      // a list, not the text it was typed as: the row's own shape, which
      // pricing, seating and issuing all read
      void addRule(ruleKindFor(field, row), row.id, { field, value: parseDisciplines(raw) });
      return;
    }
    const value =
      field === "hr_id"
        ? raw === ""
          ? null
          : (() => {
              const result = parseInteger(raw);
              return result.ok ? result.value : null;
            })()
        : raw === ""
          ? null
          : raw;
    void addRule(ruleKindFor(field, row), row.id, { field, value });
  }

  /** Undoing a log entry removes every rule behind it, so the cell returns to
   *  its source value in one action (spec `edit-rules`, Audit of applied
   *  changes). */
  async function undoEdit(ruleIds: number[]) {
    for (const ruleId of ruleIds) {
      await api.deleteRule(tournament.slug, ruleId);
    }
    refresh();
  }

  function resolveMatch(row: SheetRow, hrId: number | null) {
    setMatchRow(null);
    void addRule("match_resolution", row.id, { field: "hr_id", value: hrId });
  }

  /** Accepting the machine's proposal, which is the same verdict as picking
   *  the profile out of search — the organizer has simply not had to go
   *  looking for what the row already shows them. */
  function ratifyMatch(row: SheetRow) {
    void addRule("match_resolution", row.id, { field: "hr_id", value: row.hr_id });
  }

  // Leaving Setup dirty is confirmed (spec: setup-navigation); switching
  // between Setup's own tabs never goes through this, since it isn't a phase change.
  function requestPhase(next: Phase) {
    if (phase === "setup" && setupDirty && next !== "setup") {
      setPendingPhase(next);
    } else {
      navigate(routes.consolePath(tournament.slug, next));
    }
  }

  const rows = sheet?.rows ?? [];
  const visibleRows = rowsForPhase(rows, phase);
  // The rows Matching still owes a verdict: a machine's proposal is not a
  // verdict, and neither is the absence of one (spec etl-console, The ledger
  // idiom).
  const pendingVerdicts = rows.filter(
    (row) =>
      !row._deleted &&
      (row.match_verdict === undefined ||
        !["confirmed", "none_found"].includes(row.match_verdict)),
  ).length;
  const activeRows = rows.filter((row) => !row._deleted);
  const paidCount = activeRows.filter((row) => row.paid).length;
  // from the refreshed detail where there is one, so applying a mode in Setup
  // adds and removes phases at once rather than on the next load
  const phases = offeredPhases(detail ?? tournament);
  const boned = phase === "payments" && paymentsBonedOut(detail ?? tournament);
  const [settling, setSettling] = useState(false);
  const [recording, setRecording] = useState<SheetRow | null>(null);
  const collects = (detail ?? tournament).feature_payments;

  /** Settled with nothing passing through Squire. A write to the registration,
   *  not a rule: every other manual edit in this console persists as a rule
   *  replayed over the projection, which would reach the table and the export
   *  and neither the public participant list nor the registration's own state.
   *  Deliberate, and confined to this action and the recorded payment beside it
   *  (spec etl-console).
   *
   *  Where Squire handles the payments the mark is the waiver and a reason is
   *  required, so the cell asks for one and hands it here. Where it does not,
   *  the reason is optional and none is asked for. */
  async function toggleSettled(row: SheetRow, reason?: string | null) {
    const id = row.registration_id;
    if (typeof id !== "number") return;
    setSettling(true);
    try {
      await api.markSettled(tournament.slug, id, !row.paid, reason);
      refresh();
    } finally {
      setSettling(false);
    }
    // a refusal is left to throw: the caller is a dialog, and it keeps itself
    // open and states the reason. Swallowing it here left a row that did not
    // change and nothing at all saying why
  }
  const columns = [
    ...BASE_COLUMNS,
    ...(boned ? BONED_PAYMENTS_COLUMNS : PHASE_COLUMNS[phase]),
  ];
  const phaseEdits = editsForPhase(sheet?.edits ?? [], phase);

  return (
    <div className="app">
      <header className="topbar">
        <Link className="logo-button" to={routes.picker()} title={t("picker.title")}>
          <span className="logo">{t("app.title")}</span>
        </Link>
        <nav className="stage-control">
          {STAGES.map((stage) => (
            <button
              key={stage}
              className={stage === "pre" ? "active" : ""}
              disabled={stage !== "pre"}
            >
              {t(`stage.${stage}`)}
            </button>
          ))}
        </nav>
        <div className="tournament-info">
          <div className="tournament-name">{tournament.display_name}</div>
          <div className="tournament-date">
            {new Date(tournament.date).toLocaleDateString("cs")}
          </div>
        </div>
        <AccountMenu account={account} onLogout={onLogout} />
      </header>

      <nav className="stepper">
        {phases.map((p, index) => (
          <div key={p} className="step-slot">
            {index > 0 && <div className="step-connector" />}
            <button
              className={`step ${p === phase ? "active" : ""}`}
              onClick={() => requestPhase(p)}
            >
              <span className="step-number">{index + 1}</span>
              <span className="step-label">{t(`phase.${p}`)}</span>
            </button>
          </div>
        ))}
      </nav>

      <div className="workspace">
        {phase === "setup" ? (
          <SetupPanel
            detail={detail}
            slug={tournament.slug}
            onSaved={refresh}
            hasRegistrations={activeRows.length > 0}
            onDeleted={() => navigate(routes.picker())}
            onDirtyChange={setSetupDirty}
          />
        ) : phase === "teams" ? (
          <TeamsPanel slug={tournament.slug} />
        ) : phase === "queue" ? (
          <QueuePanel slug={tournament.slug} timezone={detail?.timezone ?? null} />
        ) : (
          <>
        {phase === "dedup" ? (
          /* the phase's work is a handful of rows out of fifty, and the fencer
             table states it where it is hardest to see (spec etl-console,
             Deduplication candidate review) */
          <DedupView
            slug={tournament.slug}
            operations={operations}
            onChanged={refresh}
            timezone={detail?.timezone ?? null}
          />
        ) : (
          /* the tabs' state lives above the table, because the fencer list is
             the first of them and gives way to whichever queue is read. Keyed
             by phase: the tabs belong to Payments, and a selection carried into
             a phase that draws no queues would leave the table hidden behind a
             tab that is not there */
          <QueueTabs key={phase} primary={t("payments.tabs.fencers")}>
          <SheetArea
            phase={phase}
            queues={
              boned ? (
                /* the phase's whole content is the mark, so what the mark
                   means goes above the table where the queues would be: a row
                   reading paid while still showing its total is the honest
                   reading of both, and a reader who takes it for a fault is
                   misreading the one true thing about it */
                <>
                  <p className="rail-hint">{t("console.settled.meaning")}</p>
                  {/* no intake exists here to issue the roster, so arriving
                      does it (design Decision 10) */}
                  <IssueOnArrival slug={tournament.slug} onIssued={refresh} />
                </>
              ) : phase === "payments" ? (
                /* one table at a time: the fencer list and five queues stacked
                   could not be read as six different things. Proposals lead
                   the queues — the one with the most work in it and the one an
                   organizer empties fastest; the recorded payments come last,
                   being the one view holding no decision */
                <>
                  <QueueTabStrip />
                  <LikelyPanel
                    slug={tournament.slug}
                    reload={queueReload}
                    onChanged={refresh}
                  />
                  <UnmatchedPanel
                    slug={tournament.slug}
                    reload={queueReload}
                    onChanged={refresh}
                  />
                  <FlaggedPanel
                    slug={tournament.slug}
                    reload={queueReload}
                    onChanged={refresh}
                  />
                  <ExpiredHoldingPanel
                    slug={tournament.slug}
                    reload={queueReload}
                    currency={detail?.local_currency ?? "CZK"}
                  />
                  <PaymentLinksPanel
                    slug={tournament.slug}
                    reload={queueReload}
                    onChanged={refresh}
                  />
                  <RecordedPaymentsPanel
                    slug={tournament.slug}
                    reload={queueReload}
                    onChanged={refresh}
                  />
                </>
              ) : null
            }
            rows={rows}
            visibleRows={visibleRows}
            columns={columns}
            activeRows={activeRows}
            paidCount={paidCount}
            revision={sheet?.edits.length ?? 0}
            timezone={detail?.timezone ?? null}
            currency={detail ?? null}
            error={error}
            refresh={refresh}
            onEdit={saveEdit}
            onValidate={cellCheck}
            onDelete={(row) => void addRule("row_delete", row.id, {})}
            onRestore={(row) => void addRule("row_restore", row.id, {})}
            /* the mark is offered on every tournament: as the boned-out
               phase's own column, and as the waiver on the state cell where
               Squire collects */
            onToggleSettled={phase === "payments" ? toggleSettled : undefined}
            collects={collects}
            onRecordPayment={
              phase === "payments" && collects ? setRecording : undefined
            }
            settling={settling}
            onRatify={ratifyMatch}
            onSearch={setMatchRow}
          />
          </QueueTabs>
        )}
        {recording && detail && (
          <RecordPaymentDialog
            slug={tournament.slug}
            row={recording}
            currency={detail.local_currency}
            eurOffered={detail.eur_payments_enabled}
            /* `refresh` is already the console's "the money moved" signal
               and bumps every queue with it */
            onRecorded={refresh}
            onClose={() => setRecording(null)}
          />
        )}

        <aside className="rail">
          <div className="rail-title">
            {t("rail.operations")} · {t(`phase.${phase}`)}
          </div>

          {/* a phase carries only its own operation's parameters; tournament
              configuration is Setup's, and a phase with none shows no panel
              (spec etl-console: "Operation parameters") */}
          {phase === "import" && (
            <ImportPanel
              slug={tournament.slug}
              operations={operations}
              onImported={refresh}
            />
          )}
          {/* the fencer list is entered and corrected here; making it billable
              is not an action of this phase and is not offered as one — payment
              intake issues registrations for it (design Decision 10) */}
          {phase === "fencers" && (
            <ManualEntryPanel detail={detail} slug={tournament.slug} onEntered={refresh} />
          )}
          {phase === "matching" && (
            <MatchPanel
              slug={tournament.slug}
              operations={operations}
              pending={pendingVerdicts}
              onChanged={refresh}
            />
          )}
          {phase === "dedup" && (
            <DedupPanel
              slug={tournament.slug}
              operations={operations}
              onChanged={refresh}
            />
          )}
          {/* the four payment queues are the phase's main column, above the
              fencer table; the rail keeps what it keeps for every phase — the
              operation's parameters and the edits log (design
              add-payments-console-ui D1) */}
          {phase === "payments" && !boned && (
            <>
              <IntakePanel
                slug={tournament.slug}
                detail={detail}
                operations={operations}
                reload={queueReload}
                onChanged={refresh}
              />
              <TolerancePanel detail={detail} slug={tournament.slug} onSaved={refresh} />
            </>
          )}
          {phase === "export" && <ExportPanel slug={tournament.slug} />}

          <ManualEditsRail
            entries={phaseEdits}
            rows={rows}
            timezone={detail?.timezone ?? null}
            onUndo={(ruleIds) => void undoEdit(ruleIds)}
          />
        </aside>
          </>
        )}
      </div>

      {/* the tournament's running work, wherever the organizer stands */}
      <OperationsIndicator running={operations.running} />

      {/* what a discipline correction did to the money, which the cell cannot
          show (spec discipline-amendment) */}
      <AmendmentNotice
        amendment={amendment}
        refusal={refusal}
        currency={detail?.local_currency ?? null}
      />

      {matchRow && (
        <MatchDialog
          row={matchRow}
          onResolve={(hrId) => resolveMatch(matchRow, hrId)}
          onClose={() => setMatchRow(null)}
        />
      )}

      {pendingPhase !== null && (
        <div className="modal-backdrop" onClick={() => setPendingPhase(null)}>
          <div className="modal" onClick={(event) => event.stopPropagation()}>
            <h2>{t("console.leaveSetup.title")}</h2>
            <p>{t("console.leaveSetup.body")}</p>
            <div className="modal-actions">
              <button
                type="button"
                className="secondary"
                onClick={() => setPendingPhase(null)}
              >
                {t("common.cancel")}
              </button>
              <button
                type="button"
                className="btn-primary"
                onClick={() => {
                  navigate(routes.consolePath(tournament.slug, pendingPhase));
                  setPendingPhase(null);
                }}
              >
                {t("console.leaveSetup.confirm")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
