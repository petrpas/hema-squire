import { IconUnlink } from "@tabler/icons-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { api, type PaymentLink } from "../api";
import { formatTransactionAmount } from "../money";
import QueueCard from "./QueueCard";

/** The tournament's active payment links.
 *
 *  These rules replay opaquely — they touch no sheet row — so they never reach
 *  the rail's edits log, the one place the console otherwise shows what a rule
 *  did. Until this card, a link once made could be neither seen nor undone
 *  (design D6).
 *
 *  Seen means seen: the queue's only action destroys a link, and nobody can aim
 *  that at the right row from the rule's own words. A rule names its transaction
 *  by external id — which, on a statement from a bank that numbers nothing, is a
 *  fingerprint of the row's own content — and its registrations by a variable
 *  symbol that a link made by choosing a fencer never had. So the row states the
 *  payment as the bank wrote it beside the fencer it was credited to, the same
 *  evidence the proposals queue puts in front of the eye that clicks.
 */
export default function PaymentLinksPanel({
  slug,
  reload,
  onChanged,
}: {
  slug: string;
  /** Bumped by the console whenever the money may have moved — a landing
   *  statement import, the Fio poll, the lifecycle run, a link made or undone.
   *  The queue reloads from it rather than waiting for the organizer. */
  reload: number;
  onChanged: () => void;
}) {
  const { t } = useTranslation();
  const [links, setLinks] = useState<PaymentLink[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [removeFailed, setRemoveFailed] = useState(false);

  const load = useCallback(() => {
    api.paymentLinks(slug).then(
      (rows) => {
        setLinks(rows);
        setFailed(false);
      },
      () => {
        setLinks([]);
        setFailed(true);
      },
    );
  }, [slug, reload]);

  useEffect(load, [load]);

  async function remove(id: number) {
    setBusyId(id);
    setRemoveFailed(false);
    try {
      await api.deleteRule(slug, id);
    } catch {
      setRemoveFailed(true);
    } finally {
      setBusyId(null);
      // refetch either way rather than assuming the outcome: removal unapplies
      // the link server-side, and what that leaves depends on what has happened
      // to the registration since
      load();
      onChanged();
    }
  }

  return (
    <QueueCard
      title={t("payments.links.title")}
      count={links === null ? null : links.length}
      loading={links === null}
      failed={failed}
    >
      <table className="sheet-table">
        <thead>
          <tr>
            <th>{t("payments.links.date")}</th>
            <th>{t("payments.links.payer")}</th>
            <th>{t("payments.links.amount")}</th>
            <th>{t("payments.links.message")}</th>
            <th>{t("payments.links.fencer")}</th>
            <th>{t("payments.links.origin")}</th>
            <th className="col-actions" />
          </tr>
        </thead>
        <tbody>
          {(links ?? []).map((link) => {
            const tx = link.transaction;
            return (
              <tr key={link.rule_id}>
                <td>{tx === null ? "—" : new Date(tx.date).toLocaleDateString("cs")}</td>
                <td>{tx?.payer_name ?? "—"}</td>
                <td>{tx === null ? "—" : formatTransactionAmount(tx.amount_cents, tx.currency)}</td>
                {/* the bank's own words, in full: judging the link is the work */}
                <td className="muted">{tx?.message ?? "—"}</td>
                <td>
                  {/* the person, not the number. The symbols follow only
                        where the payer quoted any */}
                  {link.fencers.join(", ") || "—"}
                  {link.vs.length > 0 && <span className="muted"> · {link.vs.join(", ")}</span>}
                </td>
                <td className="muted">
                  {link.auto_created ? t("payments.links.auto") : t("payments.links.manual")}
                </td>
                <td className="col-actions">
                  <button
                    type="button"
                    className="row-action"
                    title={t("payments.links.remove")}
                    disabled={busyId === link.rule_id}
                    onClick={() => void remove(link.rule_id)}
                  >
                    <IconUnlink size={16} stroke={1.5} />
                    <span className="visually-hidden">{t("payments.links.remove")}</span>
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {/* a link whose transaction is gone still holds a fencer's credit, so
            it is shown and undoable rather than hidden */}
      {(links ?? []).some((link) => link.transaction === null) && (
        <p className="rail-hint">{t("payments.links.orphaned")}</p>
      )}
      {removeFailed && <p className="login-error">{t("payments.links.failed")}</p>}
    </QueueCard>
  );
}
