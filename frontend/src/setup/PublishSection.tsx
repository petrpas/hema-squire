import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, type TournamentDetail, api } from "../api";

export function PublishSection({
  slug,
  detail,
  hasUnsavedChanges,
  onPublished,
}: {
  slug: string;
  detail: TournamentDetail;
  hasUnsavedChanges: boolean;
  onPublished: () => void;
}) {
  const { t } = useTranslation();
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const missing = detail.setup_missing ?? [];

  async function act() {
    setBusy(true);
    setError(null);
    try {
      await api.publishTournament(slug);
      onPublished();
    } catch (err) {
      const reason =
        err instanceof ApiError && typeof err.detail === "string"
          ? err.detail
          : err instanceof ApiError &&
              typeof err.detail === "object" &&
              err.detail !== null &&
              (err.detail as { reason?: string }).reason === "setup_incomplete"
            ? "setup_incomplete"
            : null;
      setError(
        reason === "already_published"
          ? t("setup.publish.failedAlreadyPublished")
          : reason === "cancelled"
            ? t("setup.publish.failedCancelled")
            : reason === "setup_incomplete"
              ? t("setup.publish.failedIncomplete")
              : t("setup.publish.failedGeneric"),
      );
      setConfirming(false);
    } finally {
      setBusy(false);
    }
  }

  if (detail.published_at !== null) {
    return (
      <section className="rail-card dashed">
        <h2>{t("setup.tabs.publish")}</h2>
        <p className="rail-hint">
          {t("setup.publish.published", {
            date: new Date(detail.published_at).toLocaleDateString("cs"),
          })}
        </p>
      </section>
    );
  }

  if (detail.cancelled_at !== null) {
    return (
      <section className="rail-card dashed">
        <h2>{t("setup.tabs.publish")}</h2>
        <p className="rail-hint">{t("setup.publish.cancelled")}</p>
      </section>
    );
  }

  return (
    <section className="rail-card dashed">
      <h2>{t("setup.tabs.publish")}</h2>
      <p className="rail-hint">{t("setup.publish.draftStatement")}</p>
      {missing.length > 0 && (
        <>
          <div className="chips">
            {missing.map((key) => (
              <span key={key} className="chip">
                {t(`setup.missing.${key}`)}
              </span>
            ))}
          </div>
          <p className="rail-hint">{t("setup.publish.blockedHint")}</p>
        </>
      )}
      {hasUnsavedChanges && <p className="rail-hint">{t("setup.publish.unsavedNote")}</p>}
      {error && <p className="login-error">{error}</p>}
      {confirming ? (
        <>
          <p className="rail-hint">{t("setup.publish.confirmBody")}</p>
          <div className="modal-actions">
            <button type="button" className="secondary" onClick={() => setConfirming(false)}>
              {t("common.cancel")}
            </button>
            <button type="button" className="btn-primary" disabled={busy} onClick={() => void act()}>
              {t("setup.publish.confirmButton")}
            </button>
          </div>
        </>
      ) : (
        <button
          className="btn-primary"
          disabled={missing.length > 0}
          onClick={() => setConfirming(true)}
        >
          {t("setup.publish.publishButton")}
        </button>
      )}
    </section>
  );
}
