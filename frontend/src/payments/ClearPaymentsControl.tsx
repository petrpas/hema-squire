import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, type ClearablePayments } from "../api";
import Modal from "../Modal";

/** Undoing an import of money.
 *
 *  A statement read wrongly puts every payment in the tournament wrong, and
 *  until this existed the only way out was to edit the database. It sits
 *  directly under the control that loads a statement, because it is that
 *  control's undo — not a separate concern with a card of its own.
 *
 *  Two things it owes the organizer. That clearing removes the stored readings
 *  of the statement rows as well as the payments, so a corrected file is read
 *  afresh — which the confirmation says plainly, because nothing on screen
 *  would otherwise explain why a re-import behaves differently. And that where
 *  money has been credited the clear is unavailable, stated here rather than
 *  discovered by pressing it, as the intake card states a missing Fio token.
 */
export default function ClearPaymentsControl({
  slug,
  reload,
  busy,
  onCleared,
}: {
  slug: string;
  /** Bumped by the console whenever the money may have moved, so the count
   *  here follows an import without the organizer reloading. */
  reload: number;
  /** The intake card's own idea of being busy: an operation the clear must not
   *  race is one the organizer must not start it during. */
  busy: boolean;
  onCleared: () => void;
}) {
  const { t } = useTranslation();
  const [totals, setTotals] = useState<ClearablePayments | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [working, setWorking] = useState(false);
  const [failed, setFailed] = useState(false);
  const [cleared, setCleared] = useState<number | null>(null);

  const load = useCallback(() => {
    api.clearablePayments(slug).then(setTotals, () => setTotals(null));
  }, [slug]);

  useEffect(load, [load, reload]);

  async function clear() {
    setWorking(true);
    setFailed(false);
    try {
      const body = await api.clearPayments(slug);
      setCleared(body.payments);
      setConfirming(false);
      load();
      onCleared();
    } catch {
      setFailed(true);
    } finally {
      setWorking(false);
    }
  }

  const payments = totals?.payments ?? 0;
  const credited = totals?.credited ?? 0;

  // nothing to clear is nothing to offer, as the import clear does
  if (payments === 0 && cleared === null) return null;

  return (
    <>
      {credited > 0 ? (
        // a fact about the tournament, not an outcome of trying: stated
        // instead of offering a control that fails (spec payments-clearing)
        <p className="rail-hint instead-of-control">{t("payments.clear.blockedByCredit")}</p>
      ) : (
        payments > 0 && (
          <button
            type="button"
            className="secondary param-save"
            disabled={busy || working}
            onClick={() => setConfirming(true)}
          >
            {t("payments.clear.action", { payments })}
          </button>
        )
      )}

      {failed && <p className="login-error">{t("payments.clear.failed")}</p>}
      {cleared !== null && (
        <p className="rail-hint">{t("payments.clear.result", { count: cleared })}</p>
      )}

      {confirming && (
        <Modal onClose={() => setConfirming(false)}>
          <div className="modal">
            <h2>{t("payments.clear.confirm.title")}</h2>
            <p>{t("payments.clear.confirm.body", { count: payments })}</p>
            {/* the half nothing else would explain: a re-import reads the file
                again rather than reusing what was stored */}
            <p>{t("payments.clear.confirm.reread")}</p>
            <p>{t("payments.clear.confirm.final")}</p>
            <div className="modal-actions">
              <button type="button" className="secondary" onClick={() => setConfirming(false)}>
                {t("common.cancel")}
              </button>
              <button
                type="button"
                className="btn-primary"
                disabled={working}
                onClick={() => void clear()}
              >
                {t("payments.clear.confirm.confirm")}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
}
