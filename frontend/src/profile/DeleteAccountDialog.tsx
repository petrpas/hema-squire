import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { type Account, ApiError, api, type DeletionImpact } from "../api";
import Modal from "../Modal";

/** Asking for the account to be deleted (spec `account-deletion`, An account
 *  holder can request deletion). States what it would do before anything is
 *  asked: the entries it cancels with what was paid on them, the held rosters
 *  the name stays on, and that organizers' own copies are out of reach. Where
 *  something blocks it, says what has to change and asks for nothing. */
export default function DeleteAccountDialog({
  onClose,
  onRequested,
}: {
  onClose: () => void;
  onRequested: (account: Account) => void;
}) {
  const { t, i18n } = useTranslation();
  const [impact, setImpact] = useState<DeletionImpact | null>(null);
  const [failed, setFailed] = useState<string | null>(null);
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.deletionImpact().then(setImpact, () => setFailed(t("profile.deletion.failed")));
  }, [t]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setFailed(null);
    try {
      onRequested(await api.requestDeletion(password));
    } catch (error) {
      setFailed(
        error instanceof ApiError && error.detail === "wrong_password"
          ? t("profile.password.wrong")
          : t("profile.deletion.failed"),
      );
      setBusy(false);
    }
  }

  const money = (cents: number, currency: string) =>
    new Intl.NumberFormat(i18n.language, { style: "currency", currency }).format(cents / 100);

  return (
    <Modal onClose={onClose}>
      <form className="modal" onSubmit={submit}>
        <h2>{t("profile.deletion.title")}</h2>
        {impact === null ? (
          failed === null && <p>{t("common.loading")}</p>
        ) : impact.blockers.length > 0 ? (
          <ul className="deletion-impact">
            {impact.blockers.map((blocker) => (
              <li key={blocker.kind}>
                {t(`profile.deletion.blocker.${blocker.kind}`, {
                  tournaments: blocker.tournaments.join(", "),
                })}
              </li>
            ))}
          </ul>
        ) : (
          <>
            <p>{t("profile.deletion.intro")}</p>
            {impact.cancelled.length > 0 && (
              <>
                <p>{t("profile.deletion.cancelled")}</p>
                <ul className="deletion-impact">
                  {impact.cancelled.map((entry) => (
                    <li key={`${entry.tournament}-${entry.variable_symbol}`}>
                      {entry.tournament}
                      {entry.credited.length > 0 &&
                        ` — ${t("profile.deletion.credited", {
                          amount: entry.credited
                            .map((c) => money(c.amount_cents, c.currency))
                            .join(", "),
                        })}`}
                    </li>
                  ))}
                </ul>
              </>
            )}
            <p>{t("profile.deletion.heldRosters", { count: impact.held_rosters })}</p>
            <p className="rail-hint">{t("profile.deletion.outOfReach")}</p>
            <label className="form-field">
              <span>{t("profile.password.current")}</span>
              <input
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </label>
          </>
        )}
        {failed && <p className="login-error">{failed}</p>}
        <div className="modal-actions">
          <button type="button" className="secondary" onClick={onClose} disabled={busy}>
            {t("common.cancel")}
          </button>
          {impact !== null && impact.blockers.length === 0 && (
            <button type="submit" className="btn-primary" disabled={busy || password === ""}>
              {t("profile.deletion.submit")}
            </button>
          )}
        </div>
      </form>
    </Modal>
  );
}
