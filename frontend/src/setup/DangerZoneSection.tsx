import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api } from "../api";

export function DangerZoneSection({
  slug,
  hasRegistrations,
  cancelled,
  onDeleted,
  onCancelled,
}: {
  slug: string;
  hasRegistrations: boolean;
  cancelled: boolean;
  onDeleted: () => void;
  onCancelled: () => void;
}) {
  const { t } = useTranslation();
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function act() {
    setBusy(true);
    setError(null);
    try {
      if (hasRegistrations) {
        await api.cancelTournament(slug);
        onCancelled();
      } else {
        await api.deleteTournament(slug);
        onDeleted();
      }
    } catch {
      setError(t("setup.danger.failed"));
    } finally {
      setBusy(false);
      setConfirming(false);
    }
  }

  if (cancelled) {
    return (
      <section className="rail-card danger-zone">
        <h2>{t("setup.danger.title")}</h2>
        <p className="rail-hint">{t("setup.danger.alreadyCancelled")}</p>
      </section>
    );
  }

  return (
    <section className="rail-card danger-zone">
      <h2>{t("setup.danger.title")}</h2>
      <p className="rail-hint">
        {hasRegistrations ? t("setup.danger.cancelHint") : t("setup.danger.deleteHint")}
      </p>
      {error && <p className="login-error">{error}</p>}
      {confirming ? (
        <div className="modal-actions">
          <button type="button" className="secondary" onClick={() => setConfirming(false)}>
            {t("common.cancel")}
          </button>
          <button type="button" className="btn-primary" disabled={busy} onClick={() => void act()}>
            {hasRegistrations ? t("setup.danger.cancelButton") : t("setup.danger.deleteButton")}
          </button>
        </div>
      ) : (
        <button className="secondary" onClick={() => setConfirming(true)}>
          {hasRegistrations ? t("setup.danger.cancelButton") : t("setup.danger.deleteButton")}
        </button>
      )}
    </section>
  );
}
