import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, api, type IngestAndMatch, type TournamentDetail } from "../api";
import { concludedMoment, conclusionText, kindName } from "../operationText";
import type { OperationsView } from "../useOperations";
import ClearPaymentsControl from "./ClearPaymentsControl";
import DroppedNote from "./DroppedNote";
import FioAuthorizationDialog from "./FioAuthorizationDialog";
import IssuedReport from "./IssuedReport";
import IssuePreflight from "./IssuePreflight";

/** Getting the tournament's money into the console: a statement from any bank,
 *  a poll of the bank's API, and the undo of either.
 *
 *  One card rather than three, because they are one concern. Each action states
 *  why it cannot run instead of offering a control that fails when used
 *  (design add-payments-intake D5).
 *
 *  The lifecycle passes — expiries and reminders — used to be a fourth button
 *  here. `POST /payments/process` still runs them and the scheduler still
 *  reaches them on its own; what this card no longer does is let an organizer
 *  fire them by hand, because in manual mode they decide nothing (every
 *  registration is dormant) while still being able to stamp seating settled.
 *  They come back as actions over the debtors table, where they can name who
 *  they act on.
 */
/** What the bank's history lock tells the console: the first day Fio will
 *  serve unasked, and the window the poll had asked for. */
type HistoryLock = { since: string; window_from: string; window_to: string };

