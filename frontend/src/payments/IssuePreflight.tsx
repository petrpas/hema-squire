import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { api, type IssuableCount, type TournamentDetail } from "../api";

/** What an intake will do to the fencer list, said before it is asked to.
 *
 *  Intake issues registrations for the rows before it matches anything, and
 *  that is irreversible: on a tournament Squire keeps the registrations for it
 *  spends variable symbols out of a sequence unique across the deployment and
 *  never reused. There is no confirmation dialog to carry the warning — the
 *  organizer reads it here, while deciding to act, rather than after having
 *  decided (design Decision 10).
 *
 *  Two things it deliberately does not do. It says nothing where there is
 *  nothing to issue: a panel that announces a consequence on every visit teaches
 *  the reader to stop reading it. And where duplicates are unresolved it states
 *  that instead — intake is refused until they are settled, and the reader is
 *  pointed at the phase that settles them rather than merely stopped.
 */
export default function IssuePreflight({
  slug,
  detail,
  revision,
}: {
  slug: string;
  detail: TournamentDetail | null;
  /** Bumped when an intake concludes, so the count is re-read rather than
   *  standing at what it was before the import issued everything. */
  revision: number;
}) {
  const { t } = useTranslation();
  const [count, setCount] = useState<IssuableCount | null>(null);

  useEffect(() => {
    api.issuableCount(slug).then(setCount, () => setCount(null));
  }, [slug, revision]);

  if (count === null) return null;

  if (count.pending_dedup > 0) {
    return (
      <p className="rail-hint">
        {t("payments.intake.dedupPending", { count: count.pending_dedup })}
      </p>
    );
  }

  if (count.pending_rows === 0) return null;

  return (
    <p className="rail-hint">
      {detail?.registrations_kept_by === "squire"
        ? t("payments.intake.willIssueWithSymbols", { count: count.pending_rows })
        : t("payments.intake.willIssue", { count: count.pending_rows })}
    </p>
  );
}
