import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { api, type IssueReport } from "../api";

/** Making the fencer list billable where no intake will do it.
 *
 *  Registrations are normally issued at the head of every payment intake, which
 *  is where the answer is needed. A tournament whose payments Squire does not
 *  collect has no intake at all, and its rows would keep no price, no
 *  outstanding column and no line in the export — and the manual paid tick
 *  would have nothing to hold its state against. So the phase issues on arrival
 *  (design Decision 10).
 *
 *  Silent when it does nothing, which is every visit after the first. Nothing
 *  scarce is spent here — such a tournament mints no variable symbols — so there
 *  is nothing to confirm; what the organizer needs is only the rows it could
 *  not do, and the reason.
 */
export default function IssueOnArrival({ slug, onIssued }: { slug: string; onIssued: () => void }) {
  const { t } = useTranslation();
  const [report, setReport] = useState<IssueReport | null>(null);
  const [blocked, setBlocked] = useState(false);
  // once per arrival: React runs an effect twice in development, and the pass
  // is idempotent but the second call is still a request nobody asked for
  const ran = useRef<string | null>(null);

  useEffect(() => {
    if (ran.current === slug) return;
    ran.current = slug;
    api.issueRegistrations(slug).then(
      (done) => {
        setReport(done);
        if (done.issued > 0) onIssued();
      },
      () => setBlocked(true),
    );
  }, [slug, onIssued]);

  if (blocked) return <p className="rail-hint">{t("issue.blockedByDedup")}</p>;
  if (report === null || report.skipped.length === 0) return null;

  return (
    <div>
      <p className="rail-hint">{t("issue.skippedHeading")}</p>
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
    </div>
  );
}
