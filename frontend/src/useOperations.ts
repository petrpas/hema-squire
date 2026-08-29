import { useCallback, useEffect, useRef, useState } from "react";

import { type Operation, type OperationKind, type OperationsReport, api } from "./api";

/** How often the console asks how the running work is going. The operations it
 *  watches are measured in minutes, so this is fine-grained enough to look
 *  live and coarse enough to cost nothing (design D7). */
const POLL_MS = 2000;

export interface OperationsView {
  /** The tournament's running operation, whatever its kind and whichever
   *  phase started it. */
  running: Operation | null;
  /** The most recent concluded operation of each kind, so a panel reports what
   *  its own step last did (spec etl-console, Report survives leaving the
   *  phase). */
  concluded: Partial<Record<OperationKind, Operation>>;
  /** Fetch once, outside the poll — after starting work, so the record appears
   *  without waiting for the next tick. */
  refresh: () => void;
}

const EMPTY: OperationsReport = { running: null, concluded: [] };

/** The console's one question about running work, asked once for every reader.
 *
 *  Polling only while something runs is what keeps an idle console silent; the
 *  first tick after a start comes from `refresh`, not from the timer.
 *
 *  `onLanded` fires once as each kind leaves `running`, and is where the fencer
 *  list is reloaded — detected here, once, rather than in each of the three
 *  panels (spec etl-console, The fencer list follows a concluded operation).
 */
export default function useOperations(
  slug: string,
  onLanded?: (kind: OperationKind) => void,
): OperationsView {
  const [report, setReport] = useState<OperationsReport>(EMPTY);
  // the callback changes identity every render in most callers; a ref keeps it
  // out of the effect's dependencies, where it would restart the poll
  const landed = useRef(onLanded);
  landed.current = onLanded;
  const wasRunning = useRef<OperationKind | null>(null);

  const refresh = useCallback(() => {
    api.operations(slug).then(
      (next) => {
        const before = wasRunning.current;
        wasRunning.current = next.running?.kind ?? null;
        if (before !== null && next.running?.kind !== before) landed.current?.(before);
        setReport(next);
      },
      () => setReport(EMPTY),
    );
  }, [slug]);

  useEffect(refresh, [refresh]);

  const running = report.running !== null;
  useEffect(() => {
    if (!running) return;
    const timer = window.setInterval(refresh, POLL_MS);
    return () => window.clearInterval(timer);
  }, [running, refresh]);

  const concluded: Partial<Record<OperationKind, Operation>> = {};
  for (const operation of report.concluded) concluded[operation.kind] = operation;

  return { running: report.running, concluded, refresh };
}
