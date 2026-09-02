import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { type Rule, api } from "../api";
import QueueCard from "./QueueCard";

/** The tournament's active payment links.
 *
 *  These rules replay opaquely — they touch no sheet row — so they never reach
 *  the rail's edits log, the one place the console otherwise shows what a rule
 *  did. Until this card, a link once made could be neither seen nor undone
 *  (design D6).
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
  const [links, setLinks] = useState<Rule[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [removeFailed, setRemoveFailed] = useState(false);

  const load = useCallback(() => {
    api.rules(slug, "payments").then(
      (rules) => {
        setLinks(rules.filter((rule) => rule.kind === "payment_link"));
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
      <>
        <table className="sheet-table">
          <thead>
            <tr>
              <th>{t("payments.links.transaction")}</th>
              <th>{t("payments.links.vs")}</th>
              <th className="col-actions" />
            </tr>
          </thead>
          <tbody>
            {(links ?? []).map((rule) => {
              const vs = Array.isArray(rule.payload.vs) ? (rule.payload.vs as number[]) : [];
              return (
                <tr key={rule.id}>
                  <td>{rule.target.replace(/^txn:/, "")}</td>
                  <td>
                    {vs.join(", ") || "—"}
                    <span className="muted">
                      {" "}
                      ·{" "}
                      {rule.payload.auto_created === true
                        ? t("payments.links.auto")
                        : t("payments.links.manual")}
                    </span>
                  </td>
                  <td className="col-actions">
                    <button
                      className="row-action"
                      title={t("payments.links.remove")}
                      disabled={busyId === rule.id}
                      onClick={() => void remove(rule.id)}
                    >
                      {t("payments.links.remove")}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {removeFailed && <p className="login-error">{t("payments.links.failed")}</p>}
      </>
    </QueueCard>
  );
}
