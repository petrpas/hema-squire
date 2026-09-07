import { useState } from "react";
import { useTranslation } from "react-i18next";
import { ApiError, api } from "../api";
import Modal from "../Modal";

/** Records the bank feed token, and never shows one.
 *
 *  Its own dialog rather than a field in the bank account section, because a
 *  token is checked against the bank as it is given: a refusal has to be
 *  readable at the field that caused it, and one folded into the tab's save bar
 *  would surface at the far end of the page long after this closed. So it
 *  writes on submit rather than staging, and stays open on a refusal — the
 *  `WaiverReasonDialog` contract.
 *
 *  The field opens empty on a tournament that already has a token. The server
 *  has never returned one and does not start here; the section states that one
 *  is recorded, and this replaces it. Submitting with the field empty is
 *  therefore inert: an organizer who opened the dialog to look at what was
 *  stored must not delete their feed by pressing save. Clearing is the removal
 *  control, which says what it does.
 */
export default function FeedTokenDialog({
  slug,
  configured,
  onDone,
  onClose,
}: {
  slug: string;
  /** Whether a token is already on file. Governs the removal control and what
   *  the dialog says it will do. */
  configured: boolean;
  /** Called with the tournament's new state once it is written. */
  onDone: (state: { configured: boolean; verified: boolean }) => void;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [token, setToken] = useState("");
  const [failed, setFailed] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const given = token.trim();

  async function write(action: () => Promise<{ configured: boolean; verified: boolean }>) {
    setBusy(true);
    setFailed(null);
    try {
      onDone(await action());
      onClose();
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
        <h2>{t("setup.feedToken.title")}</h2>
        <p className="rail-hint">{t("setup.feedToken.advice")}</p>
        {configured && <p className="rail-hint">{t("setup.feedToken.recorded")}</p>}
        <label className="form-field">
          <span>{t("setup.feedToken.label")}</span>
          <input
            autoFocus
            type="password"
            autoComplete="off"
            value={token}
            onChange={(event) => setToken(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && given && !busy) {
                event.preventDefault();
                void write(() => api.setFioToken(slug, given));
              }
            }}
          />
        </label>
        {failed && (
          <p className="login-error">
            {t(`setup.feedToken.error.${failed}`, {
              defaultValue: t("setup.feedToken.error.failed"),
            })}
          </p>
        )}

        <div className="modal-actions">
          <button type="button" className="secondary" onClick={onClose}>
            {t("common.cancel")}
          </button>
          {configured && (
            <button
              type="button"
              className="link-button"
              disabled={busy}
              onClick={() => void write(() => api.clearFioToken(slug))}
            >
              {t("setup.feedToken.remove")}
            </button>
          )}
          <button
            type="button"
            className="btn-primary"
            disabled={!given || busy}
            onClick={() => void write(() => api.setFioToken(slug, given))}
          >
            {t("setup.feedToken.save")}
          </button>
        </div>
      </div>
    </Modal>
  );
}
