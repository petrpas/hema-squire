import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { AdminTournament } from "../api";
import Modal from "../Modal";
import { formatTransactionAmount } from "../money";

/** The admin's confirmation before deleting a tournament that has
 *  registrations (spec tournament-admin, Tournament deletion and
 *  cancellation). It states what goes — the registrations and the money
 *  credited to them — and that a real event is its organizer's to cancel, and
 *  the destructive button is never the default. Nobody is mailed. */
export default function DeleteTournamentDialog({
  tournament,
  onConfirm,
  onClose,
}: {
  tournament: AdminTournament;
  /** Resolves when the tournament is gone. The dialog stays open until it
   *  does and states a failure rather than closing on one. */
  onConfirm: () => Promise<void>;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  async function confirm() {
    setBusy(true);
    setFailed(false);
    try {
      await onConfirm();
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  const credited = tournament.credited
    .map((sum) => formatTransactionAmount(sum.amount_cents, sum.currency))
    .join(" + ");

  return (
    <Modal onClose={onClose}>
      <div className="modal">
        <h2>{t("admin.tournaments.delete.title")}</h2>
        <p className="muted link-context">{tournament.display_name}</p>
        <p className="rail-hint">
          {t("admin.tournaments.delete.registrations", {
            count: tournament.registration_count,
          })}
        </p>
        <p className="rail-hint">
          {credited === ""
            ? t("admin.tournaments.delete.nothingCredited")
            : t("admin.tournaments.delete.credited", { amount: credited })}
        </p>
        <p className="rail-hint">{t("admin.tournaments.delete.cancelInstead")}</p>
        {failed && <p className="login-error">{t("admin.tournaments.delete.failed")}</p>}
        <div className="modal-actions">
          <button type="button" className="secondary" onClick={onClose}>
            {t("common.back")}
          </button>
          <button
            type="button"
            className="btn-danger"
            disabled={busy}
            onClick={() => void confirm()}
          >
            {t("admin.tournaments.delete.confirm")}
          </button>
        </div>
      </div>
    </Modal>
  );
}
