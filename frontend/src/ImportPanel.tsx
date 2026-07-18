import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { type ImportResult, api } from "./api";

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

  async function upload(file: File) {
    setBusy(true);
    setFailed(false);
    try {
      const outcome = await api.importTable(slug, file);
      setResult(outcome);
      onImported();
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
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
  );
}
