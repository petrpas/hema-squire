import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import type { Operation } from "./api";
import { progressText, startedText } from "./operationText";

/** How long a concluded operation's final line stands before the indicator
 *  leaves. Long enough to read, short enough not to become furniture. */
const LINGER_MS = 4000;

/** What the console is doing, stated in the corner of every phase.
 *
 *  Present wherever the organizer is, because the work belongs to the
 *  tournament and not to the phase that started it (spec etl-console, A
 *  standing indicator of the tournament's running work). It is text that
 *  changes when the count changes — no spinner, no bar, no motion of its own —
 *  and leaves by fade-out, which is the only departure the design spec allows.
 */
export default function OperationsIndicator({ running }: { running: Operation | null }) {
  const { t } = useTranslation();
  // the operation the card is showing, which outlives `running` by the moment
  // it takes to state that the work is done
  const [shown, setShown] = useState<Operation | null>(null);
  const [leaving, setLeaving] = useState(false);

  useEffect(() => {
    if (running !== null) {
      setShown(running);
      setLeaving(false);
      return;
    }
    if (shown === null) return;
    setLeaving(true);
    const timer = window.setTimeout(() => setShown(null), LINGER_MS);
    return () => window.clearTimeout(timer);
  }, [running, shown]);

  if (shown === null) return null;

  return (
    <aside className={`operation-indicator${leaving ? " leaving" : ""}`}>
      <div className="operation-kind">{t(`operation.label.${shown.kind}`)}</div>
      <div className="operation-count">
        {leaving ? t("operation.done") : progressText(t, shown)}
      </div>
      <div className="operation-started">{startedText(t, shown)}</div>
    </aside>
  );
}
