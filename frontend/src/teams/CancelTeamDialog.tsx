import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, type ConsoleTeam, type ConsoleTeamDiscipline } from "../api";
import Modal from "../Modal";

/** Cancelling one team of a registration (spec team-disciplines, Cancelling
 *  one team).
 *
 *  It cannot be taken back: the roster goes with the team, the place it held
 *  is freed and may be taken, and the registration is repriced. So the dialog
 *  says what will happen before it is confirmed — the fee, the roster, the
 *  place, and the letter the entering fencer gets — and the confirmation is
 *  the destructive button, never the default. */
export default function CancelTeamDialog({
  team,
  discipline,
  onConfirm,
  onClose,
}: {
  team: ConsoleTeam;
  discipline: ConsoleTeamDiscipline;
  /** Resolves when the team is cancelled. The dialog stays open until it does
   *  and states a refusal rather than closing on one. */
  onConfirm: () => Promise<void>;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [failed, setFailed] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function confirm() {
    setBusy(true);
    setFailed(null);
    try {
      await onConfirm();
    } catch (error) {
      const detail = error instanceof ApiError ? error.detail : null;
      setFailed(typeof detail === "string" ? detail : "failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal onClose={onClose}>
      <div className="modal">
        <h2>{t("teams.cancel.title")}</h2>
        <p className="muted link-context">
          {team.name} — {discipline.name || discipline.slug}
        </p>
        <p className="rail-hint">{t("teams.cancel.irreversible")}</p>
        <p className="rail-hint">{t("teams.cancel.meaning")}</p>
        <p className="rail-hint">{t("teams.cancel.roster", { count: team.members.length })}</p>
        {!team.waitlisted && <p className="rail-hint">{t("teams.cancel.place")}</p>}
        <p className="rail-hint">{t("teams.cancel.mail")}</p>
        {failed && (
          <p className="login-error">
            {t(`teams.cancel.error.${failed}`, { defaultValue: t("teams.cancel.error.failed") })}
          </p>
        )}

        <div className="modal-actions">
          <button type="button" className="secondary" onClick={onClose}>
            {t("common.cancel")}
          </button>
          <button
            type="button"
            className="btn-danger"
            disabled={busy}
            onClick={() => void confirm()}
          >
            {t("teams.cancel.confirm")}
          </button>
        </div>
      </div>
    </Modal>
  );
}
