import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { type DedupGroup as Group, api } from "../api";
import type { OperationsView } from "../useOperations";
import DedupGroup from "./DedupGroup";
import useDedupRun from "./useDedupRun";

/** The Deduplication phase: the candidate groups, and nothing else.
 *
 *  The fencer table is not here. Every other processing phase does something to
 *  every row, which is what makes the table the right shape for them; this one
 *  concerns a handful of rows and usually none, and listing fifty of them
 *  states the work in the one place it is hardest to see (design D1). The whole
 *  list is one tab away, on Fencers.
 */
export default function DedupView({
  slug,
  operations,
  onChanged,
  timezone = null,
}: {
  slug: string;
  operations: OperationsView;
  onChanged: () => void;
  timezone?: string | null;
}) {
  const { t } = useTranslation();
  const [groups, setGroups] = useState<Group[]>([]);
  const [failed, setFailed] = useState(false);
  const runner = useDedupRun(slug, operations, onChanged);

  const load = useCallback(() => {
    api.dedupGroups(slug).then(
      (data) => {
        setGroups(data);
        setFailed(false);
      },
      () => {
        setGroups([]);
        setFailed(true);
      },
    );
  }, [slug]);

  useEffect(load, [load]);

  // what a run leaves behind is read when one lands, not only on mount
  const concluded = operations.concluded.dedup;
  useEffect(load, [load, concluded?.id]);

  async function decide(
    key: string,
    accept: boolean,
    fields?: Record<string, unknown>,
    note?: string,
  ) {
    await api.dedupDecide(slug, key, accept, fields, note);
    load();
    onChanged();
  }

  const pending = groups.filter((group) => group.verdict === "pending");
  const settled = groups.filter((group) => group.verdict !== "pending");

  function render(group: Group) {
    return (
      <DedupGroup
        // a changed verdict is a changed group: it comes back with the
        // conclusion it settled on, and no draft of the old one
        key={`${group.key}:${group.verdict}`}
        group={group}
        timezone={timezone}
        onDecide={(accept, fields, note) => void decide(group.key, accept, fields, note)}
      />
    );
  }

  return (
    <main className="sheet-area">
      <div className="sheet-header">
        <h1>{t("phase.dedup")}</h1>
        <span className="dedup-count">{t("dedup.pending", { count: pending.length })}</span>
      </div>

      <div className="sheet-scroll">
        {failed ? (
          <p className="sheet-empty">{t("console.error")}</p>
        ) : groups.length === 0 ? (
          <p className="sheet-empty">
            {t("dedup.empty")}{" "}
            <button className="tertiary" disabled={runner.busy} onClick={runner.run}>
              {runner.running ? t("common.loading") : t("dedup.run")}
            </button>
          </p>
        ) : (
          <>
            {pending.map(render)}
            {settled.length > 0 && (
              <>
                <h2 className="dedup-lane">{t("dedup.settled")}</h2>
                {settled.map(render)}
              </>
            )}
          </>
        )}
      </div>
    </main>
  );
}
