import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { type ImportResult, type ImportStatus, api } from "./api";

export default function ImportPanel({
  slug,
  onImported,
}: {
  slug: string;
  onImported: () => void;
}) {
  const { t } = useTranslation();
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [failed, setFailed] = useState(false);
  const [status, setStatus] = useState<ImportStatus | null>(null);
  const [confirming, setConfirming] = useState(false);

  const refreshStatus = useCallback(() => {
    api.importStatus(slug).then(setStatus, () => setStatus(null));
  }, [slug]);

  useEffect(refreshStatus, [refreshStatus]);

  async function upload(file: File) {
    setBusy(true);
    setFailed(false);
    try {
      const outcome = await api.importTable(slug, file);
      setResult(outcome);
      refreshStatus();
      onImported();
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  /** Hard and final: the tournament asserts it never imported anything (spec
   *  table-import, Clearing the tournament's imported content). */
  async function clear() {
    setBusy(true);
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
      setBusy(false);
    }
  }

  // nothing to clear is nothing to offer
  const imported = status?.total ?? { rows: 0, files: 0 };
  const hasImports = imported.files > 0;

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
          {busy ? t("common.loading") : t("import.upload")}
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
        {failed && <p className="login-error">{t("import.failed")}</p>}
        {result && (
          <p className="rail-hint">
            {result.detail === "llm_not_configured"
              ? t("import.notConfigured", { rows: result.rows })
              : t("import.result", {
                  rows: result.rows,
                  parsed: result.parsed,
                  reused: result.reused,
                  problems: result.problems.length,
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
