import { useState } from "react";
import { useTranslation } from "react-i18next";
import Modal from "./Modal";

/** The organizer sending a guest their registration's manage link again (spec
 *  `guest-registration`). A message on the organizer's behalf, so it is asked
 *  before it is sent, and what was done is stated in place afterwards rather
 *  than announced and taken away. */
export default function ResendManageLinkDialog({
  name,
  onConfirm,
  onClose,
}: {
  name: string | null;
  /** Resolves once the mail is sent; a rejection is stated in the dialog. */
  onConfirm: () => Promise<void>;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [state, setState] = useState<"asking" | "busy" | "sent" | "failed">("asking");

  async function confirm() {
    setState("busy");
    try {
      await onConfirm();
      setState("sent");
    } catch {
      setState("failed");
    }
  }

  return (
    <Modal onClose={onClose}>
      <div className="modal">
        <h2>{t("console.resendLink.title")}</h2>
        {name && <p className="muted link-context">{name}</p>}
        <p className="rail-hint">
          {state === "sent" ? t("console.resendLink.sent") : t("console.resendLink.meaning")}
        </p>
        {state === "failed" && <p className="login-error">{t("console.resendLink.failed")}</p>}
        <div className="modal-actions">
          {state === "sent" ? (
            <button type="button" className="secondary" onClick={onClose}>
              {t("common.close")}
            </button>
          ) : (
            <>
              <button type="button" className="secondary" onClick={onClose}>
                {t("common.cancel")}
              </button>
              <button
                type="button"
                className="btn-primary"
                disabled={state === "busy"}
                onClick={() => void confirm()}
              >
                {t("console.resendLink.confirm")}
              </button>
            </>
          )}
        </div>
      </div>
    </Modal>
  );
}
