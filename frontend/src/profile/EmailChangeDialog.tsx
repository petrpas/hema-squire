import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, api } from "../api";
import Modal from "../Modal";

/** Changing the account's address (spec `profile-page`, Address change).
 *
 *  The current password is the proof a session alone does not give, and the
 *  link mailed to the new address is the proof the mailbox is the account
 *  holder's. Nothing changes until that link is followed, so the dialog ends
 *  on a statement of where the link went rather than on a saved address. A
 *  wrong password is refused in place, never as a sign-out. */
export default function EmailChangeDialog({
  email,
  onClose,
}: {
  email: string;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sentTo, setSentTo] = useState<string | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const { email: to } = await api.requestEmailChange(current, next.trim());
      setSentTo(to);
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : null;
      if (detail === "wrong_password") setError(t("profile.email.wrong"));
      else if (detail === "email_already_registered") setError(t("profile.email.taken"));
      else if (detail === "email_unchanged") setError(t("profile.email.unchanged"));
      else setError(t("profile.email.failed"));
    } finally {
      setBusy(false);
    }
  }

  if (sentTo !== null) {
    return (
      <Modal onClose={onClose}>
        <div className="modal">
          <h2>{t("profile.email.title")}</h2>
          <p className="rail-hint email-change-sent">
            {t("profile.email.sent", { email: sentTo })}
          </p>
          <div className="modal-actions">
            <button type="button" className="btn-primary" onClick={onClose}>
              {t("profile.email.close")}
            </button>
          </div>
        </div>
      </Modal>
    );
  }

  return (
    <Modal onClose={onClose}>
      {/* the account's present address as the identifier, so a password
          manager offers the current password for the right credential */}
      <form id="change-email" className="modal" onSubmit={submit}>
        <h2>{t("profile.email.title")}</h2>
        <p className="rail-hint">{t("profile.email.intro")}</p>
        <input name="email" type="email" autoComplete="username" value={email} readOnly hidden />
        <div className="form-fields">
          <label className="form-field">
            <span>{t("profile.email.new")}</span>
            <input
              name="new-email"
              type="email"
              autoComplete="off"
              value={next}
              onChange={(event) => setNext(event.target.value)}
              required
              autoFocus
            />
          </label>
          <label className="form-field">
            <span>{t("profile.password.current")}</span>
            <input
              name="current-password"
              type="password"
              autoComplete="current-password"
              value={current}
              onChange={(event) => setCurrent(event.target.value)}
              required
            />
          </label>
        </div>
        {error && <p className="login-error">{error}</p>}
        <div className="modal-actions">
          <button type="button" className="secondary" onClick={onClose} disabled={busy}>
            {t("common.cancel")}
          </button>
          <button type="submit" className="btn-primary" disabled={busy}>
            {busy ? t("profile.email.submitting") : t("profile.email.submit")}
          </button>
        </div>
      </form>
    </Modal>
  );
}
