import { type ReactNode, useContext, useEffect } from "react";
import { useTranslation } from "react-i18next";

import { QueueTabsContext } from "./QueueTabs";

/** The shell every payments queue draws itself in.
 *
 *  Inside `QueueTabs`, which is where the payments phase puts them, the card
 *  has no heading of its own: the tab carries the title and the count, and a
 *  heading under it would say the same thing twice. The card registers what it
 *  holds, then renders nothing at all unless it is the tab being read.
 *
 *  Outside the tabs it is the card it always was — a heading, the count, and
 *  its rows — which is what a queue shown on its own still needs.
 *
 *  Loading and failure are the same shape either way: one line, the card's own,
 *  so one queue failing leaves the others and the table as they were.
 */
export default function QueueCard({
  title,
  count,
  loading = false,
  failed = false,
  children,
}: {
  title: string;
  /** null while the count is not yet known — the heading shows no number
   *  rather than a zero it would have to take back. */
  count: number | null;
  loading?: boolean;
  failed?: boolean;
  children?: ReactNode;
}) {
  const { t } = useTranslation();
  const tabs = useContext(QueueTabsContext);
  const register = tabs?.register;
  const unregister = tabs?.unregister;

  useEffect(() => {
    register?.(title, count, failed);
  }, [register, title, count, failed]);

  // withdrawing the tab is its own effect, not this one's cleanup: the one
  // above re-runs on every count change, and unregistering there would send
  // the queue to the back of the strip each time its number moved
  useEffect(() => () => unregister?.(title), [unregister, title]);

  const body = failed ? (
    <p className="login-error">{t("payments.queue.failed")}</p>
  ) : loading ? (
    <p className="rail-hint">{t("common.loading")}</p>
  ) : null;

  if (tabs !== null) {
    if (tabs.active !== title) return null;
    return (
      <section
        className="rail-card queue-card"
        role="tabpanel"
        id={`queue-tabpanel-${title}`}
        aria-labelledby={`queue-tab-${title}`}
      >
        {/* an empty queue says so rather than showing an empty frame: its tab
            already states the zero, and a blank panel reads as a fault */}
        {body ?? (count === 0 ? <p className="rail-hint">{t("payments.queue.empty")}</p> : children)}
      </section>
    );
  }

  return (
    <section className={`rail-card queue-card${count === 0 ? " queue-card-empty" : ""}`}>
      <div className="rail-card-heading">
        <h2>{title}</h2>
        {count !== null && <span className="rail-count">{count}</span>}
      </div>
      {body ?? (count !== 0 && children)}
    </section>
  );
}
