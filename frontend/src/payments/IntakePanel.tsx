import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, type IngestAndMatch, type TournamentDetail, api } from "../api";
import { conclusionText, kindName } from "../operationText";
import IssuedReport from "./IssuedReport";
import IssuePreflight from "./IssuePreflight";
import type { OperationsView } from "../useOperations";

/** Getting the tournament's money into the console: a statement from any bank,
 *  a poll of the bank's API, and the lifecycle passes on demand.
 *
 *  One card rather than three, because they are one concern. Each action states
 *  why it cannot run instead of offering a control that fails when used
 *  (design add-payments-intake D5).
 */
export default function IntakePanel({
  slug,
  detail,
  operations,
  onChanged,
}: {
  slug: string;
  detail: TournamentDetail | null;
  operations: OperationsView;
  onChanged: () => void;
}) {
  const { t } = useTranslation();
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [polled, setPolled] = useState<IngestAndMatch | null>(null);
  const [working, setWorking] = useState(false);

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

  async function poll() {
    setWorking(true);
    setError(null);
    try {
      setPolled(await api.fioPoll(slug));
      onChanged();
    } catch (failure) {
      const refusal = failure instanceof ApiError ? failure.detail : null;
      const pending =
        refusal !== null && typeof refusal === "object" && "code" in refusal
          ? (refusal as { code: string; groups?: number })
          : null;
      // refused on the same ground as the import, and the bank is not asked
      setError(
        pending?.code === "dedup_pending"
          ? t("payments.intake.dedupPending", { count: pending.groups ?? 0 })
          : t("payments.intake.pollFailed"),
      );
    } finally {
      setWorking(false);
    }
  }

  async function runLifecycle() {
    setWorking(true);
    setError(null);
    try {
      await api.processLifecycle(slug);
      onChanged();
    } catch {
      setError(t("payments.intake.lifecycleFailed"));
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
        className="secondary param-save"
        disabled={busy}
        onClick={() => inputRef.current?.click()}
      >
        {running?.kind === "statement" ? t("common.loading") : t("payments.intake.upload")}
      </button>

      {detail?.fio_token_configured ? (
        <button className="secondary param-save" disabled={busy} onClick={() => void poll()}>
          {t("payments.intake.poll")}
        </button>
      ) : (
        <p className="rail-hint">{t("payments.intake.noToken")}</p>
      )}

      <button
        className="secondary param-save"
        disabled={busy}
        onClick={() => void runLifecycle()}
      >
        {t("payments.intake.lifecycle")}
      </button>

      {busy && running !== null && (
        <p className="rail-hint">
          {t("operation.busy", { kind: kindName(t, running.kind) })}
        </p>
      )}
      {polled && (
        <>
          <p className="rail-hint">
            {t("payments.intake.polled", { new: polled.new, matched: polled.matched })}
          </p>
          <IssuedReport outcome={polled} />
        </>
      )}
      {statement?.status === "done" && (
        <>
          <p className="rail-hint">
            {t("payments.intake.imported", {
              new: (statement.outcome as unknown as IngestAndMatch).new,
              matched: (statement.outcome as unknown as IngestAndMatch).matched,
            })}
          </p>
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
