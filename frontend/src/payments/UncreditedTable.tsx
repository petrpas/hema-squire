import {
  IconArrowBackUp,
  IconCheck,
  IconLink,
  IconReceiptRefund,
  IconX,
} from "@tabler/icons-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api, type UncreditedPayment } from "../api";
import { formatTransactionAmount } from "../money";
import DispositionCell from "./DispositionCell";
import LinkDialog from "./LinkDialog";

/** Every payment that arrived and lies on nobody.
 *
 *  One table where the console had three: proposals, unresolved money, and the
 *  money a check refused. All three are the same question — this arrived and is
 *  credited to nobody — with the answer to a second question written beside it,
 *  and that second answer is the disposition column. Splitting them by tab made
 *  a reader visit three tables to learn whether there was any work at all,
 *  while a payment that was none of the three (a pairing that credited nothing)
 *  appeared in no table and read as finished.
 *
 *  Sorted by disposition, so the rows wanting the same decision sit together.
 *  Not filtered: a filter that hides four rows of seven does not earn its own
 *  state, and the line beside the tab band already says how many are proposals.
 */

/** The order the dispositions read in: what can be decided from the row itself
 *  first, then what needs a look at a registration, then the payments nothing
 *  could be read from. */
const ORDER: Record<UncreditedPayment["disposition"], number> = {
  proposal: 0,
  paired_uncredited: 1,
  refused: 2,
  none: 3,
};

export default function UncreditedTable({
  slug,
  payments,
  onChanged,
}: {
  slug: string;
  payments: UncreditedPayment[];
  onChanged: () => void;
}) {
  const { t } = useTranslation();
  const [linking, setLinking] = useState<UncreditedPayment | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [errorId, setErrorId] = useState<number | null>(null);

  async function act(id: number, action: () => Promise<unknown>) {
    setBusyId(id);
    setErrorId(null);
    try {
      await action();
      onChanged();
    } catch {
      setErrorId(id);
    } finally {
      setBusyId(null);
    }
  }

  const sorted = [...payments].sort(
    (a, b) => ORDER[a.disposition] - ORDER[b.disposition] || a.date.localeCompare(b.date),
  );

  return (
    <>
      {/* nothing here has been credited and nobody has been written to — the
          table states that once rather than per row */}
      <p className="rail-hint">{t("payments.uncredited.explain")}</p>
      <table className="sheet-table">
        <thead>
          <tr>
            <th>{t("payments.uncredited.date")}</th>
            <th>{t("payments.uncredited.payer")}</th>
            <th className="col-number">{t("payments.uncredited.amount")}</th>
            <th>{t("payments.uncredited.message")}</th>
            <th>{t("payments.uncredited.disposition")}</th>
            <th className="col-actions" />
          </tr>
        </thead>
        <tbody>
          {sorted.map((payment) => (
            <tr key={payment.id}>
              <td>{new Date(payment.date).toLocaleDateString("cs")}</td>
              <td>{payment.payer_name ?? "—"}</td>
              <td className="col-number">
                {formatTransactionAmount(payment.amount_cents, payment.currency)}
              </td>
              {/* the bank's own words, in full: judging them is the work */}
              <td className="muted">{payment.message ?? "—"}</td>
              <td>
                <DispositionCell payment={payment} />
              </td>
              <td className="col-actions">
                <div className="row-actions">
                  {payment.disposition === "proposal" && (
                    <>
                      {/* the two verdicts as glyphs: spelt out they wrapped the
                          actions column onto three lines and pushed the
                          evidence off the row. The word survives as the tooltip */}
                      <button
                        type="button"
                        className="row-action"
                        title={t("payments.uncredited.confirm")}
                        disabled={busyId === payment.id}
                        onClick={() =>
                          void act(payment.id, () => api.confirmProposal(slug, payment.id))
                        }
                      >
                        <IconCheck size={16} stroke={1.5} />
                        <span className="visually-hidden">{t("payments.uncredited.confirm")}</span>
                      </button>
                      <button
                        type="button"
                        className="row-action"
                        title={t("payments.uncredited.reject")}
                        disabled={busyId === payment.id}
                        onClick={() =>
                          void act(payment.id, () => api.rejectProposal(slug, payment.id))
                        }
                      >
                        <IconX size={16} stroke={1.5} />
                        <span className="visually-hidden">{t("payments.uncredited.reject")}</span>
                      </button>
                    </>
                  )}
                  {payment.reinstate_available && (
                    <button
                      type="button"
                      className="row-action"
                      title={t("payments.flagged.reinstate")}
                      disabled={busyId === payment.id}
                      onClick={() =>
                        void act(payment.id, () => api.reinstateTransaction(slug, payment.id))
                      }
                    >
                      <IconArrowBackUp size={16} stroke={1.5} />
                      <span className="visually-hidden">{t("payments.flagged.reinstate")}</span>
                    </button>
                  )}
                  {payment.disposition === "refused" && (
                    <button
                      type="button"
                      className="row-action"
                      title={t("payments.flagged.markForRefund")}
                      disabled={busyId === payment.id}
                      onClick={() =>
                        void act(payment.id, () => api.markTransactionForRefund(slug, payment.id))
                      }
                    >
                      <IconReceiptRefund size={16} stroke={1.5} />
                      <span className="visually-hidden">{t("payments.flagged.markForRefund")}</span>
                    </button>
                  )}
                  {/* pairing by hand is offered on every row here: even a
                      refused payment may be the organizer's to assign
                      elsewhere, and a proposal may be right about the money
                      and wrong about the person */}
                  <button
                    type="button"
                    className="row-action"
                    title={t("payments.unmatched.link")}
                    onClick={() => setLinking(payment)}
                  >
                    <IconLink size={16} stroke={1.5} />
                    <span className="visually-hidden">{t("payments.unmatched.link")}</span>
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {errorId !== null && <p className="login-error">{t("payments.flagged.actionFailed")}</p>}
      {linking && (
        <LinkDialog
          slug={slug}
          transaction={linking}
          onClose={() => setLinking(null)}
          onLinked={() => {
            setLinking(null);
            onChanged();
          }}
        />
      )}
    </>
  );
}
