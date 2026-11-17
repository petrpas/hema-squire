import { useCallback, useEffect, useRef, useState } from "react";

/** Every fifteen seconds while the tab is open (spec floor-today, Přehled
 *  refreshes quietly). The data is swapped in place: nothing animates, and
 *  fields kept in the caller's own state are left alone. A failed refresh
 *  keeps the last data and reports when it was last fresh. */
export const POLL_MS = 15_000;

export function usePolled<T>(
  fetch: () => Promise<T>,
  /** What is shown: a change reads at once instead of at the next tick. */
  key: unknown = null,
): {
  data: T | null;
  failed: boolean;
  freshAt: Date | null;
  reload: () => void;
} {
  const [data, setData] = useState<T | null>(null);
  const [failed, setFailed] = useState(false);
  const [freshAt, setFreshAt] = useState<Date | null>(null);
  const fetchRef = useRef(fetch);
  fetchRef.current = fetch;

  const reload = useCallback(() => {
    fetchRef.current().then(
      (next) => {
        setData(next);
        setFailed(false);
        setFreshAt(new Date());
      },
      () => setFailed(true),
    );
  }, []);

  useEffect(() => {
    void key;
    setData(null);
    reload();
    const timer = window.setInterval(reload, POLL_MS);
    return () => window.clearInterval(timer);
  }, [reload, key]);

  return { data, failed, freshAt, reload };
}
