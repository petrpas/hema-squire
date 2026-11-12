import { useState } from "react";
import { useTranslation } from "react-i18next";

import { type AdminTournament, ApiError, api } from "../api";
import Modal from "../Modal";

/** The admin's fallback assignment of a tournament's owner, for one whose
 *  owner is gone or that never had one (spec tournament-admin, Tournament
 *  ownership transfer). Any account may be named, team member or not; the
 *  previous owner keeps console access only if they are on the team. */
export default function AssignOwnerDialog({
  tournament,
  onAssigned,
  onClose,
}: {
  tournament: AdminTournament;
  onAssigned: () => void;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function assign() {
    setBusy(true);
    setError(null);
    try {
      await api.assignOwner(tournament.slug, email.trim());
      onAssigned();
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 404
          ? t("admin.tournaments.assignOwner.notFound")
          : t("admin.tournaments.assignOwner.failed"),
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal onClose={onClose}>
      <form
        className="modal"
        onSubmit={(event) => {
          event.preventDefault();
          void assign();
        }}
      >
        <h2>{t("admin.tournaments.assignOwner.title")}</h2>
        <p className="muted link-context">{tournament.display_name}</p>
        <p className="rail-hint">
          {tournament.owner
            ? t("admin.tournaments.assignOwner.current", { name: tournament.owner.display_name })
            : t("admin.tournaments.assignOwner.none")}
        </p>
        <p className="rail-hint">{t("admin.tournaments.assignOwner.hint")}</p>
        <input
          type="email"
          value={email}
          placeholder={t("admin.tournaments.assignOwner.placeholder")}
          aria-label={t("admin.tournaments.assignOwner.placeholder")}
          onChange={(event) => setEmail(event.target.value)}
        />
        {error && <p className="login-error">{error}</p>}
        <div className="modal-actions">
          <button type="button" className="secondary" onClick={onClose}>
            {t("common.back")}
          </button>
          <button type="submit" disabled={busy || email.trim() === ""}>
            {t("admin.tournaments.assignOwner.confirm")}
          </button>
        </div>
      </form>
    </Modal>
  );
}
