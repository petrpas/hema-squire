import { useState } from "react";
import { useTranslation } from "react-i18next";
import { ApiError } from "./api";

/** Why a registration on a collecting tournament is settled with no money.
 *
 *  Its own file rather than a branch inside `SettledCell`: the cell is a
 *  toggle, and a toggle that sometimes opens a form is two behaviours wearing
 *  one name.
 *
 *  The reason is required here and nowhere else. Where the ledger is live, a
 *  paid row holding nothing beside rows holding real credits is a puzzle a
 *  reader will otherwise try to solve as a fault, and one short phrase answers
 *  it. Where no ledger exists, every row is that row and the phrase would be
 *  ceremony (spec payments).
 */
export default function WaiverReasonDialog({
  name,
  onConfirm,
  onClose,
}: {
  name: string | null;
  /** Resolves when the mark is written. The dialog stays open until it does,
   *  and states a refusal rather than closing on one: a dialog that shuts on a
   *  409 leaves a row that did not change and nothing saying why. */
  onConfirm: (reason: string) => Promise<void>;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [reason, setReason] = useState("");
  const [failed, setFailed] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const given = reason.trim();

  async function confirm() {
    setBusy(true);
    setFailed(null);
    try {
      await onConfirm(given);
    } catch (error) {
      const detail = error instanceof ApiError ? error.detail : null;
      setFailed(typeof detail === "string" ? detail : "failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(event) => event.stopPropagation()}>
        <h2>{t("console.waiver.title")}</h2>
        {name && <p className="muted link-context">{name}</p>}
        <p className="rail-hint">{t("console.waiver.meaning")}</p>
        <label className="form-field">
          <span>{t("console.waiver.reason")}</span>
          <input
            autoFocus
            value={reason}
            placeholder={t("console.waiver.placeholder")}
            onChange={(event) => setReason(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && given && !busy) {
                event.preventDefault();
                void confirm();
              }
            }}
          />
        </label>
        {failed && (
          <p className="login-error">
            {t(`console.waiver.error.${failed}`, {
              defaultValue: t("console.waiver.error.failed"),
            })}
          </p>
        )}

        <div className="modal-actions">
          <button type="button" className="secondary" onClick={onClose}>
            {t("common.cancel")}
          </button>
          <button
            type="button"
            className="btn-primary"
            disabled={!given || busy}
            onClick={() => void confirm()}
          >
            {t("console.waiver.confirm")}
          </button>
        </div>
      </div>
    </div>
  );
}
