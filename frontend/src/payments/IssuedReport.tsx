import { useTranslation } from "react-i18next";

import type { IngestAndMatch } from "../api";

/** What the issuing pass at the head of an intake did.
 *
 *  Silent where it issued nothing, which is every intake after the first. The
 *  part that earns the space is the skipped rows: a row with no discipline, no
 *  e-mail, no name, or an e-mail another row already claimed is a fencer whose
 *  payment cannot reconcile until the organizer fixes the row, and with no
 *  confirmation dialog left to carry that, the conclusion is where they learn
 *  it (design Decision 10).
 */
export default function IssuedReport({ outcome }: { outcome: IngestAndMatch }) {
  const { t } = useTranslation();
  // an operation's outcome is stored JSON, and one written before intake issued
  // anything carries neither field — read it as having issued nothing rather
  // than breaking the conclusion of an import that ran perfectly well
  const issued = outcome.issued ?? 0;
  const skipped = outcome.skipped ?? [];
  if (issued === 0 && skipped.length === 0) return null;

  return (
    <>
      {issued > 0 && <p className="rail-hint">{t("payments.intake.issued", { count: issued })}</p>}
      {skipped.length > 0 && (
        <>
          <p className="rail-hint">{t("issue.skippedHeading")}</p>
          <ul className="rail-hint">
            {skipped.map((skip) => (
              <li key={skip.row_id}>
                {t("issue.skipped", {
                  name: skip.name ?? t("issue.unnamed"),
                  reason: t(`issue.reason.${skip.reason}`),
                })}
              </li>
            ))}
          </ul>
        </>
      )}
    </>
  );
}
