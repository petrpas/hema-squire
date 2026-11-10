import { useState } from "react";
import { useTranslation } from "react-i18next";

import { type Account, api } from "../api";
import DeleteAccountDialog from "./DeleteAccountDialog";

/** The account section's deletion line (spec `profile-page`, The Profile page
 *  offers account deletion): a quiet way in while nothing is pending, and the
 *  date with a way back while something is. */
export default function AccountDeletion({
  account,
  onUpdated,
}: {
  account: Account;
  onUpdated: (account: Account) => void;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  async function withdraw() {
    setBusy(true);
    setFailed(false);
    try {
      onUpdated(await api.withdrawDeletion());
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  if (account.deletion_effective_at !== null) {
    return (
      <div className="deletion-pending">
        <p className="rail-hint">
          {t("profile.deletion.pending", {
            date: new Date(account.deletion_effective_at).toLocaleDateString(account.language),
          })}
        </p>
        <button type="button" className="secondary" disabled={busy} onClick={() => void withdraw()}>
          {t("profile.deletion.withdraw")}
        </button>
        {failed && <p className="login-error">{t("profile.deletion.failed")}</p>}
      </div>
    );
  }

  return (
    <>
      <button type="button" className="link-button" onClick={() => setOpen(true)}>
        {t("profile.deletion.open")}
      </button>
      {open && (
        <DeleteAccountDialog
          onClose={() => setOpen(false)}
          onRequested={(updated) => {
            setOpen(false);
            onUpdated(updated);
          }}
        />
      )}
    </>
  );
}
