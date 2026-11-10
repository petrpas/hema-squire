import { useState } from "react";
import { useTranslation } from "react-i18next";

import { type AdminAccount, api } from "../api";
import Modal from "../Modal";

/** Erasing what rosters show of a person (spec `account-deletion`, An Admin
 *  can erase an identity on request): for an upheld objection, or a request
 *  from someone without an account. It cannot be undone, so the dialog names
 *  the record and asks once more. */
export default function EraseIdentityDialog({
  account,
  onClose,
  onErased,
}: {
  account: AdminAccount;
  onClose: () => void;
  onErased: () => void;
}) {
  const { t } = useTranslation();
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  async function erase() {
    setBusy(true);
    setFailed(false);
    try {
      await api.adminEraseIdentity(account.id);
      onErased();
    } catch {
      setFailed(true);
      setBusy(false);
    }
  }

  return (
    <Modal onClose={onClose}>
      <div className="modal">
        <h2>{t("admin.erase.title")}</h2>
        <p>{t("admin.erase.body", { name: account.display_name })}</p>
        {failed && <p className="login-error">{t("admin.erase.failed")}</p>}
        <div className="modal-actions">
          <button type="button" className="secondary" onClick={onClose} disabled={busy}>
            {t("common.cancel")}
          </button>
          <button
            type="button"
            className="btn-primary"
            disabled={busy}
            onClick={() => void erase()}
          >
            {t("admin.erase.confirm")}
          </button>
        </div>
      </div>
    </Modal>
  );
}
