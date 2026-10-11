import { useState } from "react";
import { useTranslation } from "react-i18next";
import { ApiError } from "./api";
import Modal from "./Modal";

/** The organizer's cancellation of a registration (spec registration, An
 *  organizer may cancel a registration).
 *
 *  Offered where a deletion would stand on a row holding a live
 *  registration, and unlike a deletion it cannot be taken back: the seat it
 *  frees may be taken before anyone thinks better of it. So the dialog says
 *  what will happen before it is confirmed — the seat, the mail, and the
 *  money where some has arrived — and the confirmation is the destructive
 *  button, never the default.
 */
export default function CancelRegistrationDialog({
  name,
  paid,
  onConfirm,
  onClose,
}: {
  name: string | null;
  /** Whether money stands against the registration, which the fencer is
   *  told the organizer will settle. */
  paid: boolean;
  /** Resolves when the registration is cancelled. The dialog stays open until
   *  it does and states a refusal rather than closing on one. */
  onConfirm: (note: string | null) => Promise<void>;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [note, setNote] = useState("");
  const [failed, setFailed] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function confirm() {
    setBusy(true);
    setFailed(null);
    try {
      await onConfirm(note.trim() || null);
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
        <h2>{t("console.cancelRegistration.title")}</h2>
        {name && <p className="muted link-context">{name}</p>}
        <p className="rail-hint">{t("console.cancelRegistration.meaning")}</p>
        <p className="rail-hint">{t("console.cancelRegistration.mail")}</p>
        {paid && <p className="rail-hint">{t("console.cancelRegistration.refund")}</p>}
        <label className="form-field">
          <span>{t("console.cancelRegistration.note")}</span>
          <textarea
            value={note}
            maxLength={500}
            rows={2}
            placeholder={t("console.cancelRegistration.notePlaceholder")}
            onChange={(event) => setNote(event.target.value)}
          />
        </label>
        {failed && (
          <p className="login-error">
            {t(`console.cancelRegistration.error.${failed}`, {
              defaultValue: t("console.cancelRegistration.error.failed"),
            })}
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
            {t("console.cancelRegistration.confirm")}
          </button>
        </div>
      </div>
    </Modal>
  );
}
