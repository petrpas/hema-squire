import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { type ImportResult, type ImportStatus, api } from "./api";
import { conclusionText, kindName } from "./operationText";
import type { OperationsView } from "./useOperations";

/** Whether an upload came back with its outcome rather than starting a parse —
 *  the case where every row of the file is already decided. */
function isOutcome(started: object): started is ImportResult {
  return "parsed" in started;
}

export default function ImportPanel({
  slug,
  operations,
  onImported,
}: {
  slug: string;
  operations: OperationsView;
  onImported: () => void;
}) {
  const { t } = useTranslation();
  const inputRef = useRef<HTMLInputElement>(null);
  const [clearing, setClearing] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [failed, setFailed] = useState(false);
  const [status, setStatus] = useState<ImportStatus | null>(null);
  const [confirming, setConfirming] = useState(false);

  const refreshStatus = useCallback(() => {
    api.importStatus(slug).then(setStatus, () => setStatus(null));
  }, [slug]);

  useEffect(refreshStatus, [refreshStatus]);

  // What the panel reports comes from the tournament's record of the work, not
  // from what this component did, so it survives a remount (spec etl-console,
  // Report survives leaving the phase).
  const running = operations.running;
  const parse = operations.concluded.parse;
  const busy = running !== null || clearing;
  const outcome =
    result ?? (parse?.status === "done" ? (parse.outcome as unknown as ImportResult) : null);

  useEffect(refreshStatus, [refreshStatus, parse?.id]);

  async function upload(file: File) {
    setFailed(false);
    setResult(null);
    try {
      const started = await api.importTable(slug, file);
      // an all-reused upload never starts an operation; its outcome is the
      // response itself
      if (isOutcome(started)) setResult(started);
      operations.refresh();
      refreshStatus();
      onImported();
    } catch {
      setFailed(true);
    } finally {
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  /** Hard and final: the tournament asserts it never imported anything (spec
   *  table-import, Clearing the tournament's imported content). */
  async function clear() {
    setClearing(true);
    setFailed(false);
    try {
      await api.clearImports(slug);
      setConfirming(false);
      setResult(null);
      refreshStatus();
      onImported();
    } catch {
      setFailed(true);
    } finally {
      setClearing(false);
    }
  }

  // nothing to clear is nothing to offer
  const imported = status?.total ?? { rows: 0, files: 0 };
  const hasImports = imported.files > 0;
  const conclusion = parse ? conclusionText(t, parse) : null;

  return (
    <>
      <section className="rail-card">
        <h2>{t("import.title")}</h2>
        <p className="rail-hint">{t("import.hint")}</p>
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.xlsx"
          style={{ display: "none" }}
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) void upload(file);
          }}
        />
        <button
          className="secondary param-save"
          disabled={busy}
          onClick={() => inputRef.current?.click()}
        >
          {running?.kind === "parse" ? t("common.loading") : t("import.upload")}
        </button>
        {hasImports && (
          <button
            className="secondary param-save"
            disabled={busy}
            onClick={() => setConfirming(true)}
          >
            {t("import.clear")}
          </button>
        )}
        {/* work of another phase blocks this one, and says which */}
        {running !== null && running.kind !== "parse" && (
          <p className="rail-hint">{t("operation.busy", { kind: kindName(t, running.kind) })}</p>
        )}
        {failed && <p className="login-error">{t("import.failed")}</p>}
        {parse?.status === "failed" && <p className="login-error">{conclusion}</p>}
        {parse?.status === "interrupted" && <p className="rail-hint">{conclusion}</p>}
        {outcome && (
          <p className="rail-hint">
            {outcome.detail === "llm_not_configured"
              ? t("import.notConfigured", { rows: outcome.rows })
              : t("import.result", {
                  rows: outcome.rows,
                  parsed: outcome.parsed,
                  reused: outcome.reused,
                  problems: outcome.problems.length,
                })}
          </p>
        )}
      </section>

      {confirming && (
        <div className="modal-backdrop" onClick={() => setConfirming(false)}>
          <div className="modal" onClick={(event) => event.stopPropagation()}>
            <h2>{t("import.clearConfirm.title")}</h2>
            {/* what goes, in the terms the table shows it, and that it does not
                come back (spec, Confirmation states the cost) */}
            <p>
              {t("import.clearConfirm.body", {
                // each count carries its own plural form, so Czech agreement
                // holds for one file as well as for five
                rows: t("import.clearConfirm.rows", { count: imported.rows }),
                files: t("import.clearConfirm.files", { count: imported.files }),
              })}
            </p>
            <p>{t("import.clearConfirm.final")}</p>
            <div className="modal-actions">
              <button type="button" className="secondary" onClick={() => setConfirming(false)}>
                {t("common.cancel")}
              </button>
              <button type="button" className="btn-primary" disabled={busy} onClick={clear}>
                {t("import.clearConfirm.confirm")}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
