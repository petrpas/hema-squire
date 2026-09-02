import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, type Currency, type Transaction, api } from "../api";
import { formatMoney } from "../money";

/** Linking an unmatched transaction to the registrations it pays for.
 *
 *  Selection is a list, not a single value: one transfer covering several
 *  fencers is what the endpoint's `vs` array exists for, and a control in the
 *  row could not express it legibly. The candidates the backend detected are
 *  offered as one-click entries; anything else is typed (design D3).
 */
export default function LinkDialog({
  slug,
  transaction,
  onLinked,
  onClose,
}: {
  slug: string;
  transaction: Transaction;
  onLinked: () => void;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [selected, setSelected] = useState<number[]>([]);
  const [typed, setTyped] = useState("");
  const [unknown, setUnknown] = useState<number[]>([]);
  const [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState(false);

  const offered = transaction.candidate_vs.filter((vs) => !selected.includes(vs));

  function add(vs: number) {
    setUnknown([]);
    setSelected((current) => (current.includes(vs) ? current : [...current, vs]));
  }

  function addTyped() {
    const vs = Number(typed.trim());
    if (!Number.isInteger(vs) || vs <= 0) return;
    add(vs);
    setTyped("");
  }

  async function confirm() {
    setBusy(true);
    setUnknown([]);
    setFailed(false);
    try {
      await api.linkTransaction(slug, transaction.id, selected);
      onLinked();
      onClose();
    } catch (error) {
      // the endpoint distinguishes the two: a VS that resolves to nothing is
      // the organizer's to correct, so the dialog stays open with the entry
      // intact; a transaction matched by a concurrent poll is already resolved,
      // so the dialog closes and the queue refreshes (design D3)
      const detail = error instanceof ApiError ? error.detail : null;
      const values =
        detail && typeof detail === "object" && "unknown_vs" in detail
          ? (detail as { unknown_vs: number[] }).unknown_vs
          : null;
      if (values) {
        setUnknown(values);
      } else if (error instanceof ApiError && error.status === 409) {
        onLinked();
        onClose();
        return;
      } else {
        setFailed(true);
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(event) => event.stopPropagation()}>
        <h2>{t("payments.link.title")}</h2>
        <p className="muted link-context">
          {new Date(transaction.date).toLocaleDateString("cs")} ·{" "}
          {transaction.payer_name ?? t("payments.link.unknownPayer")} ·{" "}
          {formatMoney(transaction.amount_cents / 100, transaction.currency as Currency)}
        </p>
        {transaction.message && <p className="link-message">{transaction.message}</p>}

        {offered.length > 0 && (
          <>
            <p className="rail-hint">{t("payments.link.candidates")}</p>
            <ul className="link-candidates">
              {offered.map((vs) => (
                <li key={vs}>
                  <button className="row-action" onClick={() => add(vs)}>
                    {vs}
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}

        <div className="link-entry">
          <input
            autoFocus
            value={typed}
            inputMode="numeric"
            placeholder={t("payments.link.placeholder")}
            onChange={(event) => setTyped(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                addTyped();
              }
            }}
          />
          <button className="secondary" onClick={addTyped}>
            {t("payments.link.add")}
          </button>
        </div>

        <p className="rail-hint">{t("payments.link.selected")}</p>
        {selected.length === 0 ? (
          <p className="muted">{t("payments.link.noneSelected")}</p>
        ) : (
          <ul className="link-selected">
            {selected.map((vs) => (
              <li key={vs}>
                {vs}
                <button
                  className="row-action"
                  title={t("payments.link.remove")}
                  onClick={() => setSelected((current) => current.filter((v) => v !== vs))}
                >
                  {t("payments.link.remove")}
                </button>
              </li>
            ))}
          </ul>
        )}

        {unknown.length > 0 && (
          <p className="login-error">
            {t("payments.link.unknownVs", { values: unknown.join(", ") })}
          </p>
        )}
        {failed && <p className="login-error">{t("payments.link.failed")}</p>}

        <div className="modal-actions">
          <button disabled={busy || selected.length === 0} onClick={() => void confirm()}>
            {t("payments.link.confirm")}
          </button>
          <button className="secondary" onClick={onClose}>
            {t("common.cancel")}
          </button>
        </div>
      </div>
    </div>
  );
}
