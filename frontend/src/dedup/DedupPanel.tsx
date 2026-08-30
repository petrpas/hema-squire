import { useTranslation } from "react-i18next";

import { conclusionText, kindName } from "../operationText";
import type { OperationsView } from "../useOperations";
import useDedupRun from "./useDedupRun";

/** The Deduplication rail: the operation's run control and what its last run
 *  said.
 *
 *  The queue it used to hold is now the phase's whole main area, and so is the
 *  count of it: two numbers beside each other could only ever agree or be a bug
 *  (design D9).
 */
export default function DedupPanel({
  slug,
  operations,
  onChanged,
}: {
  slug: string;
  operations: OperationsView;
  onChanged: () => void;
}) {
  const { t } = useTranslation();
  const runner = useDedupRun(slug, operations, onChanged);
  const dedup = operations.concluded.dedup;

  return (
    <section className="rail-card">
      <h2>{t("dedup.title")}</h2>
      <button className="secondary param-save" disabled={runner.busy} onClick={runner.run}>
        {runner.running ? t("common.loading") : t("dedup.run")}
      </button>
      {runner.busy && !runner.running && operations.running !== null && (
        <p className="rail-hint">
          {t("operation.busy", { kind: kindName(t, operations.running.kind) })}
        </p>
      )}
      {runner.error && <p className="login-error">{t("dedup.notConfigured")}</p>}
      {dedup?.status === "failed" && (
        <p className="login-error">{conclusionText(t, dedup)}</p>
      )}
      {dedup?.status === "interrupted" && (
        <p className="rail-hint">{conclusionText(t, dedup)}</p>
      )}
    </section>
  );
}
