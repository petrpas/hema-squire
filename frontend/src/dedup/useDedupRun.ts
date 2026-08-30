import { useState } from "react";

import { api } from "../api";
import type { OperationsView } from "../useOperations";

/** Starting the deduplication run, from either place that offers it: the rail's
 *  panel, and the empty state that has nothing else to say (spec `etl-console`,
 *  Nothing to decide). One function so the two cannot disagree about what
 *  running means or about when it is refused. */
export default function useDedupRun(
  slug: string,
  operations: OperationsView,
  onChanged: () => void,
) {
  const [error, setError] = useState(false);

  async function run() {
    setError(false);
    try {
      await api.runDedup(slug);
      operations.refresh();
      onChanged();
    } catch {
      setError(true);
    }
  }

  return {
    run: () => void run(),
    /** True while this tournament is busy with anything at all: one operation
     *  at a time, whatever its kind. */
    busy: operations.running !== null,
    running: operations.running?.kind === "dedup",
    /** The run was refused — in practice, no LLM configured. */
    error,
  };
}
