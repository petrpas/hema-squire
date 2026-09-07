import { IconCheck, IconX } from "@tabler/icons-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { api, type Currency, type Transaction } from "../api";
import { formatMoney } from "../money";
import QueueCard from "./QueueCard";

/** Payments the resolver read a fencer's name in, waiting for a person.
 *
 *  A queue of **proposals**, not of outcomes: nothing here has been credited
 *  and nobody has been mailed. Confirming is the organizer supplying the
 *  variable symbol the payer omitted, and it credits through the same path a
 *  hand-linked payment does (spec name-assisted-matching).
 *
 *  Each row carries the bank's own text beside the fencer proposed, because a
 *  confirmation flow that is always right trains the person not to read. The
 *  evidence has to be in front of the eye that clicks, which is also why there
 *  is deliberately no confirm-all.
 */
export default function LikelyPanel({
  slug,
  reload,
  onChanged,
}: {
  slug: string;
  reload: number;
  onChanged: () => void;
}) {
  const { t } = useTranslation();
  const [transactions, setTransactions] = useState<Transaction[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState<number | null>(null);

  function refresh() {
    api.likelyTransactions(slug).then(
      (data) => {
        setTransactions(data);
        setFailed(false);
      },
      () => {
        setTransactions([]);
        setFailed(true);
      },
    );
  }

  useEffect(refresh, [slug, reload]);

  async function act(transaction: Transaction, accept: boolean) {
    setBusy(transaction.id);
    try {
      if (accept) await api.confirmProposal(slug, transaction.id);
      else await api.rejectProposal(slug, transaction.id);
      refresh();
      onChanged();
    } finally {
      setBusy(null);
    }
  }

  const proposals = transactions ?? [];

  return (
    <QueueCard
      title={t("payments.likely.title")}
      count={transactions === null ? null : proposals.length}
      loading={transactions === null}
      failed={failed}
    >
      <p className="rail-hint">{t("payments.likely.explain")}</p>
      <table className="sheet-table">
        <thead>
          <tr>
            <th>{t("payments.likely.date")}</th>
            <th>{t("payments.likely.payer")}</th>
            <th>{t("payments.likely.amount")}</th>
            <th>{t("payments.likely.message")}</th>
            <th>{t("payments.likely.fencer")}</th>
            <th className="col-actions" />
          </tr>
        </thead>
        <tbody>
          {proposals.map((tx) => (
            <tr key={tx.id}>
              <td>{new Date(tx.date).toLocaleDateString("cs")}</td>
              <td>{tx.payer_name ?? "—"}</td>
              <td>{formatMoney(tx.amount_cents / 100, tx.currency as Currency)}</td>
              {/* the bank's own words, in full: judging them is the work */}
              <td className="muted">{tx.message ?? "—"}</td>
              <td>
                <strong>{tx.proposed_fencer_name ?? "—"}</strong>
              </td>
              <td className="col-actions">
                {/* the two verdicts side by side, as glyphs: spelt out they
                    wrapped the actions column onto three lines and pushed the
                    evidence — which is what the organizer is here to read —
                    off the row. The word survives as the tooltip */}
                <div className="row-actions">
                  <button
                    type="button"
                    className="row-action"
                    title={t("payments.likely.confirm")}
                    disabled={busy === tx.id}
                    onClick={() => void act(tx, true)}
                  >
                    <IconCheck size={16} stroke={1.5} />
                    <span className="visually-hidden">{t("payments.likely.confirm")}</span>
                  </button>
                  <button
                    type="button"
                    className="row-action"
                    title={t("payments.likely.reject")}
                    disabled={busy === tx.id}
                    onClick={() => void act(tx, false)}
                  >
                    <IconX size={16} stroke={1.5} />
                    <span className="visually-hidden">{t("payments.likely.reject")}</span>
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </QueueCard>
  );
}