export default function IntakePanel({
  slug,
  detail,
  operations,
  reload,
  onChanged,
}: {
  slug: string;
  detail: TournamentDetail | null;
  operations: OperationsView;
  /** Bumped by the console whenever the money may have moved; the clear's
   *  count follows it. */
  reload: number;
  onChanged: () => void;
}) {
  const { t } = useTranslation();
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [polled, setPolled] = useState<IngestAndMatch | null>(null);
  const [working, setWorking] = useState(false);
  // the bank's history lock, held open until the organizer answers it
  const [locked, setLocked] = useState<HistoryLock | null>(null);

  const running = operations.running;
  const busy = running !== null || working;
  const statement = operations.concluded.statement;
  // what the pre-flight count is re-read against: a concluded intake has just
  // issued whatever was pending, so the statement must not keep standing
  const revision = statement?.id ?? 0;

  async function importStatement(file: File) {
    setError(null);
    setPolled(null);
    try {
      await api.importStatement(slug, file);
      operations.refresh();
      onChanged();
    } catch (failure) {
      // the endpoint distinguishes what the organizer can act on: a statement
      // nothing can read, a file that is not a table at all, and someone
      // else's operation already running
      const detail = failure instanceof ApiError ? failure.detail : null;
      const code =
        detail !== null && typeof detail === "object" && "code" in detail
          ? (detail as { code: string }).code
          : detail;
      // the roster cannot be issued while a merge could still collapse a row
      // under it, so intake refuses whole and says which phase settles that
      if (code === "dedup_pending")
        setError(
          t("payments.intake.dedupPending", {
            count: (detail as { groups?: number }).groups ?? 0,
          }),
        );
      else if (code === "no_statement_parser") setError(t("payments.intake.noParser"));
      else if (code === "unsupported_statement_format")
        setError(t("payments.intake.unsupportedFormat"));
      else if (code === "unreadable_statement") setError(t("payments.intake.unreadable"));
      else setError(t("payments.intake.importFailed"));
    } finally {
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  /** Poll the bank, optionally from a later day than the window's own start —
   *  which is what answering the history lock with the shortened window does. */
  async function poll(since?: string) {
    setWorking(true);
    setError(null);
    setLocked(null);
    try {
      setPolled(await api.fioPoll(slug, since));
      onChanged();
    } catch (failure) {
      const refusal = failure instanceof ApiError ? failure.detail : null;
      const pending =
        refusal !== null && typeof refusal === "object" && "code" in refusal
          ? (refusal as { code: string; groups?: number } & Partial<HistoryLock>)
          : null;
      // refused on the same ground as the import, and the bank is not asked
      if (pending?.code === "dedup_pending")
        setError(t("payments.intake.dedupPending", { count: pending.groups ?? 0 }));
      // the bank's own refusal, and one the organizer can lift themselves. It
      // is a question rather than a message, because only they can answer it
      else if (
        pending?.code === "fio_authorization_required" &&
        pending.since !== undefined &&
        pending.window_from !== undefined &&
        pending.window_to !== undefined
      )
        setLocked({
          since: pending.since,
          window_from: pending.window_from,
          window_to: pending.window_to,
        });
      else if (pending?.code === "fio_unreachable") setError(t("payments.intake.pollUnreachable"));
      // the shortened poll, pressed on a window that ended before the bank's
      // ninety days begin: nothing was asked, and saying so beats a row of zeros
      else if (pending?.code === "poll_window_empty" && pending.window_to !== undefined)
        setError(
          t("payments.intake.pollWindowEmpty", {
            to: new Date(pending.window_to).toLocaleDateString("cs"),
          }),
        );
      else setError(t("payments.intake.pollFailed"));
    } finally {
      setWorking(false);
    }
  }

  return (
    <section className="rail-card">
      <h2>{t("payments.intake.title")}</h2>
      <p className="rail-hint">{t("payments.intake.hint")}</p>

      {/* stated ahead of the controls, because it is what pressing one of them
          will do that cannot be undone */}
      <IssuePreflight slug={slug} detail={detail} revision={revision} />

      <input
        ref={inputRef}
        type="file"
        accept=".csv,.xlsx"
        style={{ display: "none" }}
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) void importStatement(file);
        }}
      />
      <button
        type="button"
        className="secondary param-save"
        disabled={busy}
        onClick={() => inputRef.current?.click()}
      >
        {running?.kind === "statement" ? t("common.loading") : t("payments.intake.upload")}
      </button>

      {/* the load's undo, directly beneath it: a statement read wrongly is
          undone where it was loaded, not from a card further down the rail */}
      <ClearPaymentsControl slug={slug} reload={reload} busy={busy} onCleared={onChanged} />

      {detail?.fio_token_configured ? (
        <button
          type="button"
          className="secondary param-save"
          disabled={busy}
          onClick={() => void poll()}
        >
          {t("payments.intake.poll")}
        </button>
      ) : (
        <p className="rail-hint instead-of-control">{t("payments.intake.noToken")}</p>
      )}

      {locked && (
        <FioAuthorizationDialog
          since={locked.since}
          windowFrom={locked.window_from}
          windowTo={locked.window_to}
          onPartial={() => void poll(locked.since)}
          onRetry={() => void poll()}
          onClose={() => setLocked(null)}
        />
      )}

      {busy && running !== null && (
        <p className="rail-hint">{t("operation.busy", { kind: kindName(t, running.kind) })}</p>
      )}
      {polled && (
        <>
          <p className="rail-hint">
            {t("payments.intake.polled", { new: polled.new, matched: polled.matched })}
          </p>
          <DroppedNote outcome={polled} />
          <IssuedReport outcome={polled} />
        </>
      )}
      {statement?.status === "done" && (
        <>
          <p className="rail-hint">
            {t("payments.intake.imported", {
              when: concludedMoment(statement),
              new: (statement.outcome as unknown as IngestAndMatch).new,
              matched: (statement.outcome as unknown as IngestAndMatch).matched,
            })}
          </p>
          <DroppedNote outcome={statement.outcome as unknown as IngestAndMatch} />
          <IssuedReport outcome={statement.outcome as unknown as IngestAndMatch} />
        </>
      )}
      {statement?.status === "failed" && (
        <p className="login-error">{conclusionText(t, statement)}</p>
      )}
      {statement?.status === "interrupted" && (
        <p className="rail-hint">{conclusionText(t, statement)}</p>
      )}
      {error && <p className="login-error">{error}</p>}
    </section>
  );
}
