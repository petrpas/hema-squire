import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { type Account, api } from "./api";
import Modal from "./Modal";
import { picker, privacy } from "./routes";

/** The organizer data terms, put to a tournament's owner before its console
 *  can be used (spec `privacy`, A tournament owner accepts the organizer data
 *  terms). It cannot be dismissed into the console: leaving it leads back to
 *  the picker, and accepting is the only way through. */
export default function OrganizerTermsDialog({
  onAccepted,
  onLeave,
}: {
  onAccepted: (account: Account) => void;
  onLeave: () => void;
}) {
  const { t } = useTranslation();
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const paragraphs = t("privacy.terms.paragraphs", { returnObjects: true }) as string[];

  async function accept() {
    setBusy(true);
    setFailed(false);
    try {
      onAccepted(await api.acceptOrganizerTerms());
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal onClose={onLeave}>
      <div className="modal">
        <h2>{t("privacy.terms.title")}</h2>
        {paragraphs.map((paragraph) => (
          <p key={paragraph}>{paragraph}</p>
        ))}
        <p className="rail-hint">
          <a href={privacy()} target="_blank" rel="noreferrer">
            {t("privacy.link")}
          </a>
        </p>
        {failed && <p className="login-error">{t("privacy.terms.failed")}</p>}
        <div className="modal-actions">
          <Link className="button-quiet" to={picker()}>
            {t("privacy.terms.leave")}
          </Link>
          <button
            type="button"
            className="btn-primary"
            disabled={busy}
            onClick={() => void accept()}
          >
            {t("privacy.terms.accept")}
          </button>
        </div>
      </div>
    </Modal>
  );
}
