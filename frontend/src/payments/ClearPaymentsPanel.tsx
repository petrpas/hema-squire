import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { type ClearablePayments, api } from "../api";

/** Undoing an import of money.
 *
 *  A statement read wrongly puts every payment in the tournament wrong, and
 *  until this existed the only way out was to edit the database. The undo lives
 *  beside the intake card that does the importing.
 *
 *  Two things it owes the organizer. That clearing removes the stored readings
 *  of the statement rows as well as the payments, so a corrected file is read
 *  afresh — which the confirmation says plainly, because nothing on screen
 *  would otherwise explain why a re-import behaves differently. And that where
 *  money has been credited the clear is unavailable, stated here rather than
 *  discovered by pressing it.
 */
export default function ClearPaymentsPanel({
  slug,
  reload,
  onCleared,
}: {
  slug: string;
  /** Bumped by the console whenever the money may have moved, so the count
   *  here follows an import without the organizer reloading. */
  reload: number;
  onCleared: () => void;
}) {
  const { t } = useTranslation();
  const [totals, setTotals] = useState<ClearablePayments | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const [cleared, setCleared] = useState<number | null>(null);

  const load = useCallback(() => {
    api.clearablePayments(slug).then(setTotals, () => setTotals(null));
  }, [slug]);

  useEffect(load, [load, reload]);

  async function clear() {
    setBusy(true);
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
      setBusy(false);
    }
  }

  const payments = totals?.payments ?? 0;
  const credited = totals?.credited ?? 0;

  // nothing to clear is nothing to offer, as the import clear does
  if (payments === 0 && cleared === null) return null;

  return (
    <>
      <section className="rail-card">
        <h2>
          {t("payments.clear.title")} <span className="rail-count">({payments})</span>
        </h2>
        <p className="rail-hint">{t("payments.clear.hint")}</p>

        {credited > 0 ? (
          // a fact about the tournament, not an outcome of trying: stated
          // instead of offering a control that fails (spec payments-clearing)
          <p className="rail-hint">
            {t("payments.clear.blockedByCredit", { count: credited })}
          </p>
        ) : (
          payments > 0 && (
            <button
              className="secondary param-save"
              disabled={busy}
              onClick={() => setConfirming(true)}
            >
              {t("payments.clear.action")}
            </button>
          )
        )}

        {failed && <p className="login-error">{t("payments.clear.failed")}</p>}
        {cleared !== null && (
          <p className="rail-hint">{t("payments.clear.result", { count: cleared })}</p>
        )}
      </section>

      {confirming && (
        <div className="modal-backdrop" onClick={() => setConfirming(false)}>
          <div className="modal" onClick={(event) => event.stopPropagation()}>
            <h2>{t("payments.clear.confirm.title")}</h2>
            <p>{t("payments.clear.confirm.body", { count: payments })}</p>
            {/* the half nothing else would explain: a re-import reads the file
                again rather than reusing what was stored */}
            <p>{t("payments.clear.confirm.reread")}</p>
            <p>{t("payments.clear.confirm.final")}</p>
            <div className="modal-actions">
              <button
                type="button"
                className="secondary"
                onClick={() => setConfirming(false)}
              >
                {t("common.cancel")}
              </button>
              <button
                type="button"
                className="btn-primary"
                disabled={busy}
                onClick={() => void clear()}
              >
                {t("payments.clear.confirm.confirm")}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
