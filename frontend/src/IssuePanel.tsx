import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { type IssuableCount, type IssueReport, api } from "./api";

/** Making the fencer list billable.
 *
 *  An imported or hand-entered row states who is competing; it carries no
 *  variable symbol and no balance, so a payment for that fencer can be neither
 *  matched nor linked. This issues the registrations those rows imply.
 *
 *  Two things the organizer has to be told before committing, because neither
 *  is reversible and one is a promise about other people's inboxes: how many
 *  rows will be issued, and that nobody will be mailed.
 */
export default function IssuePanel({
  slug,
  onIssued,
}: {
  slug: string;
  onIssued: () => void;
}) {
  const { t } = useTranslation();
  const [count, setCount] = useState<IssuableCount | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [report, setReport] = useState<IssueReport | null>(null);
  const [failed, setFailed] = useState(false);

  const load = useCallback(() => {
    api.issuableCount(slug).then(setCount, () => setCount(null));
  }, [slug]);

  useEffect(load, [load]);

  async function run() {
    setBusy(true);
    setFailed(false);
    try {
      setReport(await api.issueRegistrations(slug));
      setConfirming(false);
      load();
      onIssued();
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  const pending = count?.pending_rows ?? 0;
  const blocked = (count?.pending_dedup ?? 0) > 0;

  return (
    <section className="rail-card">
      <h2>
        {t("issue.title")} <span className="rail-count">({pending})</span>
      </h2>
      <p className="rail-hint">{t("issue.hint")}</p>

      {blocked ? (
        // stated rather than shown as a dead control: the organizer can act on
        // this — it tells them the duplicates are what stands in the way
        <p className="rail-hint">
          {t("issue.blockedByDedup", { count: count?.pending_dedup ?? 0 })}
        </p>
      ) : confirming ? (
        <>
          <p className="rail-hint">{t("issue.confirm", { count: pending })}</p>
          <p className="rail-hint">{t("issue.noMail")}</p>
          <button className="secondary param-save" disabled={busy} onClick={() => void run()}>
            {busy ? t("common.loading") : t("issue.confirmAction")}
          </button>
          <button className="secondary" disabled={busy} onClick={() => setConfirming(false)}>
            {t("common.cancel")}
          </button>
        </>
      ) : (
        <button
          className="secondary param-save"
          disabled={pending === 0}
          onClick={() => setConfirming(true)}
        >
          {t("issue.action")}
        </button>
      )}

      {failed && <p className="login-error">{t("issue.failed")}</p>}

      {report !== null && (
        <>
          <p className="rail-hint">
            {t("issue.result", { issued: report.issued, already: report.already })}
          </p>
          {report.skipped.length > 0 && (
            <ul className="rail-hint">
              {report.skipped.map((skip) => (
                <li key={skip.row_id}>
                  {t("issue.skipped", {
                    name: skip.name ?? t("issue.unnamed"),
                    reason: t(`issue.reason.${skip.reason}`),
                  })}
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}
